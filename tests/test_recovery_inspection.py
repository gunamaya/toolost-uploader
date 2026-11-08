import unittest
from copy import deepcopy
from unittest.mock import patch

from toolost_uploader.live_journal import DraftError
from toolost_uploader.recovery_inspection import (compare_snapshot, observe_open_draft,
                                                  prepare_review, verify_open_draft_account,
                                                  verify_review, verify_account_on_separate_tab,
                                                  review_track_labels, inspect_existing_tracks, inspect_connected_draft)


class FakeLocator:
    def __init__(self, count=0, texts=None):
        self._count, self._texts = count, texts or []

    def count(self):
        return self._count

    def all_inner_texts(self):
        return list(self._texts)


class FakePage:
    def __init__(self, account='12', url='https://toolost.com/uploader/edit/34',
                 closed=False, dialogs=0, login_fields=0, error=None, labels=None):
        self.account, self.url, self.closed = account, url, closed
        self.dialogs, self.login_fields, self.error = dialogs, login_fields, error
        self.labels = ['1 a.wav', '2 b.wav'] if labels is None else labels
        self.evaluated = []
        self.context = object()

    def is_closed(self):
        return self.closed

    def locator(self, _selector):
        if 'track-item' in _selector:
            return FakeLocator(texts=self.labels)
        return FakeLocator(self.dialogs if 'dialog' in _selector else self.login_fields)

    def evaluate(self, script):
        self.evaluated.append(script)
        if self.error:
            raise self.error
        return self.account


class ExistingTrackInspectionTests(unittest.TestCase):
    def test_same_context_account_and_labels(self):
        manifest = {'tracks': [{'track_id': 'a', 'audio': {'path': '01 - song.flac'}}]}
        page = FakePage(labels=['101 - songEdit'])
        result = inspect_existing_tracks(page, manifest=manifest, expected_account='12', expected_draft='34')
        self.assertEqual(result['matched_track_ids'], ['a'])
        self.assertEqual(len(page.evaluated), 2)

    def test_account_change_and_empty_dialog_fail_closed(self):
        manifest = {'tracks': [{'track_id': 'a', 'audio': {'path': 'a.wav'}}]}
        page = FakePage(labels=['1 a Edit'])
        page.evaluate = unittest.mock.Mock(side_effect=['12', '13'])
        with self.assertRaises(DraftError):
            inspect_existing_tracks(page, manifest=manifest, expected_account='12', expected_draft='34')
        with self.assertRaises(DraftError):
            inspect_existing_tracks(FakePage(dialogs=1), manifest=manifest, expected_account='12', expected_draft='34')


class RecoverySnapshotTests(unittest.TestCase):
    def setUp(self):
        self.manifest = {'tracks': [
            {'track_id': 'a', 'audio': {'path': 'a.wav'}},
            {'track_id': 'b', 'audio': {'path': 'b.wav'}},
        ]}
        self.observation = {'account': '12', 'profile': 'test', 'url': 'https://toolost.com/uploader/edit/34',
                            'closed': False, 'dialog_count': 0, 'login_visible': False,
                            'track_labels': ['1b.wavEdit', '2aEdit']}

    def compare(self):
        return compare_snapshot(manifest=self.manifest, expected_account='12', expected_profile='test',
                                expected_draft='34', observation=self.observation)

    def test_existing_tracks_review_handles_numbered_files_and_missing(self):
        manifest = {'tracks': [{'track_id': 'a', 'title': 'First Song', 'audio': {'path': '01 - First Song.flac'}},
                               {'track_id': 'b', 'title': 'Second Song', 'audio': {'path': '02 - Second Song.flac'}}]}
        with patch('toolost_uploader.recovery_inspection.verify_account_on_separate_tab'):
            result = inspect_existing_tracks(FakePage(labels=['102 - Second SongEdit']), manifest=manifest,
                                             expected_account='12', expected_draft='34')
        self.assertEqual(result['matched_track_ids'], ['b'])
        self.assertEqual(result['missing_track_ids'], ['a'])
        self.assertFalse(result['retry_safe'])

    def test_connected_inspection_requires_exactly_one_existing_page(self):
        from types import SimpleNamespace
        page = FakePage(labels=['1 a Edit'])
        browser = SimpleNamespace(contexts=[SimpleNamespace(pages=[page])])
        with patch('toolost_uploader.recovery_inspection.verify_account_on_separate_tab'):
            result = inspect_connected_draft(browser, manifest=self.manifest, expected_account='12', expected_draft='34')
        self.assertEqual(result['matched_track_ids'], ['a'])
        self.assertFalse(result['execution_available'])
        for pages in ([], [page, page]):
            browser.contexts[0].pages = pages
            with self.assertRaisesRegex(DraftError, 'recovery_page_not_unique'):
                inspect_connected_draft(browser, manifest=self.manifest, expected_account='12', expected_draft='34')
        self.assertFalse(result['persisted_state_verified'])

    def test_review_tolerates_punctuation_but_rejects_collisions_and_duplicates(self):
        result = review_track_labels(self.manifest, ['1 A.wav Edit', '2 b.wav Edit'])
        self.assertEqual(result['matched_track_ids'], ['a', 'b'])
        with self.assertRaises(DraftError):
            review_track_labels(self.manifest, ['1 a Edit', '2 A Edit'])
        manifest = deepcopy(self.manifest)
        manifest['tracks'][1]['audio']['path'] = 'a!.mp3'
        with self.assertRaises(DraftError):
            review_track_labels(manifest, [])

    def test_edit_suffix_is_matched_only_if_unambiguous(self):
        manifest = {'tracks': [{'track_id': 'a', 'title': 'Radio Edit', 'audio': {'path': 'song.wav'}}]}
        self.assertEqual(review_track_labels(manifest, ['1 Radio Edit'])['matched_track_ids'], ['a'])
        self.assertEqual(review_track_labels(manifest, ['1 Radio EditEdit'])['matched_track_ids'], ['a'])
        manifest['tracks'].append({'track_id': 'b', 'title': 'Radio', 'audio': {'path': 'other.wav'}})
        with self.assertRaisesRegex(DraftError, 'recovery_snapshot_ambiguous'):
            review_track_labels(manifest, ['1 Radio Edit'])

    def test_unicode_and_punctuation_title_matching_remains_unique(self):
        manifest = {'tracks': [{'track_id': 'a', 'title': 'Café - SOIR!', 'audio': {'path': 'a.wav'}},
                               {'track_id': 'b', 'title': 'Autre', 'audio': {'path': 'b.wav'}}]}
        self.assertEqual(review_track_labels(manifest, ['1 Cafe\u0301 soir Edit'])['matched_track_ids'], ['a'])
        manifest['tracks'][1]['title'] = 'CAFÉ soir'
        with self.assertRaisesRegex(DraftError, 'recovery_snapshot_ambiguous'):
            review_track_labels(manifest, ['1 Café soir Edit'])

    def test_empty_or_unknown_labels_never_authorize_retry(self):
        with patch('toolost_uploader.recovery_inspection.verify_account_on_separate_tab'):
            with self.assertRaises(DraftError):
                inspect_existing_tracks(FakePage(labels=[]), manifest=self.manifest,
                                        expected_account='12', expected_draft='34')
        result = review_track_labels(self.manifest, ['1 mystery Edit'])
        self.assertEqual(result['unexpected_labels'], ['mystery'])
        self.assertFalse(result['retry_safe'])

    def test_reversed_snapshot_is_not_identity_or_hash_proof(self):
        result = self.compare()
        self.assertEqual(result['observed_order'], ['b', 'a'])
        self.assertEqual(result['desired_order'], ['a', 'b'])
        self.assertTrue(result['reorder_required'])
        self.assertFalse(result['identity_verified'])
        self.assertFalse(result['remote_audio_hashes_verified'])
        self.assertNotIn('12', str(result))

    def test_ambiguity_fails_closed(self):
        for key, value in [('account', '13'), ('profile', 'other'), ('closed', True),
                           ('dialog_count', 1), ('dialog_count', False), ('login_visible', True),
                           ('url', 'https://toolost.com/uploader/edit/34?token=x'),
                           ('track_labels', ['1aEdit', '2aEdit']), ('track_labels', ['1aEdit'])]:
            with self.subTest(key=key, value=value):
                before = deepcopy(self.observation)
                self.observation[key] = value
                with self.assertRaises(DraftError):
                    self.compare()
                self.observation = before

    def test_review_binds_manifest_observation_and_requires_approval(self):
        args = dict(manifest=self.manifest, expected_account='12', expected_profile='test',
                    expected_draft='34', observation=self.observation)
        review = prepare_review(**args)
        self.assertFalse(review['execution_available'])
        self.assertTrue(verify_review(approved_digest=review['review_digest'], **args)['approval_matches_snapshot'])
        for digest in (None, '', '0' * 64):
            with self.assertRaises(DraftError):
                verify_review(approved_digest=digest, **args)
        self.manifest['tracks'][0]['lyrics'] = {'path': 'changed.txt'}
        with self.assertRaises(DraftError):
            verify_review(approved_digest=review['review_digest'], **args)
        self.manifest['tracks'][0].pop('lyrics')
        self.observation['track_labels'].reverse()
        with self.assertRaises(DraftError):
            verify_review(approved_digest=review['review_digest'], **args)

    def test_duplicate_manifest_label_and_track_id_rejected(self):
        self.manifest['tracks'][1]['audio']['path'] = 'a.mp3'
        with self.assertRaises(DraftError):
            self.compare()
        self.manifest['tracks'][1]['audio']['path'] = 'b.wav'
        self.manifest['tracks'][1]['track_id'] = 'a'
        with self.assertRaises(DraftError):
            self.compare()

    def test_non_navigation_request_verifies_same_page_account(self):
        page = FakePage()
        result = verify_open_draft_account(page, expected_account='12', expected_draft='34')
        self.assertTrue(result['account_verified'])
        self.assertFalse(result['profile_verified'])
        self.assertFalse(result['persisted_state_verified'])
        self.assertEqual(len(page.evaluated), 1)
        self.assertIn("credentials: 'same-origin'", page.evaluated[0])
        self.assertIn("redirect: 'error'", page.evaluated[0])

    def test_non_navigation_identity_fails_closed_for_fake_failures(self):
        cases = [
            FakePage(account='13'), FakePage(url='https://toolost.com/uploader/edit/35'),
            FakePage(dialogs=1), FakePage(login_fields=1), FakePage(error=RuntimeError()),
        ]
        for page in cases:
            with self.subTest(page=page):
                with self.assertRaises(DraftError) as raised:
                    verify_open_draft_account(page, expected_account='12', expected_draft='34')
                self.assertEqual(str(raised.exception), 'recovery_identity_unverified')

    def test_non_navigation_identity_rejects_invalid_targets(self):
        for account, draft in [('0', '34'), ('12', '0'), ('12', '34?x=1')]:
            with self.subTest(account=account, draft=draft):
                with self.assertRaises(DraftError):
                    verify_open_draft_account(FakePage(), expected_account=account, expected_draft=draft)

    def test_page_change_during_request_is_rejected(self):
        page = FakePage()
        def changed(_script):
            page.url = 'https://toolost.com/uploader/edit/35'
            return '12'
        page.evaluate = changed
        with self.assertRaises(DraftError):
            verify_open_draft_account(page, expected_account='12', expected_draft='34')

    def test_observe_open_draft_reads_without_navigation(self):
        page = FakePage(labels=['1 a.wav', '2 b.wav'])
        result = observe_open_draft(page, expected_account='12', expected_draft='34')
        self.assertTrue(result['read_only'])
        self.assertEqual(result['observation']['track_labels'], ['1 a.wav', '2 b.wav'])
        self.assertEqual(len(page.evaluated), 2)

    def test_observe_open_draft_rejects_empty_labels(self):
        with self.assertRaises(DraftError):
            observe_open_draft(FakePage(labels=[]), expected_account='12', expected_draft='34')

    def test_verify_account_uses_and_closes_only_new_tab(self):
        class Response:
            url = 'https://toolost.com/api/auth/me'
            status = 200
            def json(self): return {'user': {'id': 12}}
        class Portal:
            closed = False
            def on(self, _event, callback): self.callback = callback
            def goto(self, *_args, **_kwargs): self.callback(Response())
            def get_by_role(self, *_args, **_kwargs): return self
            def wait_for(self, **_kwargs): pass
            def wait_for_timeout(self, _ms): pass
            def close(self): self.closed = True
        class Context:
            def __init__(self): self.portal = Portal()
            def new_page(self): return self.portal
        context = Context()
        self.assertTrue(verify_account_on_separate_tab(context, expected_account='12')['account_verified'])
        self.assertTrue(context.portal.closed)


if __name__ == '__main__':
    unittest.main()
