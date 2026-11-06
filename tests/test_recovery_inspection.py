import unittest
from copy import deepcopy

from toolost_uploader.live_journal import DraftError
from toolost_uploader.recovery_inspection import (compare_snapshot, observe_open_draft,
                                                  prepare_review, verify_open_draft_account,
                                                  verify_review, verify_account_on_separate_tab)


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
