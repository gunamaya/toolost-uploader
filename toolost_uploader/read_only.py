"""Snapshot DOM list/detail yang sudah terbuka; tanpa navigasi, click atau network API."""

from datetime import datetime, timezone
import re
from urllib.parse import urlsplit


class ObservationError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def page_kind(url):
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.netloc not in ('toolost.com', 'www.toolost.com') or parsed.query or parsed.fragment:
        raise ObservationError('unsupported_page')
    if re.fullmatch(r'/user-portal/releases/manage/[1-9][0-9]*', parsed.path):
        return 'list', None
    match = re.fullmatch(r'/user-portal/releases/view/([0-9]+)/info', parsed.path)
    if match:
        return 'detail', match[1]
    raise ObservationError('unsupported_page')


def _remote_id(href, origin):
    if not isinstance(href, str):
        return None
    if href.startswith('/') and not href.startswith('//'):
        href = origin + href
    try:
        kind, remote_id = page_kind(href)
        return remote_id if kind == 'detail' else None
    except ObservationError:
        return None


def parse_snapshot(url, snapshot):
    kind, target = page_kind(url)
    if not isinstance(snapshot, dict) or snapshot.get('kind') != kind:
        raise ObservationError('incomplete_observation')
    if snapshot.get('auth') is not False:
        raise ObservationError('login_required_or_unknown')
    if snapshot.get('dialog') is not False:
        raise ObservationError('active_dialog')
    if snapshot.get('ready') is not True:
        raise ObservationError('incomplete_observation')
    origin = 'https://' + urlsplit(url).netloc
    result = dict(status='partial', account_identity=None, account_verified=False,
                  observed_at=datetime.now(timezone.utc).isoformat(), kind=kind,
                  coverage={'complete': False, 'limitations': ['account_identity_unverified']})
    if kind == 'list':
        cards = snapshot.get('cards')
        if not isinstance(cards, list) or not cards:
            raise ObservationError('empty_or_incomplete_observation')
        items = []
        seen = set()
        for card in cards:
            if not isinstance(card, dict):
                raise ObservationError('incomplete_observation')
            remote_id = _remote_id(card.get('href'), origin)
            title = card.get('title')
            if not isinstance(title, str) or not title.strip():
                raise ObservationError('incomplete_observation')
            if remote_id is not None and remote_id in seen:
                raise ObservationError('ambiguous_release_identity')
            if remote_id:
                seen.add(remote_id)
            items.append(dict(remote_release_id=remote_id, title=title.strip(),
                              remote_status={'normalized': 'unknown', 'raw': None}))
        result['items'] = items
        result['coverage']['limitations'] += ['pagination_unverified', 'status_mapping_unverified', 'visible_cards_only']
    else:
        title = snapshot.get('title')
        tracks = snapshot.get('tracks')
        if not isinstance(title, str) or not title.strip() or not isinstance(tracks, list):
            raise ObservationError('incomplete_observation')
        # Validate only exact target link observed on detail, not a guessed title match.
        edit_path = snapshot.get('edit_href')
        if edit_path != '/uploader/edit/' + target:
            raise ObservationError('release_identity_unverified')
        if any(not isinstance(t, str) or not t.strip() for t in tracks):
            raise ObservationError('incomplete_observation')
        result.update(remote_release_id=target, title=title.strip(),
                      tracks=[dict(position=i + 1, title=t.strip(), remote_track_id=None,
                                   identity_verified=False) for i, t in enumerate(tracks)])
        result['coverage']['limitations'] += ['remote_track_identity_unverified', 'metadata_artwork_options_not_observed',
                                               'empty_track_list_not_proof_of_absence']
    return result


def observe_page(page):
    """Caller owns login/navigation; this function only reads the current DOM."""
    initial_url = page.url
    kind, _ = page_kind(initial_url)
    try:
        data = page.evaluate('''kind => {
          const visible = e => e.getClientRects().length > 0;
          const all = s => [...document.querySelectorAll(s)].filter(visible);
          const auth = all('input[type="password"], input[autocomplete="one-time-code"], form[action*="login"]').length > 0
            || all('button,a').some(e => /^(sign in|log in|login|continue with google)$/i.test(e.innerText.trim()))
            || [...document.querySelectorAll('iframe[src]')].some(e => /accounts\\.google\\.com|captcha/i.test(e.getAttribute('src')));
          if (auth) return {kind, auth:true};
          const dialog = all('[role="dialog"], [aria-modal="true"]').length > 0;
          if (dialog) return {kind, auth:false, dialog:true};
          if (kind === 'list') {
            const cards = all('.release-grid-card');
            return {kind, auth:false, dialog:false, ready:cards.length > 0,
              cards:cards.map(e => ({title:e.querySelector('.release-grid-card__title')?.innerText,
                                    href:e.querySelector('.release-grid-card__title')?.getAttribute('href')}))};
          }
          const titles = all('.rs-hero__title');
          const edits = all('a[href]').filter(e => /^\\/uploader\\/edit\\/[0-9]+$/.test(e.getAttribute('href')));
          return {kind, auth:false, dialog:false, ready:titles.length === 1 && edits.length === 1,
            title:titles.length === 1 ? titles[0].innerText : null,
            edit_href:edits.length === 1 ? edits[0].getAttribute('href') : null,
            tracks:all('.release-track-item').map(e => e.querySelector('.release-track-item__title')?.innerText)};
        }''', kind)
        final_url = page.url
        if final_url != initial_url:
            raise ObservationError('page_changed')
        return parse_snapshot(final_url, data)
    except ObservationError:
        raise
    except Exception:
        raise ObservationError('observation_failed') from None
