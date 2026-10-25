"""Journal smoke live; legacy debugging logs tidak memberi izin replay mutasi."""

from copy import deepcopy
import re

from .storage import _atomic_write, _digest, _read


class DraftError(Exception):
    pass


STAGES = ('create', 'artwork', 'audio', 'metadata', 'save')
KEYS = {'journal_version', 'run_id', 'checkpoint_sha256', 'profile', 'release_id',
        'expected_account', 'endpoint', 'remote_draft_id', 'amendment', 'events', 'record_sha256'}


class LiveJournal:
    def __init__(self, session, checkpoint, expected_account, endpoint, *, existing=False):
        self.session = session
        self.checkpoint = deepcopy(checkpoint)
        self.name = checkpoint['release_id'] + '.live.json'
        self.binding = dict(journal_version=2, run_id=checkpoint['run_id'],
                            checkpoint_sha256=checkpoint['record_sha256'], profile=session.alias,
                            release_id=checkpoint['release_id'], expected_account=expected_account,
                            endpoint=endpoint)
        if existing:
            self.value = self.read()
        else:
            try:
                _read(session.directory, self.name)
            except FileNotFoundError:
                pass
            else:
                raise DraftError('live_journal_exists')
            self.value = dict(self.binding, remote_draft_id=None, amendment=None, events=[])
            self._write(self.value, initial=True)

    def read(self):
        checkpoint = self.session.read_checkpoint(self.checkpoint['release_id'])
        if checkpoint != self.checkpoint or checkpoint['state'] != 'validated':
            raise DraftError('journal_checkpoint_mismatch')
        value = _read(self.session.directory, self.name)
        self._validate(value)
        return value

    def _validate(self, value):
        if not isinstance(value, dict) or set(value) != KEYS:
            raise DraftError('legacy_or_invalid_live_journal')
        if type(value['journal_version']) is not int or any(value.get(k) != v for k, v in self.binding.items()):
            raise DraftError('journal_binding_mismatch')
        if value['record_sha256'] != _digest({k: v for k, v in value.items() if k != 'record_sha256'}):
            raise DraftError('journal_hash_mismatch')
        amendment = value['amendment']
        if amendment is not None and amendment != self._title_amendment():
            raise DraftError('invalid_title_amendment')
        events = value['events']
        if not isinstance(events, list):
            raise DraftError('invalid_live_events')
        expected = [(stage, outcome) for stage in STAGES for outcome in ('unknown', 'observed')]
        expected.append(('readback', 'verified_subset'))
        if len(events) == 10 and isinstance(events[-1], dict) and events[-1].get('operation') == 'readback':
            expected.pop(9)  # Save unknown direkonsiliasi lewat reopen, bukan respons observed palsu.
        if len(events) > len(expected):
            raise DraftError('invalid_live_events')
        remote = value['remote_draft_id']
        if remote is not None and (not isinstance(remote, str) or not re.fullmatch(r'[1-9][0-9]*', remote)):
            raise DraftError('invalid_draft_identity')
        for index, event in enumerate(events):
            if (not isinstance(event, dict) or set(event) != {'operation', 'outcome', 'remote_draft_id'} or
                    (event['operation'], event['outcome']) != expected[index] or
                    event['remote_draft_id'] != (None if index == 0 else remote)):
                raise DraftError('invalid_live_events')
        if (len(events) >= 2) != (remote is not None):
            raise DraftError('invalid_draft_identity')

    def _write(self, candidate, *, initial=False):
        if not initial and self.read() != self.value:
            raise DraftError('live_journal_changed')
        candidate = deepcopy(candidate)
        candidate['record_sha256'] = _digest({k: v for k, v in candidate.items() if k != 'record_sha256'})
        self._validate(candidate)
        _atomic_write(self.session.directory, self.name, candidate)
        self.value = candidate

    def record(self, operation, outcome, remote_id):
        candidate = deepcopy(self.value)
        old_remote = candidate['remote_draft_id']
        if old_remote is not None and remote_id != old_remote:
            raise DraftError('draft_target_changed')
        candidate['remote_draft_id'] = remote_id
        candidate['events'].append(dict(operation=operation, outcome=outcome, remote_draft_id=remote_id))
        self._write(candidate)

    def _title_amendment(self):
        original = self.checkpoint['manifest']
        effective = deepcopy(original)
        effective['title'] = original['tracks'][0]['title']
        return dict(from_title=original['title'], to_title=effective['title'],
                    approval='explicit_release_equals_track',
                    original_manifest_sha256=_digest(original), effective_manifest_sha256=_digest(effective))

    def approve_title(self):
        # Hanya sebelum create; tidak mengubah snapshot awal atau judul draft existing.
        if self.value['amendment'] is not None or self.value['events']:
            raise DraftError('title_amendment_immutable')
        candidate = deepcopy(self.value)
        candidate['amendment'] = self._title_amendment()
        self._write(candidate)

    def effective_manifest(self):
        value = self.read()
        manifest = deepcopy(self.checkpoint['manifest'])
        if value['amendment'] is not None:
            manifest['title'] = value['amendment']['to_title']
        return manifest

    def require_reconciliation(self):
        value = self.read()
        if value != self.value:
            raise DraftError('live_journal_changed')
        if not value['events'] or value['events'][-1]['operation'] not in ('save', 'readback'):
            raise DraftError('manual_reconciliation_required')
        return value['remote_draft_id']

    def verify_readback(self):
        remote = self.require_reconciliation()
        if self.value['events'][-1]['operation'] != 'readback':
            self.record('readback', 'verified_subset', remote)
