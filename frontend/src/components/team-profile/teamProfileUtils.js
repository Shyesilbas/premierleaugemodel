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

export function getPositionBadgeStyle(position) {
  const styles = {
    G: 'bg-amber-50 text-amber-700 border-amber-200',
    D: 'bg-sky-50 text-sky-700 border-sky-200',
    M: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    F: 'bg-purple-50 text-purple-700 border-purple-200',
  };
  return styles[getPlayerCategory(position)] || 'bg-slate-50 text-slate-700 border-slate-200';
}

