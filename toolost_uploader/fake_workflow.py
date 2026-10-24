"""Workflow sintetis tiga langkah, satu approval immutable; bukan executor akun."""

from copy import deepcopy

from . import approval, fake_upload, journal
from .fake_ui import FakeUI
from .storage import StorageError, _digest, _read, _require


KEYS = {"version", "run_id", "checkpoint_sha256", "approval_id", "plan_sha256",
        "steps", "upload_attempt_id", "save_attempt_id", "record_sha256"}


def desired(session, release_id, run_id):
    checkpoint = journal._checkpoint(session, release_id, run_id)
    manifest = checkpoint["manifest"]
    _require(not set(manifest) - {"schema_version", "release_id", "release_type", "title", "release_date", "artwork", "tracks"},
             "unsupported_workflow_fields")
    for track in manifest["tracks"]:
        _require(not set(track) - {"track_id", "title", "audio", "ai_assisted"}, "unsupported_workflow_fields")
    batch = fake_upload._batch(session, release_id, run_id)
    tracks = [dict(track_id=t["track_id"], basename=b["basename"], title=t["title"],
                   ai_assisted=t["ai_assisted"]) for t, b in zip(manifest["tracks"], batch)]
    return dict(title=manifest["title"], tracks=tracks)


def plan(session, release_id, *, run_id):
    return dict(operations=["fake.upload", "fake.edit", "fake.save"],
                desired_sha256=_digest(desired(session, release_id, run_id)))


def _receipt(session, release_id, record):
    checkpoint = journal._checkpoint(session, release_id, record["run_id"])
    _require(record["checkpoint_sha256"] == checkpoint["record_sha256"]
             and record["plan_sha256"] == _digest(plan(session, release_id, run_id=record["run_id"])), "workflow_stale")
    approval.verify(session, release_id, run_id=record["run_id"], approval_id=record["approval_id"],
                    account="synthetic-account", draft="synthetic-draft",
                    plan=plan(session, release_id, run_id=record["run_id"]), consumed=True)


def read(session, release_id, *, run_id):
    journal._checkpoint(session, release_id, run_id)
    try:
        record = _read(session.directory, release_id + ".workflow.json")
    except FileNotFoundError:
        raise StorageError("workflow_not_found") from None
    _require(isinstance(record, dict) and set(record) == KEYS, "invalid_workflow")
    _require(type(record["version"]) is int and record["version"] == 1 and record["run_id"] == run_id, "invalid_workflow")
    _require(isinstance(record["steps"], list) and len(record["steps"]) == 3
             and all(s in ("pending", "unknown", "applied", "not_applied", "conflict") for s in record["steps"]), "invalid_workflow")
    for key in ("approval_id", "upload_attempt_id", "save_attempt_id"):
        token = record[key]
        if key == "save_attempt_id" and token is None:
            _require(record["steps"][2] == "pending", "invalid_workflow")
        else:
            _require(isinstance(token, str) and len(token) == 32
                     and all(c in "0123456789abcdef" for c in token), "invalid_workflow")
    for index in range(1, 3):
        _require(record["steps"][index] == "pending" or all(s == "applied" for s in record["steps"][:index]), "invalid_workflow")
    _require(record["record_sha256"] == _digest({k: v for k, v in record.items() if k != "record_sha256"}), "workflow_hash_mismatch")
    _receipt(session, release_id, record)
    return record


def _write(session, release_id, record):
    return journal._save(session, release_id + ".workflow.json", record)


def start(session, release_id, *, run_id, expected_revision, approval_id):
    checkpoint = journal._checkpoint(session, release_id, run_id)
    draft_plan = plan(session, release_id, run_id=run_id)
    approval.verify(session, release_id, run_id=run_id, approval_id=approval_id,
                    account="synthetic-account", draft="synthetic-draft", plan=draft_plan)
    fake_upload._absent(session, release_id + ".workflow.json")
    # Existing Save intent cannot be adopted into this workflow.
    fake_upload._absent(session, release_id + ".attempt.json")
    attempt = fake_upload.prepare(session, release_id, run_id=run_id, expected_revision=expected_revision)
    record = dict(version=1, run_id=run_id, checkpoint_sha256=checkpoint["record_sha256"],
                  approval_id=approval_id, plan_sha256=_digest(draft_plan), steps=["pending"] * 3,
                  upload_attempt_id=attempt["attempt_id"], save_attempt_id=None)
    _write(session, release_id, record)
    approval.consume(session, release_id, run_id=run_id, approval_id=approval_id,
                     account="synthetic-account", draft="synthetic-draft", plan=draft_plan)
    return record


def _uploaded(session, release_id, run_id):
    server = fake_upload.observe(session, release_id, run_id=run_id)
    _require(server["account"] == "synthetic-account" and server["draft"] == "synthetic-draft", "fake_identity_mismatch")
    expected = fake_upload._batch(session, release_id, run_id)
    actual = [{k: t[k] for k in ("track_id", "basename", "sha256")} for t in server["tracks"]]
    _require(len(actual) == len(expected) and sorted(actual, key=lambda t: t["track_id"]) == sorted(expected, key=lambda t: t["track_id"])
             and len({t["basename"] for t in actual}) == len(actual)
             and all(t["encoding"] == "ready" for t in server["tracks"]), "reconciliation_required")
    return server


def _ui(ui):
    _require(type(ui) is FakeUI, "fake_ui_required")
    _require(ui.account == "synthetic-account" and ui.draft == "synthetic-draft", "fake_identity_mismatch")


def advance(session, release_id, *, run_id, ui, upload_mode="pending"):
    _ui(ui)
    _require(upload_mode in ("pending", "before_send", "lost_response", "partial"), "invalid_fake_mode")
    record = read(session, release_id, run_id=run_id)
    steps = record["steps"]
    _require("unknown" not in steps and not any(s in ("conflict", "not_applied") for s in steps), "reconciliation_required")
    _require("pending" in steps, "workflow_complete")
    index = steps.index("pending")
    if index == 0:
        steps[0] = "unknown"
        _write(session, release_id, record)
        fake_upload.execute(session, release_id, run_id=run_id, attempt_id=record["upload_attempt_id"], mode=upload_mode)
        return record
    _uploaded(session, release_id, run_id)
    target = desired(session, release_id, run_id)
    if index == 1:
        ui.rows()
        _require(not ui.staged["tracks"] and not ui.persisted["tracks"], "baseline_conflict")
        steps[1] = "unknown"
        _write(session, release_id, record)
        # Explicit fixture handoff from disk ingestion to in-memory UI, not a remote upload.
        ui.staged = deepcopy(target)
        _require(ui.desired()["metadata_sha256"] == _digest(target["tracks"]), "reconciliation_required")
        steps[1] = "applied"
        return _write(session, release_id, record)
    _require(ui.desired() == dict(title=target["title"], track_ids=[t["track_id"] for t in target["tracks"]],
                                 metadata_sha256=_digest(target["tracks"])), "staging_lost_or_changed")
    checkpoint = journal._checkpoint(session, release_id, run_id)
    attempt = journal.prepare(session, release_id, run_id=run_id, expected_revision=checkpoint["revision"], adapter=ui, desired=ui.desired())
    record["save_attempt_id"] = attempt["attempt_id"]
    steps[2] = "unknown"
    _write(session, release_id, record)
    outcome = journal.execute(session, release_id, run_id=run_id, attempt_id=attempt["attempt_id"], adapter=ui, desired=ui.desired())
    steps[2] = outcome["state"]
    return _write(session, release_id, record)


def reconcile(session, release_id, *, run_id, ui):
    _ui(ui)
    record = read(session, release_id, run_id=run_id)
    _require("unknown" in record["steps"], "no_unknown_step")
    index = record["steps"].index("unknown")
    if index == 1:
        # Staged memory after a crash is not authoritative persistence.
        return record
    if index == 0:
        outcome = fake_upload.read_attempt(session, release_id, run_id=run_id)
        _require(outcome["attempt_id"] == record["upload_attempt_id"], "attempt_mismatch")
        if outcome["state"] == "unknown":
            outcome = fake_upload.reconcile(session, release_id, run_id=run_id, attempt_id=record["upload_attempt_id"])
    else:
        outcome = journal.read_attempt(session, release_id, run_id=run_id)
        _require(outcome["attempt_id"] == record["save_attempt_id"], "attempt_mismatch")
        if outcome["state"] == "unknown":
            outcome = journal.reconcile(session, release_id, run_id=run_id, attempt_id=record["save_attempt_id"], adapter=ui)
    _require(outcome["state"] in ("unknown", "applied", "not_applied", "conflict"), "reconciliation_required")
    record["steps"][index] = outcome["state"]
    return _write(session, release_id, record)
