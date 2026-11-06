import unittest
from pathlib import Path
from unittest.mock import Mock

from toolost_uploader.live_draft import DraftUI, DraftError


class Row:
    def __init__(self, page, index):
        self.page, self.index = page, index

    def text_content(self):
        return f'{self.index + 1}{self.page.order[self.index]}Edit'

    def scroll_into_view_if_needed(self):
        self.page.top = max(0, self.index - 1)

    def evaluate(self, _script):
        self.page.top = max(0, self.index - 1)

    def locator(self, selector):
        return self

    def bounding_box(self):
        return dict(x=10, y=(self.index - self.page.top) * 60, width=200, height=50)


class BatchPage:
    def __init__(self, order, *, no_op=False, fail_move=False, unsafe=False):
        self.order = order[:]
        self.top = 0
        self.no_op, self.fail_move = no_op, fail_move
        self.unsafe = unsafe
        self.source = None
        self.down_count = self.up_count = 0
        self.mouse = self

    def locator(self, selector):
        return self

    def count(self):
        return len(self.order)

    def nth(self, index):
        return Row(self, index)

    def move(self, x, y, **kwargs):
        if not 0 <= y < 180:
            raise RuntimeError('pointer_outside_viewport')
        if self.source is not None and self.fail_move:
            raise RuntimeError('drag_failed')
        self.pointer_index = self.top + int(y // 60)

    def down(self):
        self.down_count += 1
        self.source = self.pointer_index

    def up(self):
        self.up_count += 1
        if not self.no_op and not self.fail_move:
            self.order.insert(self.pointer_index, self.order.pop(self.source))
        self.source = None

    def wait_for_timeout(self, timeout):
        pass

    def evaluate(self, _script, _coordinates):
        return not self.unsafe


class ReorderTests(unittest.TestCase):
    def make_ui(self, order, **kwargs):
        ui = object.__new__(DraftUI)
        ui.manifest = {'tracks': [{'audio': {'path': f'track{i:03}.mp3'}} for i in range(1, len(order) + 1)]}
        ui.page = BatchPage([f'track{i:03}' for i in order], **kwargs)
        ui.guard_target = Mock()
        return ui

    def test_batch25_reorders_across_viewport(self):
        ui = self.make_ui([10, 19, 7, 12, 8, 21, 1, 16, 18, 5, 17, 20, 11, 13, 2, 24, 6, 4, 9, 23, 14, 22, 3, 15, 25])
        ui.reorder_tracks()
        self.assertEqual(ui.page.order, [Path(t['audio']['path']).stem for t in ui.manifest['tracks']])
        self.assertEqual(ui.page.down_count, ui.page.up_count)

    def test_unknown_later_track_blocks_all_drag(self):
        ui = self.make_ui([2, 1, 3])
        ui.page.order[-1] = 'unknown'
        with self.assertRaisesRegex(DraftError, 'track_identity_ambiguous'):
            ui.reorder_tracks()
        self.assertEqual(ui.page.down_count, 0)

    def test_no_progress_stops_without_retry(self):
        ui = self.make_ui([2, 1], no_op=True)
        with self.assertRaisesRegex(DraftError, 'track_reorder_failed'):
            ui.reorder_tracks()
        self.assertEqual(ui.page.down_count, 1)

    def test_mouse_released_on_move_failure(self):
        ui = self.make_ui([2, 1], fail_move=True)
        with self.assertRaisesRegex(RuntimeError, 'drag_failed'):
            ui.reorder_tracks()
        self.assertEqual(ui.page.up_count, 1)

    def test_covered_or_offscreen_target_stops_before_mouse_down(self):
        ui = self.make_ui([2, 1], unsafe=True)
        with self.assertRaisesRegex(DraftError, 'track_reorder_target_not_visible'):
            ui.reorder_tracks()
        self.assertEqual(ui.page.down_count, 0)
