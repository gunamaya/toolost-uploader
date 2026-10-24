"""Satu alur fake Save bergate; tidak mengeksekusi browser, upload atau publish."""

from . import approval, journal
from .fake_ui import FakeUI
from .storage import _digest, _require


def plan(ui):
    _require(type(ui) is FakeUI, "fake_ui_required")
    return {"operations": ["fake.save"], "desired_sha256": _digest(ui.desired())}


def execute(session, release_id, *, run_id, expected_revision, approval_id, ui):
    _require(type(ui) is FakeUI, "fake_ui_required")
    desired = ui.desired()
    draft_plan = {"operations": ["fake.save"], "desired_sha256": _digest(desired)}
    target = dict(account=ui.account, draft=ui.draft)
    approval.verify(session, release_id, run_id=run_id, approval_id=approval_id,
                    plan=draft_plan, **target)
    # Prepare is local-only. Consume failure must leave this intent unexecuted.
    attempt = journal.prepare(session, release_id, run_id=run_id, expected_revision=expected_revision,
                              adapter=ui, desired=desired)
    approval.consume(session, release_id, run_id=run_id, approval_id=approval_id,
                     plan=draft_plan, **target)
    return journal.execute(session, release_id, run_id=run_id, attempt_id=attempt["attempt_id"],
                           adapter=ui, desired=desired)


def reconcile(session, release_id, *, run_id, approval_id, attempt_id, ui):
    _require(type(ui) is FakeUI, "fake_ui_required")
    attempt = journal.read_attempt(session, release_id, run_id=run_id)
    _require(attempt["attempt_id"] == attempt_id, "attempt_mismatch")
    # Desired comes from persisted intent, not current staged UI after reload.
    draft_plan = {"operations": ["fake.save"], "desired_sha256": attempt["desired_sha256"]}
    approval.verify(session, release_id, run_id=run_id, approval_id=approval_id,
                    account=attempt["account"], draft=attempt["draft"], plan=draft_plan, consumed=True)
    return journal.reconcile(session, release_id, run_id=run_id, attempt_id=attempt_id, adapter=ui)
