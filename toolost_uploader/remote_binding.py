"""Review ID remote eksplisit untuk recovery draft, bukan bukti byte audio."""

import hashlib
import json
import re

from .live_journal import DraftError


def observe_active_editor(page, *, account, draft):
    """Read the Vue row props without navigation or exposing audio references."""
    if (any(not isinstance(x, str) or not re.fullmatch(r'[1-9][0-9]*', x) for x in (account, draft))
            or page.url != 'https://toolost.com/uploader/edit/' + draft):
        raise DraftError('recovery_identity_unverified')
    value = page.evaluate("""() => {
        let identity = null, tracks = null;
        for (const el of document.querySelectorAll('*')) {
            let vm = el.__vue__;
            for (let depth = 0; vm && depth < 10; depth++, vm = vm.$parent) {
                const computed = vm.$options.computed || {};
                if (computed.user && computed.id && computed.release) {
                    identity = {account: String(vm.user && vm.user.id), draft: String(vm.id)};
                    tracks = vm.release && vm.release.tracks;
                    break;
                }
            }
            if (identity) break;
        }
        return {identity, tracks: Array.isArray(tracks) ? tracks.map(t => ({
            editor_key: t.id, saved: t.saved, title: t.metadata && t.metadata.title,
            track_order: t.index, audio_present: typeof t.url === 'string' && !!t.url
        })) : null};
    }""")
    if (page.url != 'https://toolost.com/uploader/edit/' + draft
            or not isinstance(value, dict) or value.get('identity') != {'account': account, 'draft': draft}
            or not isinstance(value.get('tracks'), list)):
        raise DraftError('recovery_identity_unverified')
    keys, orders = set(), set()
    for position, row in enumerate(value['tracks']):
        if (not isinstance(row, dict) or type(row.get('editor_key')) not in (str, int)
                or not str(row['editor_key']) or str(row['editor_key']) in keys
                or type(row.get('saved')) is not bool or not isinstance(row.get('title'), str)
                or not row['title'].strip()
                or row.get('audio_present') is not True):
            raise DraftError('active_editor_observation_requires_review')
        # Vue array position is observation order, not a persisted track ID.
        order = row.get('track_order')
        if order is None:
            order = position
            row['track_order'] = order
        if type(order) is not int or order < 0 or order in orders:
            raise DraftError('active_editor_observation_requires_review')
        keys.add(str(row['editor_key']))
        orders.add(order)
    return value['tracks']


def guard_active_unsaved(context, *, account, draft):
    for page in context.pages:
        if page.url == 'https://toolost.com/uploader/edit/' + draft:
            tracks = observe_active_editor(page, account=account, draft=draft)
            if any(not t['saved'] for t in tracks):
                raise DraftError('active_unsaved_upload_requires_review')


def observe_release(context, *, account, draft):
    """Read an authenticated release response in a disposable same-context tab."""
    from urllib.parse import urlsplit
    if any(not isinstance(x, str) or not re.fullmatch(r'[1-9][0-9]*', x) for x in (account, draft)):
        raise DraftError('recovery_identity_unverified')
    guard_active_unsaved(context, account=account, draft=draft)
    page = context.new_page()
    accounts, snapshots = [], []
    def on_response(response):
        u = urlsplit(response.url)
        if u.scheme != 'https' or u.netloc != 'toolost.com' or response.status != 200:
            return
        try:
            if u.path == '/api/auth/me':
                value = response.json().get('user', {}).get('id')
                if type(value) is int:
                    accounts.append(str(value))
            elif u.path == '/api/distribution/release/' + draft:
                data = response.json()
                info = data['info']
                if str(info['id']) != draft or str(info['user_id']) != account:
                    raise DraftError('recovery_identity_unverified')
                snapshots.append(data['tracks'])
        except Exception:
            snapshots.append(None)
    page.on('response', on_response)
    def read_only(route):
        if route.request.method not in ('GET', 'HEAD', 'OPTIONS') and urlsplit(route.request.url).path != '/api/auth/refresh':
            route.abort()
        else:
            route.continue_()
    page.route('https://toolost.com/**', read_only)
    try:
        page.goto('https://toolost.com/uploader/edit/' + draft, wait_until='domcontentloaded', timeout=30000)
        for _ in range(80):
            if accounts and snapshots:
                break
            page.wait_for_timeout(250)
        if page.url != 'https://toolost.com/uploader/edit/' + draft or not accounts or any(x != account for x in accounts) or len(snapshots) != 1 or not isinstance(snapshots[0], list):
            raise DraftError('recovery_identity_unverified')
        return snapshots[0]
    finally:
        page.close()


def _digest(value):
    try:
        data = json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':'), allow_nan=False)
        return hashlib.sha256(data.encode('ascii')).hexdigest()
    except (TypeError, ValueError):
        raise DraftError('remote_binding_invalid') from None


def prepare_binding(*, manifest, account, draft, tracks, mapping):
    """Buat review dari data caller; mapping harus dikonfirmasi manusia, bukan tebak judul."""
    try:
        if any(not isinstance(x, str) or not re.fullmatch(r'[1-9][0-9]*', x) for x in (account, draft)):
            raise ValueError
        local = manifest['tracks']
        if not isinstance(local, list) or not local or not isinstance(tracks, list) or not isinstance(mapping, dict):
            raise ValueError
        local_ids = [t['track_id'] for t in local]
        if any(not isinstance(x, str) or not x for x in local_ids) or len(set(local_ids)) != len(local_ids):
            raise ValueError
        remote_ids, orders = [], []
        for track in tracks:
            rid, title, order, audio = (track[x] for x in ('id', 'title', 'track_order', 'audio_url'))
            if type(rid) is int and rid > 0:
                rid = str(rid)
            if not isinstance(rid, str) or not re.fullmatch(r'[1-9][0-9]*', rid):
                raise ValueError
            if not isinstance(title, str) or not title.strip() or type(order) is not int or order < 0:
                raise ValueError
            if not isinstance(audio, str) or not audio.strip():
                raise ValueError
            remote_ids.append(rid)
            orders.append(order)
        if len(set(remote_ids)) != len(remote_ids) or len(set(orders)) != len(orders):
            raise ValueError
        if any(not isinstance(k, str) or not isinstance(v, str) for k, v in mapping.items()):
            raise ValueError
        if not set(mapping).issubset(local_ids) or not set(mapping.values()).issubset(remote_ids):
            raise ValueError
        if len(set(mapping.values())) != len(mapping):
            raise ValueError
        # Hash URLs as part of the snapshot, without returning potentially sensitive URLs.
        snapshot = [{'id': rid, 'title': track['title'], 'track_order': track['track_order'],
                     'audio_url_sha256': hashlib.sha256(track['audio_url'].encode('utf-8')).hexdigest()}
                    for rid, track in zip(remote_ids, tracks)]
        snapshot.sort(key=lambda track: track['id'])
        content = {'account': account, 'draft': draft, 'manifest': manifest,
                   'tracks': snapshot, 'mapping': mapping}
        return {'review_digest': _digest(content), 'mapping': dict(mapping),
                'account': account, 'draft': draft,
                'manifest_sha256': _digest(manifest), 'snapshot': snapshot,
                'missing_track_ids': [x for x in local_ids if x not in mapping],
                'unmapped_remote_ids': [x for x in remote_ids if x not in mapping.values()],
                'remote_audio_hashes_verified': False, 'persisted_state_verified': False,
                'observation_provenance_verified': False, 'retry_safe': False,
                'execution_available': False}
    except (KeyError, TypeError, ValueError, UnicodeError):
        raise DraftError('remote_binding_invalid') from None


def confirm_binding(*, approved_digest, manifest, account, draft, tracks, mapping):
    """Konfirmasi hanya cocok dengan observasi yang diberikan, bukan bukti byte atau izin mutasi."""
    review = prepare_binding(manifest=manifest, account=account, draft=draft, tracks=tracks, mapping=mapping)
    if not isinstance(approved_digest, str) or approved_digest != review['review_digest']:
        raise DraftError('remote_binding_review_changed')
    return {**review, 'status': 'confirmed_observation_only', 'approval_matches_snapshot': True}


def propose_mapping(manifest, tracks):
    from .recovery_inspection import _track_key
    candidates = {}
    for track in tracks:
        key = _track_key(track.get('title', ''))
        if not key or key in candidates:
            raise DraftError('remote_binding_invalid')
        candidates[key] = str(track.get('id', ''))
    mapping, seen = {}, set()
    for track in manifest['tracks']:
        key = _track_key(track['title'])
        if not key or key in seen:
            raise DraftError('remote_binding_invalid')
        seen.add(key)
        if key in candidates:
            mapping[track['track_id']] = candidates[key]
    return mapping


def observed_upload_mapping(manifest, before, after, selected):
    """Bind only the uniquely labelled ID delta of this explicit upload attempt."""
    from pathlib import Path
    before_ids = {str(t['id']) for t in before}
    added = [t for t in after if str(t['id']) not in before_ids]
    if len(added) != len(selected):
        raise DraftError('new_upload_binding_requires_review')
    labels = {}
    for track in selected:
        for label in {Path(track['audio']['path']).stem.casefold(),
                      Path(track['audio']['path']).name.casefold(), track['title'].casefold()}:
            labels.setdefault(label, set()).add(track['track_id'])
    mapping = {}
    for remote in added:
        candidates = labels.get(remote.get('title', '').casefold(), set())
        if len(candidates) != 1:
            raise DraftError('new_upload_binding_requires_review')
        local = next(iter(candidates))
        if local in mapping:
            raise DraftError('new_upload_binding_requires_review')
        mapping[local] = str(remote['id'])
    if set(mapping) != {t['track_id'] for t in selected}:
        raise DraftError('new_upload_binding_requires_review')
    return mapping


def review_live(path, *, account, draft, endpoint, alias=None, observed_binding=None):
    from pathlib import Path
    from .validation import load_manifest, validate_manifest
    if not re.fullmatch(r'http://127\.0\.0\.1:[0-9]{1,5}', endpoint) or not 1024 <= int(endpoint.rsplit(':', 1)[1]) <= 65535:
        raise DraftError('loopback_endpoint_required')
    path = Path(path).absolute()
    manifest = load_manifest(path)
    validate_manifest(manifest, path.parent)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as playwright:
        browser = playwright.chromium.connect_over_cdp(endpoint)
        if len(browser.contexts) != 1:
            raise DraftError('recovery_context_not_unique')
        tracks = observe_release(browser.contexts[0], account=account, draft=draft)
    if observed_binding is not None:
        record = verify_record(observed_binding)
        if any('editor_key' in t for t in record.get('snapshot') or []):
            raise DraftError('deferred_upload_binding_requires_review')
        from .recovery_state import content_digest, audio_identity
        if any(record.get(k) != v for k, v in dict(profile=alias, account=account,
                draft=draft).items()):
            raise DraftError('remote_binding_identity_mismatch')
        if record.get('manifest_sha256') != content_digest(manifest):
            if ('manifest' not in record or audio_identity(record['manifest']) != audio_identity(manifest)):
                raise DraftError('remote_binding_identity_mismatch')
        current = prepare_binding(manifest=manifest, account=account, draft=draft,
                                  tracks=tracks, mapping=record['mapping'])
        old_audio = {t['id']: t['audio_url_sha256'] for t in record['snapshot'] or []}
        new_audio = {t['id']: t['audio_url_sha256'] for t in current['snapshot']}
        if any(new_audio.get(rid) != digest for rid, digest in old_audio.items()):
            raise DraftError('remote_binding_review_changed')
        # IDs from the observed attempt take precedence over mutable titles.
        mapping = dict(record['mapping'])
    else:
        mapping = propose_mapping(manifest, tracks)
    review = prepare_binding(manifest=manifest, account=account, draft=draft, tracks=tracks, mapping=mapping)
    if alias is not None:
        review['review_digest'] = _digest({'review_digest': review['review_digest'], 'profile': alias})
        review['profile'] = alias
    return {**review, 'status': 'review_only', 'account_verified': True,
            'draft_verified': True, 'observation_provenance_verified': True}


def save_review_receipt(session, *, release_id, account, draft, review, approved_digest):
    """Simpan persetujuan ID; runtime masih memerlukan snapshot dan gate baru."""
    from .storage import _atomic_write, _read
    if session.closed:
        raise DraftError('remote_binding_invalid')
    name = session._check(release_id).removesuffix('.json') + '.binding.json'
    if (not isinstance(review, dict) or review.get('status') != 'review_only'
            or review.get('account_verified') is not True or review.get('draft_verified') is not True
            or review.get('observation_provenance_verified') is not True
            or review.get('retry_safe') is not False or review.get('execution_available') is not False
            or not isinstance(approved_digest, str) or not re.fullmatch(r'[0-9a-f]{64}', approved_digest)
            or review.get('review_digest') != approved_digest
            or review.get('account') != account or review.get('draft') != draft
            or ('profile' in review and review['profile'] != session.alias)
            or any(not isinstance(x, str) or not re.fullmatch(r'[1-9][0-9]*', x) for x in (account, draft))):
        raise DraftError('remote_binding_review_changed')
    record = {'version': 2, 'release_id': release_id, 'profile': session.alias,
              'account': account, 'draft': draft, 'review_digest': approved_digest,
              'mapping': review['mapping'], 'missing_track_ids': review['missing_track_ids'],
              'unmapped_remote_ids': review['unmapped_remote_ids'],
              'manifest_sha256': review['manifest_sha256'], 'snapshot': review['snapshot'],
              'remote_audio_hashes_verified': False, 'retry_safe': False}
    record['record_sha256'] = _digest(record)
    try:
        previous = _read(session.directory, name)
    except FileNotFoundError:
        _atomic_write(session.directory, name, record)
    else:
        verify_record(previous)
        if ({k: v for k, v in previous.items() if k not in ('history', 'record_sha256')} ==
                {k: v for k, v in record.items() if k != 'record_sha256'}):
            return previous
        record['history'] = previous.get('history', []) + [{k: v for k, v in previous.items() if k != 'history'}]
        record['record_sha256'] = _digest({k: v for k, v in record.items() if k != 'record_sha256'})
        _atomic_write(session.directory, name, record)
    return record


def verify_record(record):
    if (not isinstance(record, dict) or record.get('record_sha256') !=
            _digest({k: v for k, v in record.items() if k != 'record_sha256'})):
        raise DraftError('remote_binding_corrupt')
    return record


def load_receipt(session, manifest, account, draft):
    from .storage import _read
    try:
        record = verify_record(_read(session.directory, session._check(manifest['release_id']).removesuffix('.json') + '.binding.json'))
    except FileNotFoundError:
        raise DraftError('remote_binding_confirmation_required') from None
    if any(record.get(k) != v for k, v in dict(version=2, release_id=manifest['release_id'],
            profile=session.alias, account=account, draft=draft, manifest_sha256=_digest(manifest)).items()):
        raise DraftError('remote_binding_identity_mismatch')
    if record.get('unmapped_remote_ids'):
        raise DraftError('remote_binding_unmapped_tracks')
    return record
