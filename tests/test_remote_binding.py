import unittest
from unittest.mock import Mock

from toolost_uploader.live_journal import DraftError
from toolost_uploader.remote_binding import observe_release


class ObservationTests(unittest.TestCase):
    def test_observation_requires_account_and_matching_release(self):
        context = Mock()
        context.pages = []
        page = context.new_page.return_value
        page.url = 'https://toolost.com/uploader/edit/34'
        def go(*args, **kwargs):
            callback = page.on.call_args.args[1]
            for url, payload in [('https://toolost.com/api/auth/me', {'user': {'id': 12}}),
                                 ('https://toolost.com/api/distribution/release/34', {'info': {'id': 34, 'user_id': 12}, 'tracks': []})]:
                r = Mock(url=url, status=200);r.json.return_value = payload;callback(r)
        page.goto.side_effect = go
        self.assertEqual(observe_release(context, account='12', draft='34'), [])
        page.close.assert_called_once()
from toolost_uploader.remote_binding import prepare_binding, confirm_binding, propose_mapping, save_review_receipt


class RemoteBindingTests(unittest.TestCase):
    def setUp(self):
        self.args = dict(manifest={'tracks': [{'track_id': 'a'}, {'track_id': 'b'}]}, account='1', draft='2',
                         tracks=[{'id': 42, 'title': 'Song', 'track_order': 1, 'audio_url': 'https://example.test/private'}],
                         mapping={'a': '42'})

    def test_confirmation_is_snapshot_only(self):
        review = prepare_binding(**self.args)
        receipt = confirm_binding(approved_digest=review['review_digest'], **self.args)
        self.assertEqual(receipt['missing_track_ids'], ['b'])
        self.assertFalse(receipt['retry_safe'])
        self.assertFalse(receipt['remote_audio_hashes_verified'])
        self.assertFalse(receipt['persisted_state_verified'])
        self.assertNotIn('https://example.test/private', str(receipt))

    def test_changes_invalidate_review(self):
        digest = prepare_binding(**self.args)['review_digest']
        self.args['tracks'][0]['audio_url'] += '?changed'
        with self.assertRaises(DraftError):
            confirm_binding(approved_digest=digest, **self.args)

    def test_duplicate_and_unknown_bindings_fail(self):
        self.args['mapping']['b'] = '42'
        with self.assertRaises(DraftError):
            prepare_binding(**self.args)

    def test_duplicate_local_normalized_titles_fail_even_without_remote_match(self):
        manifest = {'tracks': [{'track_id': 'a', 'title': 'No, thanks'},
                               {'track_id': 'b', 'title': 'No thanks'}]}
        with self.assertRaises(DraftError):
            propose_mapping(manifest, [])

    def test_punctuation_tolerated_when_unique(self):
        manifest = {'tracks': [{'track_id': 'a', 'title': 'No, thanks'}]}
        self.assertEqual(propose_mapping(manifest, [{'id': 42, 'title': 'no thanks'}]), {'a': '42'})

    def test_receipt_is_private_and_rejects_stale_or_duplicate_approval(self):
        import tempfile
        from pathlib import Path
        from toolost_uploader.storage import profile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve() / 'private'
            review = {**prepare_binding(**self.args), 'status': 'review_only', 'account_verified': True,
                      'draft_verified': True, 'observation_provenance_verified': True}
            with profile('test', root=root) as session:
                with self.assertRaises(DraftError):
                    save_review_receipt(session, release_id='release', account='1', draft='2', review=review, approved_digest='0'*64)
                result = save_review_receipt(session, release_id='release', account='1', draft='2', review=review, approved_digest=review['review_digest'])
                self.assertFalse(result['retry_safe'])
                self.assertEqual(result, save_review_receipt(session, release_id='release', account='1', draft='2', review=review, approved_digest=review['review_digest']))
            path = root / 'profiles/test/checkpoints/release.binding.json'
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.args['mapping'] = {'a': '99'}
        with self.assertRaises(DraftError):
            prepare_binding(**self.args)

    def test_duplicate_remote_ids_and_order_fail(self):
        self.args['tracks'].append(dict(self.args['tracks'][0]))
        with self.assertRaises(DraftError):
            prepare_binding(**self.args)


if __name__ == '__main__':
    unittest.main()
