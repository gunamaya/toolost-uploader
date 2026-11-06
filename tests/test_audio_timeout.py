import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from toolost_uploader.live_draft import DraftError, audio_timeout_ms, wait_for_audio


class AudioTimeoutTests(unittest.TestCase):
    def test_size_bounds_and_batch_sum(self):
        self.assertEqual(audio_timeout_ms([{'buffer': b'x'}]), 240000)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'audio.wav'
            with path.open('wb') as stream:
                stream.truncate(256 * 1024 * 1024)
            self.assertEqual(audio_timeout_ms([str(path)]), 1144000)
            self.assertEqual(audio_timeout_ms([str(path), str(path)]), 1800000)

    def page(self, counts, dialogs):
        items = Mock(count=Mock(side_effect=counts))
        dialog = Mock(count=Mock(side_effect=dialogs))
        page = Mock()
        page.locator.side_effect = lambda selector: items if 'track-item' in selector else dialog
        return page

    def test_count_and_dialog_share_budget(self):
        page = self.page([0, 1, 1], [1, 1])
        with patch('toolost_uploader.live_draft.time.monotonic', return_value=0):
            with self.assertRaisesRegex(DraftError, 'audio_upload_timeout'):
                wait_for_audio(page, 1, 1000)
        self.assertEqual(page.wait_for_timeout.call_count, 2)

    def test_success_and_excess_count(self):
        wait_for_audio(self.page([1], [0]), 1, 1000)
        with self.assertRaisesRegex(DraftError, 'track_identity_ambiguous'):
            wait_for_audio(self.page([3], []), 2, 1000)

    def test_real_deadline_includes_slow_poll(self):
        page = self.page([0, 0], [])
        with patch('toolost_uploader.live_draft.time.monotonic', side_effect=[0, 2]):
            with self.assertRaisesRegex(DraftError, 'audio_upload_timeout'):
                wait_for_audio(page, 1, 1000)
        page.wait_for_timeout.assert_not_called()
