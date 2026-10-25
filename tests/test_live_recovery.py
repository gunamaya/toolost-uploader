import copy
import json
from pathlib import Path
import sys
import subprocess
import types
import unittest
from unittest.mock import MagicMock, Mock, patch

import test_storage
from toolost_uploader import storage
from toolost_uploader.live_draft import DraftError, DraftUI, execute
from toolost_uploader.live_journal import LiveJournal, STAGES


class LiveRecoveryTests(unittest.TestCase):
    setUp = test_storage.StorageTests.setUp

    def profile(self):
        return storage.profile('test', root=self.root)

    def journal(self, session):
        checkpoint = session.create_checkpoint(self.manifest, self.base)
        return LiveJournal(session, checkpoint, '123', 'http://127.0.0.1:9437')

    def through(self, journal, stop, outcome='unknown'):
        for stage in STAGES:
            journal.record(stage, 'unknown', None if stage == 'create' else '456')
            if stage == stop and outcome == 'unknown':
                return
            journal.record(stage, 'observed', '456')
            if stage == stop:
                return

    def kwargs(self, **overrides):
        return dict(alias='test', expected_account='123', endpoint='http://127.0.0.1:9437',
                    approve_draft=True, accept_ui_date=True, root=self.root, **overrides)

    def manifest_file(self):
        path = self.base / 'manifest.json'
        path.write_text(json.dumps(self.manifest))
        return path

    def browser(self):
        factory = MagicMock()
        page = Mock()
        page.url = 'https://toolost.com/user-portal/releases/manage/1'
        page.is_closed.return_value = False
        page.locator.return_value.count.return_value = 0
        page.is_closed.return_value = False
        factory.return_value.__enter__.return_value.chromium.connect_over_cdp.return_value.contexts = [
            types.SimpleNamespace(pages=[page])]
        module = types.ModuleType('playwright.sync_api')
        module.sync_playwright = factory
        return patch.dict(sys.modules, {'playwright': types.ModuleType('playwright'), 'playwright.sync_api': module}), factory

    def test_legacy_debug_flags_fail_before_disk_and_browser(self):
        for flag in ('resume_before_artwork', 'resume_before_audio', 'resume_selected_audio', 'resume_open_metadata'):
            with self.subTest(flag=flag), self.assertRaisesRegex(DraftError, 'debug_recovery_requires_readback_only'):
                execute('DO-NOT-READ', **self.kwargs(**{flag: True}))
        self.assertFalse(self.root.exists())

    def test_binding_and_checkpoint_mismatches(self):
        with self.profile() as session:
            journal = self.journal(session)
            for key in ('run_id', 'checkpoint_sha256', 'profile', 'release_id', 'expected_account', 'endpoint'):
                candidate = copy.deepcopy(journal.value)
                candidate[key] = 'different'
                candidate['record_sha256'] = storage._digest({k: v for k, v in candidate.items() if k != 'record_sha256'})
                storage._atomic_write(session.directory, journal.name, candidate)
                with self.subTest(key=key), self.assertRaisesRegex(DraftError, 'journal_binding_mismatch'):
                    journal.read()
            storage._atomic_write(session.directory, journal.name, journal.value)
            session.cancel_checkpoint('release-1', run_id=journal.checkpoint['run_id'], expected_revision=1)
            with self.assertRaisesRegex(DraftError, 'journal_checkpoint_mismatch'):
                journal.record('create', 'unknown', None)

    def test_malformed_legacy_hash_and_event_ledgers_rejected(self):
        with self.profile() as session:
            journal = self.journal(session)
            malformed = [None, [], {'run_id': journal.checkpoint['run_id'], 'events': []}]
            for field, value in (('record_sha256', '0' * 64), ('events', None),
                                 ('events', [{'operation': 'save', 'outcome': 'observed', 'remote_draft_id': '456'}]),
                                 ('remote_draft_id', 456), ('journal_version', True)):
                candidate = copy.deepcopy(journal.value)
                candidate[field] = value
                if field != 'record_sha256':
                    candidate['record_sha256'] = storage._digest({k: v for k, v in candidate.items() if k != 'record_sha256'})
                malformed.append(candidate)
            for value in malformed:
                storage._atomic_write(session.directory, journal.name, value)
                with self.subTest(value=value), self.assertRaises(DraftError):
                    journal.read()

    def test_create_upload_and_save_cannot_be_replayed_across_restart(self):
        for stage in STAGES:
            with self.subTest(stage=stage):
                with self.profile() as session:
                    manifest = copy.deepcopy(self.manifest)
                    manifest['release_id'] = 'test-' + stage
                    checkpoint = session.create_checkpoint(manifest, self.base)
                    journal = LiveJournal(session, checkpoint, '123', 'http://127.0.0.1:9437')
                    self.through(journal, stage)
                    restarted = LiveJournal(session, journal.checkpoint, '123', journal.binding['endpoint'], existing=True)
                    before = storage._read(session.directory, journal.name)
                    with self.assertRaises(DraftError):
                        restarted.record(stage, 'unknown', before['remote_draft_id'])
                    self.assertEqual(storage._read(session.directory, journal.name), before)
                    if stage != 'save':
                        with self.assertRaisesRegex(DraftError, 'manual_reconciliation_required'):
                            restarted.require_reconciliation()

    def test_orphan_journal_and_existing_checkpoint_not_overwritten(self):
        path = self.manifest_file()
        with self.profile() as session:
            storage._atomic_write(session.directory, 'release-1.live.json', {'legacy': True})
        with self.assertRaisesRegex(DraftError, 'live_journal_exists'):
            execute(path, **self.kwargs())
        with self.profile() as session:
            self.assertEqual(storage._read(session.directory, 'release-1.live.json'), {'legacy': True})
        with self.assertRaisesRegex(storage.StorageError, 'checkpoint_exists'):
            execute(path, **self.kwargs())

    def test_title_amendment_immutable_audited_and_snapshot_unchanged(self):
        with self.profile() as session:
            journal = self.journal(session)
            original = copy.deepcopy(journal.checkpoint)
            journal.approve_title()
            amendment = journal.read()['amendment']
            self.assertEqual(amendment['from_title'], self.manifest['title'])
            self.assertEqual(amendment['to_title'], self.manifest['tracks'][0]['title'])
            self.assertEqual(amendment['original_manifest_sha256'], storage._digest(self.manifest))
            effective = journal.effective_manifest()
            self.assertEqual(amendment['effective_manifest_sha256'], storage._digest(effective))
            effective['tracks'][0]['title'] = 'caller change'
            self.assertEqual(session.read_checkpoint('release-1'), original)
            self.assertEqual(self.manifest['title'], 'Synthetic release')
            restarted = LiveJournal(session, original, '123', journal.binding['endpoint'], existing=True)
            with self.assertRaisesRegex(DraftError, 'title_amendment_immutable'):
                restarted.approve_title()
            self.assertEqual(restarted.effective_manifest()['title'], amendment['to_title'])
            candidate = copy.deepcopy(journal.value)
            candidate['amendment']['to_title'] = 'unapproved'
            candidate['record_sha256'] = storage._digest({k: v for k, v in candidate.items() if k != 'record_sha256'})
            storage._atomic_write(session.directory, journal.name, candidate)
            with self.assertRaisesRegex(DraftError, 'invalid_title_amendment'):
                journal.read()

    def test_amendment_failure_never_creates_or_changes_original(self):
        path = self.manifest_file()
        with patch('toolost_uploader.live_journal.LiveJournal.approve_title', side_effect=OSError):
            with self.assertRaises(OSError):
                execute(path, **self.kwargs(approve_release_title_amendment=True))
        with self.profile() as session:
            value = storage._read(session.directory, 'release-1.live.json')
            self.assertEqual(value['events'], [])
            self.assertIsNone(value['amendment'])
            self.assertEqual(session.read_checkpoint('release-1')['manifest'], self.manifest)

    def test_unknown_save_reconciliation_readback_only_and_idempotent(self):
        path = self.manifest_file()
        with self.profile() as session:
            journal = self.journal(session)
            self.through(journal, 'save')
            checkpoint = journal.checkpoint
        browser, factory = self.browser()
        with browser, patch('toolost_uploader.live_draft.DraftUI') as ui_type:
            ui = ui_type.return_value
            ui.verify_account.side_effect = lambda: self.assertIsNone(getattr(ui, 'remote_id', None))
            ui.remote_id = None
            execute(path, **self.kwargs(reconcile_only=True))
            ui.verify_account.assert_called_once()
            ui.readback.assert_called_once()
            ui.action.assert_not_called()
            for name in ('create', 'artwork', 'audio', 'metadata', 'save'):
                getattr(ui, name).assert_not_called()
            ui.close.assert_called_once()
        with self.profile() as session:
            journal = LiveJournal(session, checkpoint, '123', 'http://127.0.0.1:9437', existing=True)
            events = journal.read()['events']
            self.assertEqual(events[-2]['outcome'], 'unknown')
            self.assertEqual(events[-1]['outcome'], 'verified_subset')
            journal.verify_readback()
            self.assertEqual(journal.read()['events'], events)

    def test_failed_identity_or_readback_keeps_unknown_without_mutation(self):
        path = self.manifest_file()
        with self.profile() as session:
            journal = self.journal(session)
            self.through(journal, 'save')
            before = journal.read()
        for failure in ('verify_account', 'readback'):
            browser, factory = self.browser()
            with browser, patch('toolost_uploader.live_draft.DraftUI') as ui_type:
                ui = ui_type.return_value
                getattr(ui, failure).side_effect = DraftError('unverified')
                with self.assertRaisesRegex(DraftError, 'unverified'):
                    execute(path, **self.kwargs(reconcile_only=True))
                ui.action.assert_not_called()
                if failure == 'verify_account':
                    ui.readback.assert_not_called()
                ui.close.assert_called_once()
            with self.profile() as session:
                self.assertEqual(storage._read(session.directory, journal.name), before)

    def test_reconcile_wrong_binding_and_manifest_stop_before_browser(self):
        path = self.manifest_file()
        with self.profile() as session:
            journal = self.journal(session)
            self.through(journal, 'save')
        for key, value in (('expected_account', '999'), ('endpoint', 'http://127.0.0.1:9438')):
            kwargs = self.kwargs(reconcile_only=True)
            kwargs[key] = value
            with self.subTest(key=key), self.assertRaisesRegex(DraftError, 'journal_binding_mismatch'):
                execute(path, **kwargs)
        changed = copy.deepcopy(self.manifest)
        changed['title'] = 'changed'
        path.write_text(json.dumps(changed))
        with self.assertRaisesRegex(DraftError, 'resume_manifest_mismatch'):
            execute(path, **self.kwargs(reconcile_only=True))

    def test_journal_write_failure_preserves_unknown_and_blocks_next_attempt(self):
        with self.profile() as session:
            journal = self.journal(session)
            journal.record('create', 'unknown', None)
            with patch('toolost_uploader.live_journal._atomic_write', side_effect=storage.StorageError('write_failed')):
                with self.assertRaises(storage.StorageError):
                    journal.record('create', 'observed', '456')
            self.assertEqual(journal.read()['events'][-1]['outcome'], 'unknown')
            with self.assertRaises(DraftError):
                journal.record('create', 'unknown', None)

    def ui(self):
        page = Mock()
        page.url = 'https://toolost.com/user-portal/releases/manage/1'
        page.is_closed.return_value = False
        page.locator.return_value.count.return_value = 0
        ui = DraftUI(page, self.manifest, self.base, '123', Mock())
        return ui, page

    def test_recovery_without_full_account_preflight_never_reads_or_mutates(self):
        ui, page = self.ui()
        ui.remote_id = '456'
        for name in ('create', 'artwork', 'audio', 'metadata', 'save'):
            operation = Mock()
            with self.assertRaisesRegex(DraftError, 'identity_preflight_required_or_changed'):
                ui.action(name, operation)
            operation.assert_not_called()
        with self.assertRaises(DraftError):
            ui.readback()
        page.goto.assert_not_called()
        ui.record.assert_not_called()

    def test_full_account_preflight_observes_only_real_response_metadata(self):
        for account in (123, 999, None, True):
            ui, page = self.ui()
            callbacks = {}
            page.on.side_effect = lambda name, callback: callbacks.update({name: callback})
            def navigate(*args, **kwargs):
                if account is not None:
                    response = Mock(url='https://toolost.com/api/auth/me', status=200)
                    response.json.return_value = {'user': {'id': account}}
                    callbacks['response'](response)
                    ui.observe_account(response)
            page.goto.side_effect = navigate
            if account == 123:
                ui.verify_account()
                self.assertTrue(ui.identity_verified)
            else:
                with self.assertRaisesRegex(DraftError, 'account_mismatch_or_unobserved'):
                    ui.verify_account()
                self.assertFalse(ui.identity_verified)
            page.remove_listener.assert_called_once()
            ui.close()
            page.context.remove_listener.assert_called_once()

    def test_account_session_and_target_changed_block_at_click_boundary(self):
        for change in ('account', 'expired', 'malformed', 'target', 'login'):
            ui, page = self.ui()
            ui.identity_verified = True
            ui.remote_id = '456'
            page.url = 'https://toolost.com/uploader/edit/456'
            if change in ('account', 'expired', 'malformed'):
                response = Mock(url='https://toolost.com/api/auth/me', status=401 if change == 'expired' else 200)
                response.json.return_value = {'user': {'id': 999}}
                if change == 'malformed':
                    response.json.side_effect = ValueError
                ui.observe_account(response)
            else:
                page.url = 'https://toolost.com/login' if change == 'login' else 'https://toolost.com/uploader/edit/999'
            locator = Mock()
            with self.subTest(change=change), self.assertRaises(DraftError):
                ui.click(locator)
            locator.click.assert_not_called()
            ui.record.assert_not_called()

    def test_same_process_duplicate_action_never_retried_even_after_timeout(self):
        for stage in ('create', 'artwork', 'audio', 'save'):
            ui, page = self.ui()
            ui.identity_verified = True
            operation = Mock(side_effect=TimeoutError)
            with self.assertRaises(TimeoutError):
                ui.action(stage, operation)
            with self.assertRaisesRegex(DraftError, 'duplicate_action_requires_reconciliation'):
                ui.action(stage, operation)
            operation.assert_called_once()
            self.assertEqual(ui.record.call_count, 1)

    def test_account_change_during_click_blocks_write_and_keeps_unknown(self):
        ui, page = self.ui()
        ui.identity_verified = True
        ui.remote_id = '456'
        page.url = 'https://toolost.com/uploader/edit/456'
        route = Mock()
        route.request.method = 'POST'
        locator = Mock()
        def click():
            response = Mock(url='https://toolost.com/api/auth/me', status=401)
            ui.observe_account(response)
            ui.guard_request(route)
        locator.click.side_effect = click
        with self.assertRaisesRegex(DraftError, 'identity_preflight_required_or_changed'):
            ui.action('save', lambda: ui.click(locator))
        route.abort.assert_called_once()
        route.continue_.assert_not_called()
        ui.record.assert_called_once_with('save', 'unknown', '456')

    def test_write_guard_blocks_unverified_changed_or_closed_target(self):
        for change in ('unverified', 'target', 'origin', 'login', 'closed', 'read_only'):
            ui, page = self.ui()
            ui.identity_verified = change != 'unverified'
            ui.remote_id = '456'
            page.url = 'https://toolost.com/uploader/edit/456'
            if change == 'target':
                page.url = 'https://toolost.com/uploader/edit/999'
            elif change == 'origin':
                page.url = 'https://example.test/'
            elif change == 'login':
                page.url = 'https://toolost.com/login'
            elif change == 'closed':
                page.is_closed.return_value = True
            elif change == 'read_only':
                ui.read_only = True
            route = Mock()
            route.request.method = 'POST'
            ui.guard_request(route)
            route.abort.assert_called_once()
            route.continue_.assert_not_called()
        ui, page = self.ui()
        ui.identity_verified = True
        route = Mock()
        route.request.method = 'POST'
        ui.guard_request(route)
        route.continue_.assert_called_once()
        ui.close()
        page.context.unroute.assert_called_once()

    def test_reconciliation_does_not_need_upload_assets(self):
        path = self.manifest_file()
        with self.profile() as session:
            journal = self.journal(session)
            self.through(journal, 'save')
        self.asset.unlink()
        browser, factory = self.browser()
        with browser, patch('toolost_uploader.live_draft.DraftUI') as ui_type:
            execute(path, **self.kwargs(reconcile_only=True))
            ui_type.return_value.readback.assert_called_once()
            ui_type.return_value.action.assert_not_called()

    def test_fresh_executor_persists_real_journal_and_amendment_before_create(self):
        path = self.manifest_file()
        browser, factory = self.browser()
        def verify(ui):
            ui.identity_verified = True
        def create(ui):
            with open(self.root / 'profiles/test/checkpoints/release-1.live.json') as stream:
                journal = json.load(stream)
            self.assertEqual(journal['amendment']['to_title'], self.manifest['tracks'][0]['title'])
            self.assertEqual(journal['events'][-1]['outcome'], 'unknown')
            self.assertEqual(ui.manifest['title'], self.manifest['tracks'][0]['title'])
            ui.remote_id = '456'
            ui.page.url = 'https://toolost.com/uploader/edit/456'
        with browser, patch.object(DraftUI, 'verify_account', verify), patch.object(DraftUI, 'create', create), \
                patch.object(DraftUI, 'artwork'), patch.object(DraftUI, 'audio'), \
                patch.object(DraftUI, 'metadata'), patch.object(DraftUI, 'save'), patch.object(DraftUI, 'readback'):
            result = execute(path, **self.kwargs(approve_release_title_amendment=True))
        self.assertEqual(result['status'], 'draft_saved_subset')
        with self.profile() as session:
            checkpoint = session.read_checkpoint('release-1')
            journal = LiveJournal(session, checkpoint, '123', 'http://127.0.0.1:9437', existing=True)
            self.assertEqual(journal.value['events'][-1]['outcome'], 'verified_subset')
            self.assertEqual(checkpoint['manifest'], self.manifest)

    def test_script_help_and_invalid_arguments_redact_values(self):
        script = Path(__file__).resolve().parents[1] / 'scripts/upload_draft.py'
        result = subprocess.run([sys.executable, str(script), '--help'], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0)
        self.assertIn('--reconcile-readback-only', result.stdout)
        result = subprocess.run([sys.executable, str(script), '--unknown-private-value'],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn('--unknown-private-value', result.stdout + result.stderr)

    def test_fresh_save_timeout_is_unknown_and_never_retried(self):
        path = self.manifest_file()
        browser, factory = self.browser()
        def verify(ui):
            ui.identity_verified = True
        def create(ui):
            ui.remote_id = '456'
            ui.page.url = 'https://toolost.com/uploader/edit/456'
        with browser, patch.object(DraftUI, 'verify_account', verify), patch.object(DraftUI, 'create', create), \
                patch.object(DraftUI, 'artwork'), patch.object(DraftUI, 'audio'), \
                patch.object(DraftUI, 'metadata'), patch.object(DraftUI, 'save', side_effect=TimeoutError) as save, \
                patch.object(DraftUI, 'readback') as readback:
            with self.assertRaises(TimeoutError):
                execute(path, **self.kwargs())
            save.assert_called_once()
            readback.assert_not_called()
        with self.profile() as session:
            checkpoint = session.read_checkpoint('release-1')
            journal = LiveJournal(session, checkpoint, '123', 'http://127.0.0.1:9437', existing=True)
            self.assertEqual(journal.value['events'][-1]['operation'], 'save')
            self.assertEqual(journal.value['events'][-1]['outcome'], 'unknown')
        with self.assertRaisesRegex(storage.StorageError, 'checkpoint_exists'):
            execute(path, **self.kwargs())

    def test_actual_journal_intent_failure_never_calls_ui_operation(self):
        ui, page = self.ui()
        ui.identity_verified = True
        with self.profile() as session:
            journal = self.journal(session)
            ui.record = journal.record
            operation = Mock()
            with patch('toolost_uploader.live_journal._atomic_write', side_effect=storage.StorageError('write_failed')):
                with self.assertRaises(storage.StorageError):
                    ui.action('create', operation)
            operation.assert_not_called()
            self.assertEqual(journal.read()['events'], [])

    def test_account_change_after_action_does_not_claim_observed(self):
        ui, page = self.ui()
        ui.identity_verified = True
        def operation():
            ui.identity_changed = True
        with self.assertRaisesRegex(DraftError, 'identity_preflight_required_or_changed'):
            ui.action('save', operation)
        ui.record.assert_called_once_with('save', 'unknown', None)


if __name__ == '__main__':
    unittest.main()
