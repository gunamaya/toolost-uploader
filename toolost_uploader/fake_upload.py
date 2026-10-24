"""Upload fixture persisten lokal; tidak membaca audio atau menghubungi layanan."""

from pathlib import Path
import uuid

from .journal import _checkpoint, _save
from .storage import StorageError, _digest, _read, _require


SERVER_KEYS = {"version", "run_id", "checkpoint_sha256", "account", "draft", "tracks", "upload_calls", "record_sha256"}
ATTEMPT_KEYS = {"version", "run_id", "checkpoint_sha256", "attempt_id", "batch_sha256", "state", "record_sha256"}


def _name(session, release_id, suffix):
    session._check(release_id)
    return release_id + suffix


def _absent(session, name):
    try:
        _read(session.directory, name)
    except FileNotFoundError:
        return
    raise StorageError("fixture_exists")


def _record(session, release_id, run_id, suffix, keys):
    checkpoint = _checkpoint(session, release_id, run_id)
    try:
        record = _read(session.directory, _name(session, release_id, suffix))
    except FileNotFoundError:
        raise StorageError("fixture_not_found") from None
    _require(isinstance(record, dict) and set(record) == keys, "invalid_fixture")
    _require(type(record["version"]) is int and record["version"] == 1, "invalid_fixture")
    _require(record["run_id"] == run_id and record["checkpoint_sha256"] == checkpoint["record_sha256"],
             "journal_checkpoint_mismatch")
    _require(record["record_sha256"] == _digest({k: v for k, v in record.items() if k != "record_sha256"}),
             "fixture_hash_mismatch")
    return record


def _batch(session, release_id, run_id):
    checkpoint = _checkpoint(session, release_id, run_id)
    return [dict(track_id=t["track_id"], basename=Path(t["audio"]["path"]).name,
                 sha256=t["audio"]["sha256"]) for t in checkpoint["manifest"]["tracks"]]


def initialize(session, release_id, *, run_id):
    checkpoint = _checkpoint(session, release_id, run_id)
    name = _name(session, release_id, ".fake-server.json")
    _absent(session, name)
    return _save(session, name, dict(version=1, run_id=run_id, checkpoint_sha256=checkpoint["record_sha256"],
                                   account="synthetic-account", draft="synthetic-draft", tracks=[], upload_calls=0))


def observe(session, release_id, *, run_id):
    record = _record(session, release_id, run_id, ".fake-server.json", SERVER_KEYS)
    _require(isinstance(record["account"], str) and isinstance(record["draft"], str), "invalid_fixture")
    _require(type(record["upload_calls"]) is int and record["upload_calls"] in (0, 1), "invalid_fixture")
    _require(isinstance(record["tracks"], list), "invalid_fixture")
    for track in record["tracks"]:
        _require(isinstance(track, dict) and set(track) == {"track_id", "basename", "sha256", "encoding"}, "invalid_fixture")
        _require(all(isinstance(track[k], str) and track[k] for k in track), "invalid_fixture")
        _require(len(track["sha256"]) == 64 and all(c in "0123456789abcdef" for c in track["sha256"]), "invalid_fixture")
        _require(track["encoding"] in ("pending", "ready", "failed"), "invalid_fixture")
    return record


def read_attempt(session, release_id, *, run_id):
    record = _record(session, release_id, run_id, ".upload-attempt.json", ATTEMPT_KEYS)
    _require(record["state"] in ("prepared", "unknown", "applied", "not_applied", "conflict"), "invalid_fixture")
    for key, length in (("attempt_id", 32), ("batch_sha256", 64)):
        value = record[key]
        _require(isinstance(value, str) and len(value) == length and all(c in "0123456789abcdef" for c in value), "invalid_fixture")
    _require(record["batch_sha256"] == _digest(_batch(session, release_id, run_id)), "batch_mismatch")
    return record


def prepare(session, release_id, *, run_id, expected_revision):
    checkpoint = _checkpoint(session, release_id, run_id)
    _require(type(expected_revision) is int and checkpoint["revision"] == expected_revision, "revision_conflict")
    name = _name(session, release_id, ".upload-attempt.json")
    _absent(session, name)
    server = observe(session, release_id, run_id=run_id)
    _require(server["account"] == "synthetic-account" and server["draft"] == "synthetic-draft", "fake_identity_mismatch")
    _require(not server["tracks"] and server["upload_calls"] == 0, "reconciliation_required")
    return _save(session, name, dict(version=1, run_id=run_id, checkpoint_sha256=checkpoint["record_sha256"],
                                   attempt_id=uuid.uuid4().hex, batch_sha256=_digest(_batch(session, release_id, run_id)),
                                   state="prepared"))


def execute(session, release_id, *, run_id, attempt_id, mode="pending"):
    _require(mode in ("pending", "lost_response", "before_send", "partial"), "invalid_fake_mode")
    record = read_attempt(session, release_id, run_id=run_id)
    _require(record["attempt_id"] == attempt_id, "attempt_mismatch")
    _require(record["state"] == "prepared", "reconciliation_required")
    server = observe(session, release_id, run_id=run_id)
    _require(server["account"] == "synthetic-account" and server["draft"] == "synthetic-draft", "fake_identity_mismatch")
    _require(not server["tracks"] and server["upload_calls"] == 0, "baseline_conflict")
    record["state"] = "unknown"
    _save(session, _name(session, release_id, ".upload-attempt.json"), record)
    if mode == "before_send":
        return record
    tracks = list(reversed(_batch(session, release_id, run_id)))
    if mode == "partial":
        tracks = tracks[:1]
    server["tracks"] = [dict(t, encoding="pending") for t in tracks]
    server["upload_calls"] = 1
    _save(session, _name(session, release_id, ".fake-server.json"), server)
    # Response (including simulated loss) never proves encoding or persisted release Save.
    return record


def settle(session, release_id, *, run_id, failed=False):
    """Fixture-only server progression; never invoked by reconcile or execute."""
    _require(type(failed) is bool, "invalid_fake_mode")
    server = observe(session, release_id, run_id=run_id)
    for track in server["tracks"]:
        if track["encoding"] == "pending":
            track["encoding"] = "failed" if failed else "ready"
    return _save(session, _name(session, release_id, ".fake-server.json"), server)


def reconcile(session, release_id, *, run_id, attempt_id):
    record = read_attempt(session, release_id, run_id=run_id)
    _require(record["attempt_id"] == attempt_id, "attempt_mismatch")
    _require(record["state"] == "unknown", "invalid_attempt_transition")
    server = observe(session, release_id, run_id=run_id)
    expected = _batch(session, release_id, run_id)
    actual = [{k: t[k] for k in ("track_id", "basename", "sha256")} for t in server["tracks"]]
    names = [t["basename"] for t in actual]
    ids = [t["track_id"] for t in actual]
    if server["account"] != "synthetic-account" or server["draft"] != "synthetic-draft":
        state = "conflict"
    elif not actual and server["upload_calls"] == 0:
        state = "not_applied"
    elif len(names) != len(set(names)) or len(ids) != len(set(ids)):
        return record
    elif any(t not in expected for t in actual):
        state = "conflict"
    elif len(actual) != len(expected) or any(t["encoding"] != "ready" for t in server["tracks"]):
        return record
    else:
        state = "applied"
    record["state"] = state
    return _save(session, _name(session, release_id, ".upload-attempt.json"), record)
