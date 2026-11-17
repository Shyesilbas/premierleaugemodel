/** URL query-string router modeled after nbaModelApp/frontend/src/lib/router.ts. */

export function parseUrlRoute() {
  const params = new URLSearchParams(window.location.search);
  const rawTab = params.get('tab') || 'fixtures';
  const legacyHashMatch = /^#match-(\d+)$/.exec(window.location.hash || '');
  const matchId = params.get('matchId') || (legacyHashMatch ? legacyHashMatch[1] : null);
  const playerId = params.get('playerId');
  const team = params.get('team');
  const compareP1 = params.get('p1');
  const compareP2 = params.get('p2');

  return {
    tab: rawTab,
    matchId: matchId ? String(matchId) : null,
    playerId: playerId ? String(playerId) : null,
    team: team && !Number.isNaN(Number(team)) ? Number(team) : null,
    compareP1: compareP1 ? String(compareP1) : null,
    compareP2: compareP2 ? String(compareP2) : null,
  };
}

export function navigateTo(target = {}, replace = false) {
  const current = parseUrlRoute();
  const nextTab = target.tab !== undefined ? target.tab : current.tab;
  const isSameTab = nextTab === current.tab;
  const params = new URLSearchParams();

  if (nextTab && nextTab !== 'fixtures') {
    params.set('tab', nextTab);
  }

  if (nextTab === 'fixtures') {
    const matchId = target.matchId !== undefined ? target.matchId : isSameTab ? current.matchId : null;
    if (matchId != null) params.set('matchId', String(matchId));
  } else if (nextTab === 'players') {
    const playerId = target.playerId !== undefined ? target.playerId : isSameTab ? current.playerId : null;
    if (playerId != null) params.set('playerId', String(playerId));
  } else if (nextTab === 'teams') {
    const team = target.team !== undefined ? target.team : isSameTab ? current.team : null;
    if (team != null) params.set('team', String(team));
  } else if (nextTab === 'player-compare') {
    const p1 = target.compareP1 !== undefined ? target.compareP1 : isSameTab ? current.compareP1 : null;
    const p2 = target.compareP2 !== undefined ? target.compareP2 : isSameTab ? current.compareP2 : null;
    if (p1 != null) params.set('p1', String(p1));
    if (p2 != null) params.set('p2', String(p2));
  } else if (target.matchId) {
    params.set('matchId', String(target.matchId));
  }

  const qs = params.toString();
  const cleanHash = nextTab === 'fixtures' && !target.matchId && window.location.hash.startsWith('#match-')
    ? ''
    : window.location.hash;
  const nextUrl = `${window.location.pathname}${qs ? `?${qs}` : ''}${cleanHash}`;
  const currentUrl = `${window.location.pathname}${window.location.search}${window.location.hash}`;

  if (nextUrl === currentUrl) return;

  const statePayload = { ...current, ...target, tab: nextTab };
  if (replace) {
    window.history.replaceState(statePayload, '', nextUrl);
  } else {
    window.history.pushState(statePayload, '', nextUrl);
  }
  window.dispatchEvent(new PopStateEvent('popstate', { state: window.history.state }));
}

export function updateUrlRoute(state, replace = false) {
  navigateTo(state, replace);
}
