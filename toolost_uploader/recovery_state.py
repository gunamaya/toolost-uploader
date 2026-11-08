"""Identitas konten dan successor recovery; riwayat live lama tetap immutable."""

from copy import deepcopy

from .storage import _digest, _read, _atomic_write
from .live_journal import DraftError


def content_manifest(manifest):
    value = deepcopy(manifest)
    if isinstance(value.get('artwork'), dict):
        value['artwork'].pop('path', None)
    for track in value.get('tracks', []):
        if isinstance(track.get('audio'), dict):
            track['audio'].pop('path', None)
        if isinstance(track.get('lyrics'), dict):
            track['lyrics'].pop('path', None)
    return value


def content_digest(manifest):
    return _digest(content_manifest(manifest))


def audio_identity(manifest):
    return [(t['track_id'], t['audio']['sha256']) for t in manifest['tracks']]


def read_successor(session, release_id, account, endpoint):
    name = session._check(release_id).removesuffix('.json') + '.successor.json'
    try:
        value = _read(session.directory, name)
    except FileNotFoundError:
        return None
    if (not isinstance(value, dict) or value.get('record_sha256') !=
            _digest({k: v for k, v in value.items() if k != 'record_sha256'})
            or any(value.get(k) != v for k, v in dict(version=1, profile=session.alias,
                release_id=release_id, account=account, endpoint=endpoint).items())):
        raise DraftError('recovery_successor_mismatch')
    return value


def save_successor(session, manifest, account, draft, endpoint, ledger):
    if not ledger['events'] or ledger['events'][-1] != dict(operation='complete', outcome='observed', track_id=None):
        raise DraftError('recovery_not_complete')
    previous = read_successor(session, manifest['release_id'], account, endpoint)
    value = dict(version=1, profile=session.alias, release_id=manifest['release_id'],
                 account=account, draft=draft, endpoint=endpoint,
                 manifest_sha256=content_digest(manifest), ledger_sha256=ledger['record_sha256'])
    if previous and any(previous.get(k) != v for k, v in value.items()):
        value['history'] = previous.get('history', []) + [{k: v for k, v in previous.items() if k != 'history'}]
    elif previous:
        return
    value['record_sha256'] = _digest(value)
    _atomic_write(session.directory, session._check(manifest['release_id']).removesuffix('.json') + '.successor.json', value)
