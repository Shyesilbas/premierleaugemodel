export const SQUAD_POSITION_TABS = [
  { id: 'all', label: 'Tümü' },
  { id: 'G', label: 'Kaleci' },
  { id: 'D', label: 'Savunma' },
  { id: 'M', label: 'Orta Saha' },
  { id: 'F', label: 'Forvet' },
];

export function getPlayerCategory(position) {
  if (!position) return 'other';
  const value = String(position).trim().toUpperCase();
  if (['G', 'GK', 'GOALKEEPER'].includes(value)) return 'G';
  if (['D', 'DEF', 'DEFENDER', 'CB', 'LB', 'RB', 'LWB', 'RWB'].includes(value)) return 'D';
  if (['M', 'MID', 'MIDFIELDER', 'CM', 'DM', 'AM', 'LM', 'RM'].includes(value)) return 'M';
  if (['F', 'FWD', 'FORWARD', 'ST', 'CF', 'RW', 'LW', 'ATT'].includes(value)) return 'F';
  return 'other';
}

export function getPositionOrder(category) {
  return ({ G: 1, D: 2, M: 3, F: 4 })[category] || 5;
}

export function getPositionLabel(position) {
  const labels = { G: 'Kaleci', D: 'Savunma', M: 'Orta Saha', F: 'Forvet' };
  return labels[getPlayerCategory(position)] || position || 'Oyuncu';
}

export const RESULT_META = {
  W: { label: 'G', title: 'Galibiyet', className: 'bg-status-success text-white' },
  D: { label: 'B', title: 'Beraberlik', className: 'bg-status-draw text-text-primary' },
  L: { label: 'M', title: 'Mağlubiyet', className: 'bg-status-error text-white' },
};

// Competitions a Premier League club's fixture list can contain, in the order used by the "by league" sort.
// Logos are the official emblems (cropped to the mark without the wordmark) kept under public/competitions.
export const COMPETITIONS = {
  premier_league: { key: 'premier_league', order: 0, abbr: 'PL', name: 'Premier League', logo: '/competitions/premier_league.svg', className: 'border-border text-text-secondary' },
  champions_league: { key: 'champions_league', order: 1, abbr: 'ŞL', name: 'Şampiyonlar Ligi', logo: '/competitions/champions_league.svg', className: 'border-status-info text-status-info' },
  europa_league: { key: 'europa_league', order: 2, abbr: 'AL', name: 'Avrupa Ligi', logo: '/competitions/europa_league.svg', className: 'border-status-warning text-status-warning' },
};

export const competitionOf = (match) => COMPETITIONS[match?.competition?.key] || COMPETITIONS.premier_league;
