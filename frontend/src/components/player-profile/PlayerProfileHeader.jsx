import { handleTeamBadgeError } from '../../utils/imageFallbacks';
import { Coins, Star, TrendingUp } from 'lucide-react';
import PlayerAvatar from '../PlayerAvatar';

const SEASONS = [
  ['2026_27', '2026-27'], ['2025_26', '2025-26'], ['2024_25', '2024-25'],
  ['2023_24', '2023-24'], ['2022_23', '2022-23'], ['all', 'Tüm sezonlar'],
];

function RatingValue({ value }) {
  const color = value >= 7.5 ? 'text-emerald-700'
    : value >= 6.8 ? 'text-emerald-600'
      : value >= 6.0 ? 'text-sky-700'
        : value ? 'text-amber-700' : 'text-slate-400';
  return (
    <div className="flex items-baseline justify-center sm:justify-start gap-1">
      <strong className={`text-lg font-black tabular-nums font-mono ${color}`}>
        {value != null ? value.toFixed(1) : '—'}
      </strong>
      {value != null && <span className="text-[10px] font-semibold text-slate-400">/ 10</span>}
    </div>
  );
}

function SummaryMetric({ label, value, className = '' }) {
  return (
    <div className={`px-4 py-3 text-center sm:text-left sm:px-6 ${className}`}>
      <span className="block text-[10px] font-semibold uppercase tracking-wide text-slate-500">{label}</span>
      <strong className="text-lg font-bold tabular-nums text-slate-900">{value}</strong>
    </div>
  );
}

export default function PlayerProfileHeader({ player, stats, team, position, season, onSeasonChange, onOpenMarketValue }) {
  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex flex-col gap-5 p-4 sm:flex-row sm:items-center sm:p-6">
        <PlayerAvatar player={player} size="lg" className="h-20 w-20 rounded-2xl" />
        <div className="min-w-0 flex-1 text-center sm:text-left">
          <div className="flex flex-wrap items-center justify-center gap-2 sm:justify-start">
            <h2 className="text-2xl font-black tracking-tight text-slate-950">{player.name}</h2>
            {position && <span className={`rounded-md border px-2 py-0.5 text-[11px] font-semibold ${position.class}`}>{position.label}</span>}
            {player.market_value && (
              <button type="button" onClick={onOpenMarketValue} title={`${player.name} kariyer piyasa değeri grafiğini görüntüle`} className="inline-flex items-center gap-1.5 rounded-md border border-amber-300 bg-amber-50 hover:bg-amber-100 px-2.5 py-0.5 text-[11px] font-black text-amber-900 font-mono shadow-2xs transition cursor-pointer active:scale-95 group">
                <Coins className="w-3 h-3 text-amber-700" />
                <span>Piyasa Değeri: {player.market_value.formatted}</span>
                <TrendingUp className="w-2.5 h-2.5 text-amber-600 opacity-60 group-hover:opacity-100 transition-opacity" />
              </button>
            )}
          </div>
          <div className="mt-1.5 flex flex-wrap items-center justify-center gap-x-3 gap-y-1 text-sm text-slate-600 sm:justify-start">
            {team && <span className="inline-flex items-center gap-1.5 font-semibold text-slate-800"><img src={team.badge} alt="" className="h-4 w-4 object-contain" onError={handleTeamBadgeError} />{team.name}</span>}
            {player.country && <span>{player.country}</span>}
            {player.shirt && <span>Forma no: {player.shirt}</span>}
          </div>
          <p className="mt-2 text-xs text-slate-500">
            Premier League kariyeri <span className="mx-1">·</span>{player.total_appearances || 0} maç <span className="mx-1">·</span>{player.total_goals || 0} gol <span className="mx-1">·</span>{player.total_assists || 0} asist
          </p>
        </div>
        <label className="flex shrink-0 items-center gap-2 self-center text-xs font-semibold text-slate-500 sm:self-start">
          Sezon
          <select value={season} onChange={event => onSeasonChange(event.target.value)} className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-800 outline-none focus:border-slate-400">
            {SEASONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
      </div>

      <div className="grid grid-cols-2 divide-x divide-y divide-slate-200 border-t border-slate-200 sm:grid-cols-6 sm:divide-y-0">
        <SummaryMetric label="Maç" value={stats.appearances || 0} />
        <SummaryMetric label="Dakika" value={stats.minutes || 0} />
        <SummaryMetric label="Gol" value={stats.goals || 0} />
        <SummaryMetric label="Asist" value={stats.assists || 0} />
        <div className="px-4 py-3 text-center sm:text-left sm:px-6 bg-slate-50/60">
          <div className="flex items-center justify-center sm:justify-start gap-1"><span className="block text-[10px] font-bold uppercase tracking-wide text-slate-600">Ort. Reyting</span><Star className="w-2.5 h-2.5 text-amber-500 fill-amber-500" /></div>
          <RatingValue value={stats.average_rating} />
        </div>
        <button type="button" onClick={() => player.market_value && onOpenMarketValue()} className={`px-4 py-3 text-center sm:text-left sm:px-6 bg-amber-50/40 ${player.market_value ? 'cursor-pointer hover:bg-amber-100/60 transition group' : 'cursor-default'}`} title={player.market_value ? `${player.name} kariyer piyasa değeri grafiğini görüntüle` : undefined}>
          <div className="flex items-center justify-center sm:justify-start gap-1"><span className="block text-[10px] font-bold uppercase tracking-wide text-amber-800">Transfermarkt</span>{player.market_value && <TrendingUp className="w-2.5 h-2.5 text-amber-600 opacity-60 group-hover:opacity-100" />}</div>
          <strong className="text-lg font-black tabular-nums text-amber-950 font-mono">{player.market_value ? player.market_value.formatted : '—'}</strong>
        </button>
      </div>
    </section>
  );
}
