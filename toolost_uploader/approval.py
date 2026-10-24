"""Gate sintetis offline; bukan pembuktian identitas akun atau izin executor nyata."""

import uuid

from .journal import _checkpoint, _save
from .storage import StorageError, _digest, _read, _require


BINDING_KEYS = {"version", "profile", "account", "authority", "record_sha256"}
APPROVAL_KEYS = {"version", "profile", "account", "draft", "run_id", "checkpoint_sha256",
                 "plan_sha256", "approval_id", "state", "authority", "record_sha256"}


def _identity(account, draft):
    _require(account == "synthetic-account" and draft == "synthetic-draft", "identity_review_required")


def _read_record(session, release_id, suffix, keys):
    session._check(release_id)
    try:
        record = _read(session.directory, release_id + suffix)
    except FileNotFoundError:
        raise StorageError("approval_record_missing") from None
    _require(isinstance(record, dict) and set(record) == keys, "invalid_approval_record")
    _require(type(record["version"]) is int and record["version"] == 1
             and record["profile"] == session.alias and record["authority"] == "synthetic-offline",
             "invalid_approval_record")
    _require(record["record_sha256"] == _digest({k: v for k, v in record.items() if k != "record_sha256"}),
             "approval_hash_mismatch")
    return record


def _absent(session, name):
    try:
        _read(session.directory, name)
    except FileNotFoundError:
        return
    raise StorageError("approval_record_exists")


def _plan(plan):
    _require(isinstance(plan, dict) and set(plan) == {"operations", "desired_sha256"}, "invalid_draft_plan")
    operations = plan["operations"]
    _require(isinstance(operations, list) and bool(operations)
             and all(op in ("fake.upload", "fake.edit", "fake.save") for op in operations)
             and len(operations) == len(set(operations)), "invalid_draft_plan")
    digest = plan["desired_sha256"]
    _require(isinstance(digest, str) and len(digest) == 64
             and all(c in "0123456789abcdef" for c in digest), "invalid_draft_plan")
    return _digest(plan)


def bind(session, *, account, reviewed):
    session._check("binding")
    _require(reviewed is True, "binding_review_required")
    _identity(account, "synthetic-draft")
    name = "_offline-binding.json"
    _absent(session, name)
    return _save(session, name, dict(version=1, profile=session.alias, account=account,
                                    authority="synthetic-offline"))


def _binding(session, release_id, account):
    # Binding per profile memakai inode privat dalam directory yang sudah terkunci.
    try:
        record = _read(session.directory, "_offline-binding.json")
    except FileNotFoundError:
        raise StorageError("binding_review_required") from None
    _require(isinstance(record, dict) and set(record) == BINDING_KEYS, "invalid_approval_record")
    _require(type(record["version"]) is int and record["version"] == 1
             and record["profile"] == session.alias and record["authority"] == "synthetic-offline"
             and record["account"] == account == "synthetic-account", "binding_mismatch")
    _require(record["record_sha256"] == _digest({k: v for k, v in record.items() if k != "record_sha256"}),
             "approval_hash_mismatch")


def approve(session, release_id, *, run_id, expected_revision, account, draft, plan, approved):
    checkpoint = _checkpoint(session, release_id, run_id)
    _identity(account, draft)
    _binding(session, release_id, account)
    _require(approved is True, "confirmation_required")
    _require(type(expected_revision) is int and checkpoint["revision"] == expected_revision, "revision_conflict")
    plan_hash = _plan(plan)
    name = release_id + ".approval.json"
    _absent(session, name)
    return _save(session, name, dict(version=1, profile=session.alias, account=account, draft=draft,
                                    run_id=run_id, checkpoint_sha256=checkpoint["record_sha256"],
                                    plan_sha256=plan_hash, approval_id=uuid.uuid4().hex,
                                    state="approved", authority="synthetic-offline"))


def verify(session, release_id, *, run_id, approval_id, account, draft, plan, consumed=False):
    checkpoint = _checkpoint(session, release_id, run_id)
    _identity(account, draft)
    _binding(session, release_id, account)
    record = _read_record(session, release_id, ".approval.json", APPROVAL_KEYS)
    token = record["approval_id"]
    _require(isinstance(token, str) and len(token) == 32
             and all(c in "0123456789abcdef" for c in token)
             and record["state"] in ("approved", "consumed"), "invalid_approval_record")
    _require(type(consumed) is bool, "invalid_approval_record")
    _require(record["state"] == ("consumed" if consumed else "approved"),
             "approval_not_consumed" if consumed else "approval_consumed")
    _require(record["approval_id"] == approval_id and record["run_id"] == run_id,
             "approval_mismatch")
    _require(record["account"] == account and record["draft"] == draft
             and record["checkpoint_sha256"] == checkpoint["record_sha256"]
             and record["plan_sha256"] == _plan(plan), "approval_stale")
    return record


def consume(session, release_id, *, run_id, approval_id, account, draft, plan):
    record = verify(session, release_id, run_id=run_id, approval_id=approval_id,
                    account=account, draft=draft, plan=plan)
    record["state"] = "consumed"
    return _save(session, release_id + ".approval.json", record)
