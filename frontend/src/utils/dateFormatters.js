export function formatSeasonLabel(season, separator = '-') {
  return season == null ? '' : String(season).replace('_', separator);
}

export function parseKickoff(label) {
  if (!label) return { date: '-', time: '' };
  const parts = String(label).split(',');
  if (parts.length < 2) return { date: parts[0].trim(), time: '' };
  return { date: parts[0].trim(), time: parts[1].trim().replace(/\s+(BST|GMT)/gi, '') };
}
