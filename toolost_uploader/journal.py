"""Simulasi save offline; tidak menerima adapter browser/akun nyata."""

import json
import uuid

from .storage import StorageError, _atomic_write, _digest, _encode, _read, _require


STATES = ("prepared", "unknown", "applied", "not_applied", "conflict")
KEYS = {"journal_version", "attempt_id", "run_id", "checkpoint_sha256", "profile", "release_id",
        "operation", "account", "draft", "baseline_sha256", "desired_sha256", "state", "record_sha256"}


def _fake_state(value):
    _require(isinstance(value, dict) and set(value) == {"title", "track_ids"}, "invalid_fake_state")
    _require(isinstance(value["title"], str) and bool(value["title"].strip()), "invalid_fake_state")
    tracks = value["track_ids"]
    _require(isinstance(tracks, list) and all(isinstance(item, str) and item for item in tracks), "invalid_fake_state")
    _require(len(tracks) == len(set(tracks)), "invalid_fake_state")
    return json.loads(_encode(value))


class FakeAdapter:
    """State sintetis dalam memori; respons save bukan bukti persistence."""

    def __init__(self, baseline, *, mode="success"):
        _require(mode in ("success", "lost_response", "before_send", "partial", "ambiguous"), "invalid_fake_mode")
        self.account = "synthetic-account"
        self.draft = "synthetic-draft"
        self.state = _fake_state(baseline)
        self.mode = mode
        self.save_calls = 0
        self.read_calls = 0
        self.read_error = False
        self.complete = True
        self.identity_verified = True

    def save(self, desired):
        self.save_calls += 1
        if self.mode == "before_send":
            raise TimeoutError
        self.state = _fake_state(desired)
        if self.mode == "partial":
            self.state["track_ids"] = []
            self.complete = False
        if self.mode == "ambiguous":
            self.identity_verified = False
        if self.mode == "lost_response":
            raise TimeoutError

    def observe(self):
        self.read_calls += 1
        if self.read_error:
            raise TimeoutError
        return dict(account=self.account, draft=self.draft, state=_fake_state(self.state),
                    complete=self.complete, identity_verified=self.identity_verified)


def _checkpoint(session, release_id, run_id):
    record = session.read_checkpoint(release_id)
    _require(record["run_id"] == run_id, "run_mismatch")
    _require(record["state"] == "validated", "invalid_transition")
    return record


def _observe(adapter):
    try:
        return adapter.observe()
    except TimeoutError:
        raise StorageError("fake_observation_unavailable") from None


def _save(session, name, record):
    record["record_sha256"] = _digest({key: value for key, value in record.items() if key != "record_sha256"})
    _atomic_write(session.directory, name, record)
    return record


def read_attempt(session, release_id, *, run_id):
    checkpoint = _checkpoint(session, release_id, run_id)
    try:
        record = _read(session.directory, release_id + ".attempt.json")
    except FileNotFoundError:
        raise StorageError("attempt_not_found") from None
    _require(isinstance(record, dict) and set(record) == KEYS, "invalid_journal")
    _require(type(record["journal_version"]) is int and record["journal_version"] == 1, "invalid_journal")
    _require(record["profile"] == session.alias and record["release_id"] == release_id
             and record["run_id"] == run_id and record["checkpoint_sha256"] == checkpoint["record_sha256"],
             "journal_checkpoint_mismatch")
    _require(record["operation"] == "fake.save" and record["state"] in STATES, "invalid_journal")
    _require(record["account"] == "synthetic-account" and record["draft"] == "synthetic-draft", "invalid_journal")
    for key, length in (("attempt_id", 32), ("baseline_sha256", 64), ("desired_sha256", 64)):
        value = record[key]
        _require(isinstance(value, str) and len(value) == length and all(c in "0123456789abcdef" for c in value), "invalid_journal")
    _require(record["record_sha256"] == _digest({key: value for key, value in record.items() if key != "record_sha256"}),
             "journal_hash_mismatch")
    return record


def prepare(session, release_id, *, run_id, expected_revision, adapter, desired):
    _require(type(adapter) is FakeAdapter, "fake_adapter_required")
    checkpoint = _checkpoint(session, release_id, run_id)
    _require(type(expected_revision) is int and checkpoint["revision"] == expected_revision, "revision_conflict")
    desired = _fake_state(desired)
    name = release_id + ".attempt.json"
    try:
        _read(session.directory, name)
    except FileNotFoundError:
        pass
    else:
        raise StorageError("attempt_exists")
    observation = _observe(adapter)
    _require(observation["account"] == "synthetic-account" and observation["draft"] == "synthetic-draft",
             "fake_identity_mismatch")
    _require(observation["complete"] and observation["identity_verified"], "reconciliation_required")
    baseline_hash = _digest(observation["state"])
    _require(baseline_hash != _digest(desired), "no_change")
    record = dict(journal_version=1, attempt_id=uuid.uuid4().hex, run_id=run_id,
                  checkpoint_sha256=checkpoint["record_sha256"], profile=session.alias,
                  release_id=release_id, operation="fake.save", account=observation["account"],
                  draft=observation["draft"], baseline_sha256=baseline_hash,
                  desired_sha256=_digest(desired), state="prepared")
    return _save(session, name, record)


def reconcile(session, release_id, *, run_id, attempt_id, adapter):
    _require(type(adapter) is FakeAdapter, "fake_adapter_required")
    record = read_attempt(session, release_id, run_id=run_id)
    _require(record["attempt_id"] == attempt_id, "attempt_mismatch")
    _require(record["state"] == "unknown", "invalid_attempt_transition")
    try:
        observed = adapter.observe()
    except TimeoutError:
        return record
    if observed["account"] != record["account"] or observed["draft"] != record["draft"]:
        state = "conflict"
    elif not observed["complete"] or not observed["identity_verified"]:
        return record
    else:
        digest = _digest(observed["state"])
        state = ("applied" if digest == record["desired_sha256"] else
                 "not_applied" if digest == record["baseline_sha256"] else "conflict")
    record["state"] = state
    return _save(session, release_id + ".attempt.json", record)


def execute(session, release_id, *, run_id, attempt_id, adapter, desired):
    _require(type(adapter) is FakeAdapter, "fake_adapter_required")
    record = read_attempt(session, release_id, run_id=run_id)
    _require(record["attempt_id"] == attempt_id, "attempt_mismatch")
    _require(record["state"] == "prepared", "reconciliation_required")
    desired = _fake_state(desired)
    _require(_digest(desired) == record["desired_sha256"], "desired_mismatch")
    observed = _observe(adapter)
    _require(observed["account"] == record["account"] and observed["draft"] == record["draft"], "fake_identity_mismatch")
    _require(observed["complete"] and observed["identity_verified"]
             and _digest(observed["state"]) == record["baseline_sha256"], "baseline_conflict")
    # Unknown durably written BEFORE calling save: crash/timeout cannot authorize retry.
    record["state"] = "unknown"
    _save(session, release_id + ".attempt.json", record)
    try:
        adapter.save(desired)
    except TimeoutError:
        return record
    return reconcile(session, release_id, run_id=run_id, attempt_id=attempt_id, adapter=adapter)
