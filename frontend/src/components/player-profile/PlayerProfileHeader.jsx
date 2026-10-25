import { handleTeamBadgeError } from '../../utils/imageFallbacks';
import { Coins, Star, TrendingUp } from 'lucide-react';
import PlayerAvatar from '../PlayerAvatar';

const SEASONS = [
  ['2026_27', '2026-27'],
  ['2025_26', '2025-26'],
  ['2024_25', '2024-25'],
  ['2023_24', '2023-24'],
  ['2022_23', '2022-23'],
  ['all', 'Tüm sezonlar'],
];

function RatingValue({ value }) {
  const color = value >= 7.5 ? 'text-status-success'
    : value >= 6.8 ? 'text-status-success'
      : value >= 6.0 ? 'text-status-info'
        : value ? 'text-status-warning' : 'text-text-muted';

  return (
    <div className="flex items-baseline justify-center sm:justify-start gap-1">
      <span className={`text-lg font-semibold tabular-nums tabular-nums ${color}`}>
        {value != null ? value.toFixed(1) : '—'}
      </span>
      {value != null && <span className="text-xs text-text-tertiary">/ 10</span>}
    </div>
  );
}

function SummaryMetric({ label, value, className = '' }) {
  return (
    <div className={`p-4 text-center sm:text-left ${className}`}>
      <span className="block text-xs font-medium text-text-secondary">{label}</span>
      <span className="text-lg font-semibold tabular-nums text-text-primary">{value}</span>
    </div>
  );
}

export default function PlayerProfileHeader({ player, stats, team, position, season, onSeasonChange, onOpenMarketValue }) {
  return (
    <section className="bg-background-primary border border-border rounded">
      <div className="flex flex-col gap-5 p-5 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-col sm:flex-row items-center sm:items-start gap-4 min-w-0">
          <PlayerAvatar player={player} size="xl" shape="circle" className="w-16 h-16 shrink-0" />
          <div className="min-w-0 text-center sm:text-left">
            <div className="flex flex-wrap items-center justify-center gap-2 sm:justify-start">
              <h1 className="text-2xl font-semibold text-text-primary tracking-tight">
                {player.name}
              </h1>
              {position && (
                <span className={`rounded-sm border px-2 py-0.5 text-xs font-medium ${position.class}`}>
                  {position.label}
                </span>
              )}
              {player.market_value && (
                <button
                  type="button"
                  onClick={onOpenMarketValue}
                  title={`${player.name} piyasa değeri geçmişi`}
                  className="inline-flex items-center gap-1.5 rounded-sm border border-border bg-background-tertiary hover:bg-background-secondary px-2.5 py-0.5 text-xs font-medium text-text-primary transition-colors cursor-pointer"
                >
                  <Coins className="w-3.5 h-3.5 text-text-secondary" />
                  <span className="tabular-nums">{player.market_value.formatted}</span>
                  <TrendingUp className="w-3 h-3 text-text-tertiary" />
                </button>
              )}
            </div>

            <div className="mt-1.5 flex flex-wrap items-center justify-center gap-x-3 gap-y-1 text-sm text-text-secondary sm:justify-start">
              {team && (
                <span className="inline-flex items-center gap-1.5 font-medium text-text-primary">
                  <img src={team.badge} alt="" className="h-4 w-4 object-contain" onError={handleTeamBadgeError} />
                  {team.name}
                </span>
              )}
              {player.country && <span>{player.country}</span>}
              {player.shirt && <span>Forma: #{player.shirt}</span>}
            </div>

            <p className="mt-2 text-xs text-text-tertiary">
              Premier League kariyeri <span className="mx-1">·</span>
              {player.total_appearances || 0} maç <span className="mx-1">·</span>
              {player.total_goals || 0} gol <span className="mx-1">·</span>
              {player.total_assists || 0} asist
            </p>
          </div>
        </div>

        <div className="flex shrink-0 items-center justify-center sm:justify-end gap-2">
          <label htmlFor="player-season-select" className="text-xs font-medium text-text-secondary">
            Sezon:
          </label>
          <select
            id="player-season-select"
            value={season}
            onChange={event => onSeasonChange(event.target.value)}
            className="h-9 rounded border border-border bg-background-primary px-3 text-sm font-medium text-text-primary outline-none focus:border-border-focus transition-colors"
          >
            {SEASONS.map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-2 divide-x divide-y divide-border-light border-t border-border-light sm:grid-cols-6 sm:divide-y-0">
        <SummaryMetric label="Maç" value={stats.appearances || 0} />
        <SummaryMetric label="Dakika" value={stats.minutes || 0} />
        <SummaryMetric label="Gol" value={stats.goals || 0} />
        <SummaryMetric label="Asist" value={stats.assists || 0} />
        <div className="p-4 text-center sm:text-left bg-background-tertiary/40">
          <div className="flex items-center justify-center sm:justify-start gap-1 mb-0.5">
            <span className="block text-xs font-medium text-text-secondary">Ort. Reyting</span>
            <Star className="w-3 h-3 text-status-warning fill-status-warning" />
          </div>
          <RatingValue value={stats.average_rating} />
        </div>
        <button
          type="button"
          onClick={() => player.market_value && onOpenMarketValue()}
          className={`p-4 text-center sm:text-left transition-colors ${
            player.market_value
              ? 'cursor-pointer hover:bg-background-tertiary/50'
              : 'cursor-default'
          }`}
          title={player.market_value ? `${player.name} piyasa değeri geçmişini görüntüle` : undefined}
        >
          <div className="flex items-center justify-center sm:justify-start gap-1 mb-0.5">
            <span className="block text-xs font-medium text-text-secondary">Piyasa Değeri</span>
            {player.market_value && <TrendingUp className="w-3 h-3 text-text-tertiary" />}
          </div>
          <span className="text-lg font-semibold tabular-nums text-text-primary block">
            {player.market_value ? player.market_value.formatted : '—'}
          </span>
        </button>
      </div>
    </section>
  );
}
