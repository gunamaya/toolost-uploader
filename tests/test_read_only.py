import unittest
from unittest.mock import Mock

from toolost_uploader.read_only import ObservationError, parse_snapshot, observe_page


class ReadOnlyTests(unittest.TestCase):
    def list_snapshot(self, cards=None):
        return {'kind': 'list', 'auth': False, 'dialog': False, 'ready': True,
                'cards': cards if cards is not None else [{'title': 'Synthetic release', 'href': '/user-portal/releases/view/123/info'}]}

    def detail_snapshot(self, title='Synthetic release', tracks=None):
        return {'kind': 'detail', 'auth': False, 'dialog': False, 'ready': True,
                'title': title, 'edit_href': '/uploader/edit/123', 'tracks': tracks if tracks is not None else ['Track A']}

    def error(self, code, url, snapshot):
        with self.assertRaises(ObservationError) as error:
            parse_snapshot(url, snapshot)
        self.assertEqual(error.exception.code, code)

    def test_list_is_partial_and_does_not_claim_account(self):
        result = parse_snapshot('https://toolost.com/user-portal/releases/manage/1', self.list_snapshot())
        self.assertEqual(result['items'][0]['remote_release_id'], '123')
        self.assertIsNone(result['account_identity'])
        self.assertFalse(result['account_verified'])
        self.assertEqual(result['items'][0]['remote_status']['normalized'], 'unknown')
        self.assertFalse(result['coverage']['complete'])

    def test_detail_identity_and_track_ids_unknown(self):
        result = parse_snapshot('https://toolost.com/user-portal/releases/view/123/info', self.detail_snapshot())
        self.assertEqual(result['remote_release_id'], '123')
        self.assertIsNone(result['tracks'][0]['remote_track_id'])
        self.assertFalse(result['tracks'][0]['identity_verified'])

    def test_guards(self):
        self.error('unsupported_page', 'https://toolost.com/user-portal/releases/manage/1?x=1', self.list_snapshot())
        self.error('unsupported_page', 'https://evil.test/user-portal/releases/manage/1', self.list_snapshot())
        for key, value, code in (('auth', True, 'login_required_or_unknown'),
                                 ('dialog', True, 'active_dialog'), ('ready', False, 'incomplete_observation')):
            data = self.list_snapshot(); data[key] = value
            self.error(code, 'https://toolost.com/user-portal/releases/manage/1', data)
        self.error('release_identity_unverified', 'https://toolost.com/user-portal/releases/view/123/info',
                   dict(self.detail_snapshot(), edit_href='/uploader/edit/999'))

    def test_duplicate_and_empty_are_not_absence(self):
        self.error('ambiguous_release_identity', 'https://toolost.com/user-portal/releases/manage/1', self.list_snapshot([
            {'title': 'A', 'href': '/user-portal/releases/view/123/info'},
            {'title': 'B', 'href': '/user-portal/releases/view/123/info'},
        ]))
        self.error('empty_or_incomplete_observation', 'https://toolost.com/user-portal/releases/manage/1', self.list_snapshot([]))
        self.error('incomplete_observation', 'https://toolost.com/user-portal/releases/view/123/info',
                   dict(self.detail_snapshot(), tracks=[None]))

    def test_unknown_and_null_fields_are_not_reconstructed(self):
        data = self.detail_snapshot(); data['title'] = '  '
        self.error('incomplete_observation', 'https://toolost.com/user-portal/releases/view/123/info', data)
        data = self.detail_snapshot(); data['edit_href'] = None
        self.error('release_identity_unverified', 'https://toolost.com/user-portal/releases/view/123/info', data)

    def test_collector_reads_only_evaluate_and_detects_navigation(self):
        page = Mock()
        page.url = 'https://toolost.com/user-portal/releases/view/123/info'
        page.evaluate.return_value = self.detail_snapshot()
        self.assertEqual(observe_page(page)['kind'], 'detail')
        self.assertEqual([call[0] for call in page.method_calls], ['evaluate'])

        def navigate(*args):
            page.url = 'https://toolost.com/login'
            return self.detail_snapshot()

        page.evaluate.side_effect = navigate
        with self.assertRaises(ObservationError) as error:
            observe_page(page)
        self.assertEqual(error.exception.code, 'page_changed')

    def test_collector_error_is_redacted(self):
        page = Mock()
        page.url = 'https://toolost.com/user-portal/releases/view/123/info'
        page.evaluate.side_effect = RuntimeError('PRIVATE COOKIE SECRET')
        with self.assertRaises(ObservationError) as error:
            observe_page(page)
        self.assertEqual(str(error.exception), 'observation_failed')


if __name__ == '__main__':
    unittest.main()
