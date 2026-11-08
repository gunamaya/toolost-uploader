import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock

from toolost_uploader.live_draft import recovery_steps
from toolost_uploader.live_journal import DraftError, RecoveryJournal
from toolost_uploader.remote_binding import prepare_binding, save_review_receipt, load_receipt
from toolost_uploader.storage import profile, _atomic_write


class RecoveryTests(unittest.TestCase):
    def setup_run(self, session, count):
        manifest = {'release_id': 'r', 'title': 'Album', 'tracks': [
            {'track_id': 'a', 'title': 'One', 'audio': {'sha256': 'a' * 64}},
            {'track_id': 'b', 'title': 'Two', 'audio': {'sha256': 'b' * 64}}]}
        tracks = [{'id': i + 10, 'title': t['title'], 'track_order': i + 1,
                   'audio_url': 'https://audio.test/' + str(i)} for i, t in enumerate(manifest['tracks'][:count])]
        mapping = {t['track_id']: str(remote['id']) for t, remote in zip(manifest['tracks'], tracks)}
        review = dict(prepare_binding(manifest=manifest, account='1', draft='2', tracks=tracks, mapping=mapping),
                      status='review_only', account_verified=True, draft_verified=True, observation_provenance_verified=True)
        receipt = save_review_receipt(session, release_id='r', account='1', draft='2', review=review, approved_digest=review['review_digest'])
        ui = Mock(manifest=manifest)
        ui._audio_batch.side_effect = lambda ts, **kw: add(ts)
        ui._append_batch.side_effect = lambda ts, *a, **kw: add(ts)
        def add(ts):
            tracks.append({'id': len(tracks) + 10, 'title': ts[0]['title'],
                           'track_order': len(tracks) + 1, 'audio_url': 'https://audio.test/' + str(len(tracks))})
        ui.page.locator.return_value.count.return_value = 1
        journal = RecoveryJournal(session, manifest, '1', '2', 'http://127.0.0.1:9437')
        return ui, journal, receipt, tracks

    def test_all_some_none_upload_only_missing_and_restart_idempotent(self):
        for count in (0, 1, 2):
            with self.subTest(count=count), tempfile.TemporaryDirectory() as tmp:
                with profile('test', root=Path(tmp).resolve() / 'private') as session:
                    ui, journal, receipt, tracks = self.setup_run(session, count)
                    recovery_steps(ui, journal, receipt, lambda: deepcopy(tracks))
                    self.assertEqual(ui._audio_batch.call_count + ui._append_batch.call_count, 2 - count)
                    ui.create.assert_not_called()
                    ui.save.assert_called_once()
                    recovered = RecoveryJournal(session, ui.manifest, '1', '2', 'http://127.0.0.1:9437')
                    recovery_steps(ui, recovered, receipt, lambda: deepcopy(tracks))
                    ui.save.assert_called_once()

    def test_interrupted_unknown_upload_never_replayed(self):
        with tempfile.TemporaryDirectory() as tmp, profile('test', root=Path(tmp).resolve() / 'private') as session:
            ui, journal, receipt, tracks = self.setup_run(session, 0)
            ui._audio_batch.side_effect = RuntimeError('lost response')
            with self.assertRaises(RuntimeError):
                recovery_steps(ui, journal, receipt, lambda: deepcopy(tracks))
            with self.assertRaisesRegex(DraftError, 'upload_unknown'):
                recovery_steps(ui, journal, receipt, lambda: deepcopy(tracks))
            self.assertEqual(ui._audio_batch.call_count, 1)
            ui.save.assert_not_called()

    def test_snapshot_external_change_stops_before_mutation(self):
        with tempfile.TemporaryDirectory() as tmp, profile('test', root=Path(tmp).resolve() / 'private') as session:
            ui, journal, receipt, tracks = self.setup_run(session, 2)
            tracks[0]['audio_url'] += 'changed'
            with self.assertRaisesRegex(DraftError, 'review_changed'):
                recovery_steps(ui, journal, receipt, lambda: deepcopy(tracks))
            ui.save.assert_not_called()
            ui._append_batch.assert_not_called()

    def test_receipt_corruption_account_manifest_and_profile_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp, profile('test', root=Path(tmp).resolve() / 'private') as session:
            ui, journal, receipt, tracks = self.setup_run(session, 2)
            for account, draft, manifest in [('9', '2', ui.manifest), ('1', '9', ui.manifest),
                                              ('1', '2', dict(ui.manifest, title='changed'))]:
                with self.assertRaises(DraftError):
                    load_receipt(session, manifest, account, draft)
            receipt['mapping']['a'] = '999'
            _atomic_write(session.directory, 'r.binding.json', receipt)
            with self.assertRaisesRegex(DraftError, 'corrupt'):
                load_receipt(session, ui.manifest, '1', '2')

    def test_metadata_failure_preserves_new_binding_before_retry(self):
        with tempfile.TemporaryDirectory() as tmp, profile('test', root=Path(tmp).resolve() / 'private') as session:
            ui, journal, receipt, tracks = self.setup_run(session, 1)
            ui.sync_metadata_and_order.side_effect = RuntimeError('interrupted')
            with self.assertRaises(RuntimeError):
                recovery_steps(ui, journal, receipt, lambda: deepcopy(tracks))
            self.assertEqual(journal.read()['mapping'], {'a': '10', 'b': '11'})
            with self.assertRaisesRegex(DraftError, 'unknown_requires_review'):
                recovery_steps(ui, journal, receipt, lambda: deepcopy(tracks))
            self.assertEqual(ui._append_batch.call_count, 1)

    def test_changed_during_run_stops_before_next_upload(self):
        with tempfile.TemporaryDirectory() as tmp, profile('test', root=Path(tmp).resolve() / 'private') as session:
            ui, journal, receipt, tracks = self.setup_run(session, 1)
            calls = 0
            def observe():
                nonlocal calls
                calls += 1
                result = deepcopy(tracks)
                if calls > 1:
                    result[0]['title'] = 'External edit'
                return result
            with self.assertRaisesRegex(DraftError, 'review_changed'):
                recovery_steps(ui, journal, receipt, observe)
            ui._append_batch.assert_not_called()

    def test_reconfirmation_idempotent_and_changed_review_keeps_history(self):
        with tempfile.TemporaryDirectory() as tmp, profile('test', root=Path(tmp).resolve() / 'private') as session:
            ui, journal, receipt, tracks = self.setup_run(session, 1)
            tracks[0]['title'] = 'Changed'
            review = dict(prepare_binding(manifest=ui.manifest, account='1', draft='2', tracks=tracks, mapping=receipt['mapping']),
                          status='review_only', account_verified=True, draft_verified=True, observation_provenance_verified=True)
            changed = save_review_receipt(session, release_id='r', account='1', draft='2', review=review, approved_digest=review['review_digest'])
            self.assertEqual(changed['history'][0], receipt)
            self.assertEqual(changed, save_review_receipt(session, release_id='r', account='1', draft='2', review=review, approved_digest=review['review_digest']))

    def test_cli_contract(self):
        import contextlib
        import io
        import json
        from unittest.mock import patch
        from toolost_uploader.cli import main
        out = io.StringIO()
        with patch('toolost_uploader.live_draft.recover', return_value={'status': 'draft_recovered_subset'}) as recover, contextlib.redirect_stdout(out):
            code = main(['recover', 'manifest.json', '--profile', 'test', '--expected-account', '1',
                         '--draft-id', '2', '--approve-draft', '--accept-ui-date', '--json'])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out.getvalue())['status'], 'draft_recovered_subset')
        self.assertEqual(recover.call_args.kwargs['draft_id'], '2')

    def test_save_response_lost_stops_and_retains_history(self):
        with tempfile.TemporaryDirectory() as tmp, profile('test', root=Path(tmp).resolve() / 'private') as session:
            ui, journal, receipt, tracks = self.setup_run(session, 2)
            ui.save.side_effect = RuntimeError('response lost')
            with self.assertRaises(RuntimeError):
                recovery_steps(ui, journal, receipt, lambda: deepcopy(tracks))
            self.assertEqual(journal.read()['events'][-1]['outcome'], 'unknown')
            with self.assertRaisesRegex(DraftError, 'unknown_requires_review'):
                recovery_steps(ui, journal, receipt, lambda: deepcopy(tracks))
            ui.save.assert_called_once()

    def test_profile_lock_blocks_other_writer(self):
        from toolost_uploader.storage import StorageError
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve() / 'private'
            with profile('test', root=root):
                with self.assertRaisesRegex(StorageError, 'profile_locked'):
                    with profile('test', root=root):
                        self.fail('second writer entered')


class LegacyRecoveryIntegrationTests(unittest.TestCase):
    """Exercise the public executor with real immutable storage, offline UI only."""

    def setUp(self):
        import test_storage
        test_storage.StorageTests.setUp(self)
        import hashlib
        lyrics = b'Synthetic lyrics only.\n'
        (self.base / 'lyrics.txt').write_bytes(lyrics)
        self.manifest['tracks'][0]['lyrics'] = {
            'path': 'lyrics.txt', 'sha256': hashlib.sha256(lyrics).hexdigest()}
        self.endpoint = 'http://127.0.0.1:9437'
        self.tracks = [{'id': 10, 'title': self.manifest['tracks'][0]['title'],
                        'track_order': 1, 'audio_url': 'https://audio.test/10'}]
        self.snapshot_base = self.base / 'unique-gui-snapshot'
        self.snapshot_base.mkdir()
        (self.snapshot_base / 'copied-audio.bin').write_bytes(self.asset.read_bytes())
        (self.snapshot_base / 'copied-artwork.bin').write_bytes(self.asset.read_bytes())
        (self.snapshot_base / 'copied-lyrics.txt').write_bytes(lyrics)
        self.replacement = deepcopy(self.manifest)
        self.replacement['artwork']['path'] = 'copied-artwork.bin'
        self.replacement['tracks'][0]['audio']['path'] = 'copied-audio.bin'
        self.replacement['tracks'][0]['lyrics']['path'] = 'copied-lyrics.txt'
        self.replacement['tracks'][0]['ai_assisted'] = False
        self.path = self.snapshot_base / 'manifest.json'
        import json
        self.path.write_text(json.dumps(self.replacement))

    def seed(self, *, account='1', draft='2', journal=True):
        from toolost_uploader.live_journal import LiveJournal
        with profile('test', root=self.root) as session:
            checkpoint = session.create_checkpoint(self.manifest, self.base)
            if journal:
                legacy = LiveJournal(session, checkpoint, account, self.endpoint)
                # A title amendment exercises validation against the OLD manifest.
                legacy.approve_title()
                legacy.record('create', 'unknown', None)
                legacy.record('create', 'observed', draft)
                legacy.record('artwork', 'unknown', draft)
                legacy.record('artwork', 'observed', draft)
                legacy.record('audio', 'unknown', draft)
                legacy.record_track('track-1', self.manifest['tracks'][0]['audio']['sha256'], 0, 'unknown')
                legacy.record_track('track-1', self.manifest['tracks'][0]['audio']['sha256'], 0, 'observed')
                legacy.record('audio', 'observed', draft)
                legacy.record('metadata', 'unknown', draft)
            review = dict(prepare_binding(manifest=self.replacement, account='1', draft='2',
                          tracks=self.tracks, mapping={t['track_id']: str(remote['id'])
                              for t, remote in zip(self.replacement['tracks'], self.tracks)}), status='review_only',
                          account_verified=True, draft_verified=True, observation_provenance_verified=True)
            save_review_receipt(session, release_id=self.manifest['release_id'], account='1', draft='2',
                                review=review, approved_digest=review['review_digest'])
        self.directory = self.root / 'profiles/test/checkpoints'
        self.historical = {p: p.read_bytes() for p in self.directory.iterdir()
                           if p.name.endswith(('.live.json', 'release-1.json'))}

    def invoke(self, *, update=False, failure=False):
        from unittest.mock import patch
        from toolost_uploader.live_draft import recover
        page, ui, context = Mock(), Mock(), Mock()
        context.new_page.return_value = page
        page.locator.return_value.count.return_value = 0
        ui.page.locator.return_value.count.return_value = 1
        ui.manifest = self.replacement
        if failure:
            ui.sync_metadata_and_order.side_effect = RuntimeError('metadata interrupted')
        with patch('playwright.sync_api.sync_playwright') as playwright, \
                patch('toolost_uploader.live_draft.DraftUI', return_value=ui) as factory, \
                patch('toolost_uploader.remote_binding.observe_release',
                      side_effect=lambda *a, **kw: deepcopy(self.tracks)) as observe:
            playwright.return_value.__enter__.return_value.chromium.connect_over_cdp.return_value.contexts = [context]
            kwargs = dict(alias='test', expected_account='1', endpoint=self.endpoint,
                          approve_draft=True, accept_ui_date=True, root=self.root)
            if update:
                from toolost_uploader.live_draft import execute
                result = execute(self.path, allow_update=True, **kwargs)
            else:
                result = recover(self.path, draft_id='2', **kwargs)
        return result, ui, factory, observe

    def assert_history_unchanged(self):
        for path, original in self.historical.items():
            self.assertEqual(path.read_bytes(), original)

    def test_reviewed_replacement_preserves_original_checkpoint_and_journal_bytes(self):
        from toolost_uploader.storage import _read
        self.seed()
        # Recovery must not depend on the historical assets still existing.
        self.asset.unlink()
        result, ui, factory, observe = self.invoke()
        self.assertEqual(result['status'], 'draft_recovered_subset')
        self.assertEqual(factory.call_args.args[1:3], (self.replacement, self.snapshot_base))
        ui.save.assert_called_once()
        ui.sync_metadata_and_order.assert_called_once()
        ui.create.assert_not_called()
        ui._audio_batch.assert_not_called()
        ui._append_batch.assert_not_called()
        self.assertGreater(observe.call_count, 1)
        self.assert_history_unchanged()
        with profile('test', root=self.root) as session:
            ledger = _read(session.directory, 'release-1.recovery.json')
        self.assertEqual(ledger['mapping'], {'track-1': '10'})
        self.assertEqual(ledger['events'][-1]['operation'], 'complete')

    def test_album_with_lyrics_on_every_track_public_recovery_fresh_paths(self):
        for manifest in (self.manifest, self.replacement):
            manifest['release_type'] = 'album'
            second = deepcopy(manifest['tracks'][0])
            second.update(track_id='track-2', title='Second synthetic track')
            manifest['tracks'].append(second)
        self.tracks.append(dict(id=11, title='Second synthetic track', track_order=2,
                                audio_url='https://audio.test/11'))
        import json
        self.path.write_text(json.dumps(self.replacement))
        self.seed()
        with self.assertRaisesRegex(RuntimeError, 'metadata interrupted'):
            self.invoke(failure=True)
        self.fresh_copy()
        self.public_review()
        result, ui, factory, _ = self.invoke()
        self.assertEqual(result['status'], 'draft_recovered_subset')
        self.assertEqual(factory.call_args.args[1:3], (self.replacement, self.snapshot_base))
        for track in self.replacement['tracks']:
            self.assertTrue((self.snapshot_base / track['lyrics']['path']).is_file())
        ui.save.assert_called_once()
        ui._audio_batch.assert_not_called()
        ui._append_batch.assert_not_called()
        self.assert_history_unchanged()

    def test_checkpoint_without_legacy_journal_allows_reviewed_replacement(self):
        self.seed(journal=False)
        self.assertEqual(self.invoke()[0]['status'], 'draft_recovered_subset')
        self.assert_history_unchanged()

    def test_legacy_account_or_draft_conflict_stops_before_browser(self):
        from unittest.mock import patch
        for account, draft, code in [('9', '2', 'journal_binding_mismatch'),
                                     ('1', '9', 'draft_target_changed')]:
            with self.subTest(account=account, draft=draft):
                # Each case gets its own genuine original storage.
                self.root = self.base / ('state-' + account + '-' + draft)
                self.seed(account=account, draft=draft)
                with patch('playwright.sync_api.sync_playwright') as browser:
                    with self.assertRaisesRegex(DraftError, code):
                        self.invoke()
                    browser.assert_not_called()
                self.assert_history_unchanged()
                self.assertFalse((self.directory / 'release-1.recovery.json').exists())

    def test_corrupt_legacy_journal_rejected_without_rewriting_history(self):
        self.seed()
        import json
        path = self.directory / 'release-1.live.json'
        value = json.loads(path.read_text())
        value['record_sha256'] = '0' * 64
        path.write_text(json.dumps(value))
        self.historical[path] = path.read_bytes()
        with self.assertRaisesRegex(DraftError, 'journal_hash_mismatch'):
            self.invoke()
        self.assert_history_unchanged()

    def test_replacement_without_matching_receipt_stops_before_browser(self):
        from unittest.mock import patch
        from toolost_uploader.storage import _read, _digest
        self.seed()
        for field, value in [('account', '9'), ('draft', '9'), ('profile', 'other'),
                             ('manifest_sha256', '0' * 64)]:
            with self.subTest(field=field), profile('test', root=self.root) as session:
                receipt = _read(session.directory, 'release-1.binding.json')
                changed = deepcopy(receipt)
                changed[field] = value
                changed['record_sha256'] = _digest({k: v for k, v in changed.items() if k != 'record_sha256'})
                _atomic_write(session.directory, 'release-1.binding.json', changed)
            with patch('playwright.sync_api.sync_playwright') as browser:
                with self.assertRaisesRegex(DraftError, 'remote_binding_identity_mismatch'):
                    self.invoke()
                browser.assert_not_called()
            with profile('test', root=self.root) as session:
                _atomic_write(session.directory, 'release-1.binding.json', receipt)
            self.assert_history_unchanged()

    def test_corrupt_original_checkpoint_rejected(self):
        from toolost_uploader.storage import StorageError
        import json
        self.seed()
        path = self.directory / 'release-1.json'
        value = json.loads(path.read_text())
        value['manifest']['title'] = 'tampered'
        path.write_text(json.dumps(value))
        self.historical[path] = path.read_bytes()
        with self.assertRaisesRegex(StorageError, 'manifest_hash_mismatch'):
            self.invoke()
        self.assert_history_unchanged()

    def fresh_copy(self, *, metadata=False):
        import json
        target = self.base / ('snapshot-' + str(len(list(self.base.glob('snapshot-*')))))
        target.mkdir()
        assets = [self.replacement['artwork']]
        for track in self.replacement['tracks']:
            assets.extend(track[key] for key in ('audio', 'lyrics') if key in track)
        for asset in assets:
            name = 'new-' + Path(asset['path']).name
            (target / name).write_bytes((self.snapshot_base / asset['path']).read_bytes())
            asset['path'] = name
        if metadata:
            self.replacement['tracks'][0]['ai_assisted'] = not self.replacement['tracks'][0]['ai_assisted']
        self.snapshot_base = target
        self.path = target / 'manifest.json'
        self.path.write_text(json.dumps(self.replacement))

    def public_review(self):
        from unittest.mock import patch
        from toolost_uploader.remote_binding import review_live
        from toolost_uploader.storage import _read
        with profile('test', root=self.root) as session:
            ledger = _read(session.directory, 'release-1.recovery.json')
        with patch('playwright.sync_api.sync_playwright') as playwright, \
                patch('toolost_uploader.remote_binding.observe_release', return_value=deepcopy(self.tracks)):
            playwright.return_value.__enter__.return_value.chromium.connect_over_cdp.return_value.contexts = [Mock()]
            review = review_live(self.path, account='1', draft='2', endpoint=self.endpoint,
                                 alias='test', observed_binding=ledger)
        with profile('test', root=self.root) as session:
            save_review_receipt(session, release_id='release-1', account='1', draft='2',
                                review=review, approved_digest=review['review_digest'])
        return review

    def test_failed_normal_upload_public_review_recover_fresh_paths(self):
        from toolost_uploader.live_draft import normal_upload_audio
        from toolost_uploader.storage import _read
        self.seed()
        self.tracks.clear()
        ui = Mock(manifest=deepcopy(self.replacement), serial_audio=False, remote_id='2')
        def upload(tracks, **kwargs):
            self.tracks.append(dict(id=10, title=tracks[0]['title'], track_order=1, audio_url='https://audio.test/10'))
        ui._audio_batch.side_effect = upload
        with profile('test', root=self.root) as session:
            journal = RecoveryJournal(session, ui.manifest, '1', '2', self.endpoint)
            normal_upload_audio(ui, journal, lambda: deepcopy(self.tracks))
            journal.append('metadata_save', 'unknown')
            before = journal.read()
        # Normal upload has recorded unknown metadata intent before it failed.
        self.assertEqual(before['events'][-1]['outcome'], 'unknown')
        self.fresh_copy()
        self.public_review()
        result, recovered, _, _ = self.invoke()
        self.assertEqual(result['status'], 'draft_recovered_subset')
        recovered._audio_batch.assert_not_called()
        recovered._append_batch.assert_not_called()
        with profile('test', root=self.root) as session:
            after = _read(session.directory, 'release-1.recovery.json')
        self.assertEqual(after['events'][:len(before['events'])], before['events'])
        self.assert_history_unchanged()

    def test_failed_recovery_public_review_recover_fresh_paths(self):
        from toolost_uploader.storage import _read
        self.seed()
        with self.assertRaisesRegex(RuntimeError, 'metadata interrupted'):
            self.invoke(failure=True)
        with profile('test', root=self.root) as session:
            before = _read(session.directory, 'release-1.recovery.json')
        self.fresh_copy()
        self.public_review()
        self.assertEqual(self.invoke()[0]['status'], 'draft_recovered_subset')
        with profile('test', root=self.root) as session:
            after = _read(session.directory, 'release-1.recovery.json')
        self.assertEqual(after['events'][:len(before['events'])], before['events'])
        self.assert_history_unchanged()

    def test_recovered_public_update_unchanged_and_new_reviewed_metadata(self):
        for legacy in ('unknown', 'no_journal', 'no_checkpoint'):
            with self.subTest(legacy=legacy):
                self.root = self.base / ('update-' + legacy)
                if legacy == 'no_checkpoint':
                    # Explicit recovery can start from a receipt alone.
                    with profile('test', root=self.root) as session:
                        review = dict(prepare_binding(manifest=self.replacement, account='1', draft='2',
                            tracks=self.tracks, mapping={'track-1': '10'}), status='review_only',
                            account_verified=True, draft_verified=True, observation_provenance_verified=True)
                        save_review_receipt(session, release_id='release-1', account='1', draft='2',
                                            review=review, approved_digest=review['review_digest'])
                    self.historical = {}
                else:
                    self.seed(journal=legacy == 'unknown')
                self.invoke()
                unchanged, ui, _, _ = self.invoke(update=True)
                self.assertEqual(unchanged['status'], 'draft_updated_subset')
                ui.save.assert_not_called()
                ui.create.assert_not_called()
                self.fresh_copy(metadata=True)
                # Exact current snapshot approval is still mandatory.
                with self.assertRaisesRegex(DraftError, 'remote_binding_identity_mismatch'):
                    self.invoke(update=True)
                self.public_review()
                changed, ui, _, _ = self.invoke(update=True)
                self.assertEqual(changed['status'], 'draft_updated_subset')
                ui.sync_metadata_and_order.assert_called_once()
                ui.save.assert_called_once()
                ui.create.assert_not_called()
                ui._audio_batch.assert_not_called()
                ui._append_batch.assert_not_called()
                self.assert_history_unchanged()
                from toolost_uploader.storage import _read
                with profile('test', root=self.root) as session:
                    ledger = _read(session.directory, 'release-1.recovery.json')
                    successor = _read(session.directory, 'release-1.successor.json')
                self.assertEqual(ledger['history'][0]['events'][-1]['operation'], 'complete')
                self.assertEqual(successor['history'][0]['draft'], '2')

    def test_review_rejects_external_audio_but_allows_explicit_metadata_revision(self):
        self.seed()
        self.invoke()
        self.fresh_copy(metadata=True)
        self.tracks[0]['audio_url'] += '/external'
        with self.assertRaisesRegex(DraftError, 'remote_binding_review_changed'):
            self.public_review()

    def test_content_identity_excludes_only_asset_paths(self):
        from toolost_uploader.recovery_state import content_digest
        manifest = deepcopy(self.replacement)
        relocated = deepcopy(manifest)
        relocated['artwork']['path'] += '/new'
        relocated['tracks'][0]['audio']['path'] += '/new'
        relocated['tracks'][0]['lyrics']['path'] += '/new'
        self.assertEqual(content_digest(manifest), content_digest(relocated))
        for mutation in ('sha256', 'lyrics_sha256', 'lyrics_metadata', 'metadata', 'id', 'other_path', 'order'):
            changed = deepcopy(manifest)
            if mutation == 'sha256':
                changed['tracks'][0]['audio']['sha256'] = 'f' * 64
            elif mutation == 'lyrics_sha256':
                changed['tracks'][0]['lyrics']['sha256'] = 'f' * 64
            elif mutation == 'lyrics_metadata':
                changed['tracks'][0]['lyrics']['language'] = 'id'
            elif mutation == 'metadata':
                changed['tracks'][0]['ai_assisted'] = True
            elif mutation == 'id':
                changed['tracks'][0]['track_id'] = 'other'
            elif mutation == 'other_path':
                changed['path'] = 'meaningful metadata'
            else:
                second = deepcopy(changed['tracks'][0])
                second['track_id'] = 'second'
                changed['tracks'].append(second)
            self.assertNotEqual(content_digest(manifest), content_digest(changed))

    def test_failed_recovery_metadata_reapproval_preserves_unknown_and_history(self):
        from toolost_uploader.storage import _read
        self.seed()
        with self.assertRaisesRegex(RuntimeError, 'metadata interrupted'):
            self.invoke(failure=True)
        with profile('test', root=self.root) as session:
            before = _read(session.directory, 'release-1.recovery.json')
        self.fresh_copy(metadata=True)
        self.public_review()
        self.invoke()
        with profile('test', root=self.root) as session:
            after = _read(session.directory, 'release-1.recovery.json')
        self.assertEqual(after['history'][0], before)
        self.assertEqual(after['events'][:len(before['events'])], before['events'])
        self.assertEqual(before['events'][-1]['outcome'], 'unknown')

    def test_recovered_update_fresh_paths_requires_exact_new_receipt(self):
        self.seed()
        self.invoke()
        self.fresh_copy()
        with self.assertRaisesRegex(DraftError, 'remote_binding_identity_mismatch'):
            self.invoke(update=True)
        self.public_review()
        result, ui, _, _ = self.invoke(update=True)
        self.assertEqual(result['status'], 'draft_updated_subset')
        ui.create.assert_not_called()
        ui._audio_batch.assert_not_called()
        ui._append_batch.assert_not_called()
        self.assert_history_unchanged()
