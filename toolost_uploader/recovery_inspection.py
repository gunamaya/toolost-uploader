"""Perbandingan snapshot recovery; bukan adapter browser atau bukti identitas akun."""

import re
import hashlib
import json
from pathlib import PurePath
from urllib.parse import urlsplit

from .live_journal import DraftError


_ACCOUNT_REQUEST = """async () => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 5000);
    try {
        const response = await fetch('/api/auth/me', {
            method: 'GET', credentials: 'same-origin', redirect: 'error',
            cache: 'no-store', signal: controller.signal
        });
        if (response.status !== 200 || response.redirected ||
            response.url !== 'https://toolost.com/api/auth/me' || !response.body) return null;
        const reader = response.body.getReader();
        let chunks = [], size = 0;
        while (true) {
            const {done, value} = await reader.read();
            if (done) break;
            size += value.length;
            if (size > 65536) { await reader.cancel(); return null; }
            chunks.push(value);
        }
        const bytes = new Uint8Array(size);
        let offset = 0;
        for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
        const data = JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(bytes));
        const id = data?.user?.id;
        return Number.isSafeInteger(id) && id > 0 ? String(id) : null;
    } catch (_) { return null; }
    finally { clearTimeout(timer); }
}"""


def verify_open_draft_account(page, *, expected_account, expected_draft):
    """Periksa akun pada page yang diberikan, tanpa memilih page atau navigasi."""
    if any(not isinstance(value, str) or not re.fullmatch(r'[1-9][0-9]*', value)
           for value in (expected_account, expected_draft)):
        raise DraftError('recovery_identity_unverified')

    def check_page():
        if page.is_closed() or page.url != 'https://toolost.com/uploader/edit/' + expected_draft:
            raise ValueError
        if page.locator('[role=dialog]:visible,[aria-modal=true]:visible').count() != 0:
            raise ValueError
        if page.locator('input[type=password]:visible,input[autocomplete=one-time-code]:visible').count() != 0:
            raise ValueError

    try:
        check_page()
        account = page.evaluate(_ACCOUNT_REQUEST)
        check_page()
        if not isinstance(account, str) or account != expected_account:
            raise ValueError
    except Exception:
        raise DraftError('recovery_identity_unverified') from None
    return {'account_verified': True, 'profile_verified': False,
            'persisted_state_verified': False, 'execution_available': False}


def prepare_review(*, manifest, expected_account, expected_profile, expected_draft, observation):
    """Buat fingerprint review lokal, bukan izin untuk menyentuh browser."""
    comparison = compare_snapshot(
        manifest=manifest, expected_account=expected_account, expected_profile=expected_profile,
        expected_draft=expected_draft, observation=observation,
    )
    try:
        payload = json.dumps(
            {'manifest': manifest, 'account': expected_account, 'profile': expected_profile,
             'draft': expected_draft, 'observation': observation},
            sort_keys=True, ensure_ascii=True, separators=(',', ':'), allow_nan=False,
        ).encode('utf-8')
    except (TypeError, ValueError, UnicodeError):
        raise DraftError('recovery_snapshot_ambiguous') from None
    return {**comparison, 'review_digest': hashlib.sha256(payload).hexdigest(),
            'execution_available': False}


def verify_review(*, approved_digest, manifest, expected_account, expected_profile, expected_draft, observation):
    """Validasi approval terhadap snapshot ulang; tetap tidak mengotorisasi mutasi."""
    review = prepare_review(
        manifest=manifest, expected_account=expected_account, expected_profile=expected_profile,
        expected_draft=expected_draft, observation=observation,
    )
    if not isinstance(approved_digest, str) or approved_digest != review['review_digest']:
        raise DraftError('recovery_review_changed_or_not_approved')
    return {**review, 'approval_matches_snapshot': True}


def compare_snapshot(*, manifest, expected_account, expected_profile, expected_draft, observation):
    """Bandingkan observasi yang disediakan caller, tanpa mengakses browser atau state.

    Caller bertanggung jawab atas asal observasi; fungsi ini tidak membuktikan
    bahwa account dan profile berasal dari browser yang sedang diperiksa.
    """
    try:
        if any(not isinstance(x, str) or not x for x in (expected_account, expected_profile, expected_draft)):
            raise ValueError
        if not re.fullmatch(r'[1-9][0-9]*', expected_draft):
            raise ValueError
        if (observation['account'] != expected_account or observation['profile'] != expected_profile
                or observation['closed'] is not False or observation['dialog_count'] != 0
                or type(observation['dialog_count']) is not int or observation['login_visible'] is not False):
            raise ValueError
        url = urlsplit(observation['url'])
        if (url.scheme != 'https' or url.netloc != 'toolost.com'
                or url.path != '/uploader/edit/' + expected_draft or url.query or url.fragment):
            raise ValueError
        tracks = manifest['tracks']
        labels = observation['track_labels']
        if not isinstance(tracks, list) or not tracks or not isinstance(labels, list) or len(labels) != len(tracks):
            raise ValueError
        lookup = {}
        track_ids = set()
        for index, track in enumerate(tracks):
            track_id = track['track_id']
            path = track['audio']['path']
            if not isinstance(track_id, str) or not track_id or track_id in track_ids or not isinstance(path, str) or not path:
                raise ValueError
            track_ids.add(track_id)
            name = PurePath(path).name.lower()
            stem = PurePath(path).stem.lower()
            if not stem:
                raise ValueError
            for label in {stem, name}:
                if label in lookup and lookup[label] != index:
                    raise ValueError
                lookup[label] = index
        order = []
        for text in labels:
            if not isinstance(text, str):
                raise ValueError
            label = re.sub(r'^\s*\d+\s*', '', text.lower()).strip()
            label = re.sub(r'\s*edit\s*$', '', label).strip()
            if label not in lookup:
                raise ValueError
            order.append(lookup[label])
        if len(set(order)) != len(tracks):
            raise ValueError
        return {
            'status': 'snapshot_comparison_only',
            'identity_verified': False,
            'remote_audio_hashes_verified': False,
            'observed_order': [tracks[i]['track_id'] for i in order],
            'desired_order': [track['track_id'] for track in tracks],
            'reorder_required': order != list(range(len(tracks))),
            'limitations': ['observation_provenance_unverified', 'remote_audio_hashes_not_proven',
                            'snapshot_not_persisted_state'],
        }
    except (KeyError, TypeError, ValueError, AttributeError):
        raise DraftError('recovery_snapshot_ambiguous') from None
