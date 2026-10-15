/**
 * Team profile & tactical metrics client-side caching utility.
 * Saves requests by keeping data cached in localStorage until the team's next scheduled match completes.
 */

const CACHE_PREFIX = 'pl_team_cache_v3_';

/**
 * Retrieve cached data for a given category, team and season.
 * Returns null if no cache exists or if expired.
 */
export function getCachedTeamData(category, teamId, season) {
  try {
    const key = `${CACHE_PREFIX}${category}_${teamId}_${season}`;
    const raw = localStorage.getItem(key);
    if (!raw) return null;

    const record = JSON.parse(raw);
    if (!record || !record.data) return null;

    // Check expiry: if expiresAt is a timestamp and has passed, invalidate
    if (record.expiresAt !== null && record.expiresAt !== undefined) {
      if (Date.now() > record.expiresAt) {
        localStorage.removeItem(key);
        return null;
      }
    }

    return {
      data: record.data,
      cachedAt: record.cachedAt,
      expiresAt: record.expiresAt,
      nextMatchLabel: record.nextMatchLabel || null,
      isPermanent: record.expiresAt === null,
    };
  } catch (err) {
    console.warn('Failed to read from team cache:', err);
    return null;
  }
}

/**
 * Store data into localStorage with calculated expiry.
 */
export function setCachedTeamData(category, teamId, season, data, expiresAt = null, nextMatchLabel = null) {
  try {
    const key = `${CACHE_PREFIX}${category}_${teamId}_${season}`;
    const payload = {
      data,
      cachedAt: Date.now(),
      expiresAt,
      nextMatchLabel,
    };
    localStorage.setItem(key, JSON.stringify(payload));
  } catch (err) {
    console.warn('Failed to save to team cache:', err);
  }
}

/**
 * Calculate appropriate expiry timestamp for a team based on upcoming fixtures.
 * Historical completed seasons never expire.
 */
export function calculateTeamExpiry(nextMatch, season) {
  const isCurrentSeason = (season === '2026_27' || season === 'current');
  
  // Historical seasons never change
  if (!isCurrentSeason && season !== 'all') {
    return { expiresAt: null, label: 'Geçmiş sezon verisi (Süresiz)' };
  }

  if (nextMatch) {
    const matchTime = nextMatch.kickoff_millis;
    if (matchTime && typeof matchTime === 'number') {
      const matchEndTime = matchTime + (2.5 * 60 * 60 * 1000); // 2.5 hours after kickoff
      if (matchEndTime > Date.now()) {
        const dateStr = nextMatch.kickoff_label ? nextMatch.kickoff_label.split(',')[0] : 'Sıradaki maç';
        return {
          expiresAt: matchEndTime,
          label: `Sonraki maç: ${nextMatch.opponent_name || ''} (${dateStr})`,
        };
      } else {
        // Scheduled in past, waiting for match ingestion
        return {
          expiresAt: Date.now() + (15 * 60 * 1000),
          label: 'Maç sonucu bekleniyor (15 dk)',
        };
      }
    }
  }

  // Fallback if no next match found (e.g. season end or unknown): 12 hours
  return {
    expiresAt: Date.now() + (12 * 60 * 60 * 1000),
    label: '12 saat geçerli',
  };
}

/**
 * Clear cached team categories (used on manual refresh)
 */
export function clearTeamCache(teamId, season) {
  try {
    const categories = ['profile', 'tactics', 'scenarios', 'attackers'];
    categories.forEach(cat => {
      localStorage.removeItem(`${CACHE_PREFIX}${cat}_${teamId}_${season}`);
    });
    localStorage.removeItem(`${CACHE_PREFIX}manager_changes_all_${season}`);
    localStorage.removeItem(`${CACHE_PREFIX}fixtures_grouped_all_${season}`);
    localStorage.removeItem(`${CACHE_PREFIX}standings_all_${season}`);
    localStorage.removeItem(`${CACHE_PREFIX}staff_all_${season}`);
  } catch (err) {
    console.warn('Failed to clear team cache:', err);
  }
}
