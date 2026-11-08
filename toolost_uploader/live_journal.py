"""Journal smoke live; legacy debugging logs tidak memberi izin replay mutasi."""

from copy import deepcopy
import re

from .storage import _atomic_write, _digest, _read


class DraftError(Exception):
    pass


STAGES = ('create', 'artwork', 'audio', 'metadata', 'save')
APPEND_STAGES = ('append_audio', 'append_metadata', 'save')
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
        if not isinstance(value, dict) or not (KEYS <= set(value) <= KEYS | {'track_events', 'sync_pending'}):
            raise DraftError('legacy_or_invalid_live_journal')
        if type(value['journal_version']) is not int or any(value.get(k) != v for k, v in self.binding.items()):
            raise DraftError('journal_binding_mismatch')
        if value['record_sha256'] != _digest({k: v for k, v in value.items() if k != 'record_sha256'}):
            raise DraftError('journal_hash_mismatch')
        if 'sync_pending' in value and type(value['sync_pending']) is not bool:
            raise DraftError('invalid_sync_state')
        amendment = value['amendment']
        if amendment is not None and amendment != self._title_amendment():
            raise DraftError('invalid_title_amendment')
        events = value['events']
        if not isinstance(events, list):
            raise DraftError('invalid_live_events')
        expected = [(stage, outcome) for stage in STAGES for outcome in ('unknown', 'observed')]
        expected.append(('readback', 'verified_subset'))
        if len(events) >= 10 and events[9].get('operation') == 'readback' and expected[9] == ('save', 'observed'):
            expected.pop(9)

        idx = len(expected)
        while idx < len(events):
            op = events[idx].get('operation')
            if op in ('update_title', 'update_date', 'update_artwork', 'append_audio', 'update_metadata', 'append_metadata', 'save'):
                expected.extend([(op, 'unknown'), (op, 'observed')])
            elif op == 'readback':
                if (idx > 0 and events[idx - 1].get('operation') == 'save'
                        and events[idx - 1].get('outcome') == 'unknown'
                        and expected and expected[-1] == ('save', 'observed')):
                    expected.pop()
                expected.append(('readback', 'verified_subset'))
            else:
                break
            idx = len(expected)

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
        self._validate_tracks(value)

    def _validate_tracks(self, value):
        events = value.get('track_events', [])
        if not isinstance(events, list):
            raise DraftError('invalid_track_events')
        pending = None
        completed = set()
        manifest_tracks = self.checkpoint['manifest']['tracks']
        for event in events:
            if not isinstance(event, dict) or set(event) != {'track_id', 'sha256', 'index', 'outcome', 'stage_event'}:
                raise DraftError('invalid_track_events')
            index, stage = event['index'], event['stage_event']
            if (type(index) is not int or not 0 <= index < len(manifest_tracks)
                    or type(stage) is not int or not 0 <= stage < len(value['events'])):
                raise DraftError('invalid_track_binding')
            parent = value['events'][stage]
            if parent['operation'] not in ('audio', 'append_audio') or parent['outcome'] != 'unknown':
                raise DraftError('invalid_track_stage')
            expected = manifest_tracks[index]
            if event['track_id'] != expected['track_id'] or event['sha256'] != expected['audio']['sha256']:
                raise DraftError('invalid_track_binding')
            key = (stage, index, event['track_id'], event['sha256'])
            if event['outcome'] == 'unknown':
                if pending is not None or key in completed:
                    raise DraftError('track_outcome_unknown')
                pending = key
            elif event['outcome'] == 'observed' and pending == key:
                completed.add(key)
                pending = None
            else:
                raise DraftError('invalid_track_sequence')
        if pending is not None and len(value['events']) != pending[0] + 1:
            raise DraftError('track_outcome_unknown')

    def record_track(self, track_id, sha256, index, outcome):
        candidate = deepcopy(self.value)
        if not candidate['events'] or candidate['events'][-1]['operation'] not in ('audio', 'append_audio') or candidate['events'][-1]['outcome'] != 'unknown':
            raise DraftError('track_stage_not_active')
        candidate.setdefault('track_events', []).append(dict(track_id=track_id, sha256=sha256,
            index=index, outcome=outcome, stage_event=len(candidate['events']) - 1))
        self._write(candidate)

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
        if operation == 'readback' and outcome == 'verified_subset' and candidate.get('sync_pending'):
            candidate['sync_pending'] = False
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
        if value.get('sync_pending'):
            raise DraftError('sync_outcome_unknown_requires_review')
        if not value['events'] or value['events'][-1]['operation'] not in ('save', 'readback'):
            raise DraftError('manual_reconciliation_required')
        return value['remote_draft_id']

    def verify_readback(self):
        remote = self.require_reconciliation()
        if self.value['events'][-1]['operation'] != 'readback':
            self.record('readback', 'verified_subset', remote)

    def begin_sync(self):
        self.require_reconciliation()
        candidate = deepcopy(self.value)
        candidate['sync_pending'] = True
        self._write(candidate)

    def update_for_append(self, new_checkpoint):
        if self.checkpoint['release_id'] != new_checkpoint['release_id']:
            raise DraftError('release_id_mismatch')
        checkpoint = self.session.read_checkpoint(new_checkpoint['release_id'])
        if checkpoint != new_checkpoint or checkpoint['state'] != 'validated':
            raise DraftError('journal_checkpoint_mismatch')
        value = _read(self.session.directory, self.name)
        if not isinstance(value, dict) or not value.get('events') or value['events'][-1]['operation'] not in ('save', 'readback'):
            raise DraftError('manual_reconciliation_required')
        # Existing per-track bindings belong to the old immutable manifest revision.
        # Preserve the audit trail only when track identity/order remains compatible.
        if value.get('track_events'):
            old_tracks = self.checkpoint['manifest']['tracks']
            new_tracks = new_checkpoint['manifest']['tracks']
            bindings = lambda tracks: [(t['track_id'], t['audio']['sha256']) for t in tracks]
            if bindings(new_tracks[:len(old_tracks)]) != bindings(old_tracks):
                raise DraftError('serial_checkpoint_reorder_requires_review')
        self.checkpoint = deepcopy(new_checkpoint)
        self.binding['checkpoint_sha256'] = new_checkpoint['record_sha256']
        candidate = deepcopy(value)
        candidate['checkpoint_sha256'] = new_checkpoint['record_sha256']
        candidate['record_sha256'] = _digest({k: v for k, v in candidate.items() if k != 'record_sha256'})
        self._validate(candidate)
        _atomic_write(self.session.directory, self.name, candidate)
        self.value = candidate


class RecoveryJournal:
    """Ledger terpisah agar recovery tidak menulis ulang riwayat live lama."""

    def __init__(self, session, manifest, account, draft, endpoint, *, receipt=None):
        self.session = session
        self.name = session._check(manifest['release_id']).removesuffix('.json') + '.recovery.json'
        from .recovery_state import content_digest, content_manifest
        self.binding = dict(version=1, profile=session.alias, release_id=manifest['release_id'],
                            manifest_sha256=content_digest(manifest), account=account, draft=draft,
                            endpoint=endpoint)
        try:
            self.value = _read(session.directory, self.name)
        except FileNotFoundError:
            self.value = dict(self.binding, manifest=content_manifest(manifest), events=[], snapshot=None, mapping={})
            self._save()
        # A new exact receipt explicitly authorizes a new metadata revision, never
        # silently discard the previous attempt or its unresolved mutation intent.
        from .recovery_state import audio_identity
        from .remote_binding import verify_record
        old = self.value
        if (old.get('manifest_sha256') != self.binding['manifest_sha256']
                and receipt is not None):
            verify_record(old)
            verify_record(receipt)
            if (any(old.get(k) != v for k, v in self.binding.items() if k != 'manifest_sha256')
                    or receipt.get('manifest_sha256') != _digest(manifest)
                    or any(receipt.get(k) != v for k, v in dict(profile=session.alias,
                        release_id=manifest['release_id'], account=account, draft=draft).items())
                    or receipt.get('review_digest') == old.get('approval_digest')
                    or 'manifest' not in old
                    or audio_identity(old['manifest']) != audio_identity(manifest)):
                raise DraftError('recovery_manifest_reapproval_required')
            old.setdefault('history', []).append(deepcopy({k: v for k, v in old.items() if k != 'history'}))
            old['manifest_sha256'] = self.binding['manifest_sha256']
            old['manifest'] = content_manifest(manifest)
            self._save()
        self.read()

    def read(self):
        value = _read(self.session.directory, self.name)
        if (not isinstance(value, dict) or any(value.get(k) != v for k, v in self.binding.items())
                or value.get('record_sha256') != _digest({k: v for k, v in value.items() if k != 'record_sha256'})
                or not isinstance(value.get('events'), list)):
            raise DraftError('recovery_journal_corrupt_or_mismatched')
        if value != self.value:
            raise DraftError('recovery_journal_changed')
        return deepcopy(value)

    def _save(self):
        self.value['record_sha256'] = _digest({k: v for k, v in self.value.items() if k != 'record_sha256'})
        _atomic_write(self.session.directory, self.name, self.value)

    def append(self, operation, outcome, *, snapshot=None, mapping=None, track_id=None, approval_digest=None):
        self.read()
        if approval_digest is not None:
            self.value['approval_digest'] = approval_digest
        self.value['events'].append(dict(operation=operation, outcome=outcome, track_id=track_id))
        if snapshot is not None:
            self.value['snapshot'] = deepcopy(snapshot)
        if mapping is not None:
            self.value['mapping'] = dict(mapping)
        self._save()
