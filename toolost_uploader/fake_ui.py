"""Model UI sintetis deterministik; bukan DOM, Playwright atau layanan Too Lost."""

from copy import deepcopy

from .storage import _digest, _require


def _projection(state):
    return {"title": state["title"], "track_ids": [t["track_id"] for t in state["tracks"]],
            "metadata_sha256": _digest(state["tracks"])}


class FakeUI:
    def __init__(self, *, save_route="dialog", field_ticks=1, encoding_ticks=2):
        _require(save_route in ("dialog", "navigation", "error", "lost_response", "metadata_loss"), "invalid_fake_mode")
        _require(type(field_ticks) is int and field_ticks >= 0
                 and type(encoding_ticks) is int and encoding_ticks >= 1, "invalid_fake_delay")
        self.account = "synthetic-account"
        self.draft = "synthetic-draft"
        self.persisted = {"title": "Synthetic baseline", "tracks": []}
        self.staged = deepcopy(self.persisted)
        self.save_route = save_route
        self.field_ticks = field_ticks
        self.encoding_ticks = encoding_ticks
        self.visible_after = 0
        self.clock = 0
        self.panel = "main"
        self.active_track = None
        self.active_track = None
        self.selected = []
        self.encoding = None
        self.progress = 0
        self.upload_attempted = False
        self.upload_calls = 0
        self.save_calls = 0
        self.read_calls = 0
        self.read_error = False
        self.identity_verified = True
        self.complete = True
        self.save_dialogs = 0

    def tick(self):
        self.clock += 1
        if self.encoding is not None and self.clock >= self.encoding[0]:
            self.staged["tracks"].extend(reversed(self.encoding[1]))
            self.encoding = None
            self.panel = "main"

    def _main(self):
        _require(self.panel == "main" and self.clock >= self.visible_after, "fake_panel_not_ready")

    def open_upload(self):
        self._main()
        _require(not self.upload_attempted, "reconciliation_required")
        self.panel = "upload_dialog"

    def browse(self):
        _require(self.panel == "upload_dialog", "fake_wrong_scope")
        self.panel = "file_chooser"

    def select(self, tracks):
        _require(self.panel == "file_chooser", "fake_wrong_scope")
        _require(isinstance(tracks, list) and bool(tracks), "invalid_fake_tracks")
        for track in tracks:
            _require(isinstance(track, dict) and set(track) == {"track_id", "basename"}, "invalid_fake_tracks")
            _require(all(isinstance(v, str) and v.strip() for v in track.values()), "invalid_fake_tracks")
        ids = [t["track_id"] for t in tracks] + [t["track_id"] for t in self.staged["tracks"]]
        _require(len(ids) == len(set(ids)), "invalid_fake_tracks")
        self.selected = [dict(t, title=t["basename"], ai_assisted=False) for t in tracks]
        self.panel = "upload_dialog"

    def upload(self):
        _require(self.panel == "upload_dialog" and bool(self.selected), "fake_wrong_scope")
        _require(not self.upload_attempted, "reconciliation_required")
        self.upload_attempted = True
        self.upload_calls += 1
        self.progress = 100
        self.encoding = (self.clock + self.encoding_ticks, deepcopy(self.selected))
        self.panel = "encoding"

    def rows(self):
        self._main()
        _require(self.encoding is None, "fake_encoding_pending")
        names = [t["basename"] for t in self.staged["tracks"]]
        _require(len(names) == len(set(names)) and self.identity_verified, "reconciliation_required")
        return deepcopy(self.staged["tracks"])

    def reorder(self, track_ids):
        rows = self.rows()
        _require(isinstance(track_ids, list) and len(track_ids) == len(rows)
                 and len(set(track_ids)) == len(track_ids)
                 and set(track_ids) == {t["track_id"] for t in rows}, "fake_track_mapping_conflict")
        by_id = {t["track_id"]: t for t in rows}
        self.staged["tracks"] = [by_id[key] for key in track_ids]

    def edit_track(self, track_id):
        self.rows()
        _require(track_id in [t["track_id"] for t in self.staged["tracks"]], "fake_track_mapping_conflict")
        self.panel = "track_editor"
        self.active_track = track_id
        self.visible_after = self.clock + self.field_ticks

    def set_ai(self, value):
        _require(type(value) is bool, "invalid_fake_boolean")
        _require(self.panel == "track_editor"
                 and self.clock >= self.visible_after, "fake_panel_not_ready")
        self._track()["ai_assisted"] = value

    def _track(self):
        _require(self.panel == "track_editor", "fake_wrong_scope")
        matches = [t for t in self.staged["tracks"] if t["track_id"] == self.active_track]
        _require(len(matches) == 1, "fake_wrong_scope")
        return matches[0]

    def ai_readback(self):
        _require(self.clock >= self.visible_after, "fake_panel_not_ready")
        return {"native_checked": False, "aria_checked": self._track()["ai_assisted"]}

    def done(self):
        self._track()
        _require(self.clock >= self.visible_after, "fake_panel_not_ready")
        self.panel = "main"
        self.visible_after = self.clock + self.field_ticks

    def set_title(self, title):
        self._main()
        _require(isinstance(title, str) and title.strip(), "invalid_fake_title")
        self.staged["title"] = title

    def desired(self):
        self.rows()
        return _projection(self.staged)

    def save(self, desired):
        self.rows()
        _require(desired == self.desired(), "desired_mismatch")
        self.save_calls += 1
        if self.save_route == "dialog":
            self.panel = "save_dialog"
            self.save_dialogs += 1
            # Satu konfirmasi sintetis dalam attempt yang sudah dijurnal, bukan retry.
        if self.save_route == "error":
            self.panel = "error_dialog"
            raise TimeoutError
        self.persisted = deepcopy(self.staged)
        if self.save_route == "metadata_loss" and self.persisted["tracks"]:
            self.persisted["tracks"][0]["ai_assisted"] = False
        self.panel = "list"
        if self.save_route == "lost_response":
            raise TimeoutError

    def observe(self):
        self.read_calls += 1
        if self.read_error:
            raise TimeoutError
        names = [t["basename"] for t in self.persisted["tracks"]]
        return dict(account=self.account, draft=self.draft, state=_projection(self.persisted),
                    complete=self.complete and self.encoding is None,
                    identity_verified=self.identity_verified and len(names) == len(set(names)))

    def reopen(self):
        _require(self.encoding is None, "fake_encoding_pending")
        self.staged = deepcopy(self.persisted)
        self.panel = "main"
        self.active_track = None
        self.visible_after = self.clock + self.field_ticks
