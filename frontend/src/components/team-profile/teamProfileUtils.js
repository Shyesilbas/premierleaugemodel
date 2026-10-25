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
