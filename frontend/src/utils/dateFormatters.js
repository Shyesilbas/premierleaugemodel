export function formatSeasonLabel(season, separator = '-') {
  return season == null ? '' : String(season).replace('_', separator);
}

export function parseKickoff(label) {
  if (!label) return { date: '-', time: '' };
  const parts = String(label).split(',');
  if (parts.length < 2) return { date: parts[0].trim(), time: '' };
  return { date: parts[0].trim(), time: parts[1].trim().replace(/\s+(BST|GMT)/gi, '') };
}

const KICKOFF_MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

// 'Sat 17 Oct 2026, 15:00 BST' -> sortable number (local clock, good enough to order matches); 0 when unknown.
export function kickoffSortKey(label) {
  const match = /(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})(?:,\s*(\d{1,2}):(\d{2}))?/.exec(label || '');
  const month = match ? KICKOFF_MONTHS.indexOf(match[2]) : -1;
  if (month === -1) return 0;
  return new Date(Number(match[3]), month, Number(match[1]), Number(match[4] || 0), Number(match[5] || 0)).getTime();
}
