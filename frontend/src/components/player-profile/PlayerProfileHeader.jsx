import React, { useMemo } from 'react';
import { ArrowLeftRight, ChevronRight, Star, TrendingUp } from 'lucide-react';
import { useCompetition } from '../../context/competitionState';
import { seasonsFor } from '../../data/seasons';
import { getTeam } from '../../data/teams';
import { formatSeasonLabel, kickoffSortKey } from '../../utils/dateFormatters';
import { handleTeamBadgeError } from '../../utils/imageFallbacks';
import PlayerAvatar from '../PlayerAvatar';
import { Badge } from '../common/Badge';
import { Button } from '../common/Button';
import { Card } from '../common/Card';
import { Select } from '../common/Select';

const SEASONS = [
  ['2026_27', '2026-27'],
  ['2025_26', '2025-26'],
  ['2024_25', '2024-25'],
  ['2023_24', '2023-24'],
  ['2022_23', '2022-23'],
  ['all', 'Tüm sezonlar'],
];

function ratingColor(value) {
  if (value == null) return 'text-text-muted';
  if (value >= 7.5) return 'text-status-success';
  if (value >= 6.8) return 'text-status-info';
  if (value >= 6.0) return 'text-text-primary';
  return 'text-status-warning';
}

export default function PlayerProfileHeader({
  player,
  stats,
  matches = [],
  europeanStats = null,
  team,
  position,
  season,
  onSeasonChange,
  onOpenMarketValue,
  onCompare,
}) {
  const { activeCompetition, competitionKey, hasRichData } = useCompetition();
  const seasonChoices = SEASONS
    .filter(([value]) => seasonsFor(competitionKey).includes(value))
    .map(([value, label]) => ({ value, label }));

  const clubChain = useMemo(() => {
    const ordered = [...matches].sort((a, b) => kickoffSortKey(a.kickoff) - kickoffSortKey(b.kickoff));
    const chain = [];
    ordered.forEach((m) => {
      if (!m.team_id) return;
      const prev = chain[chain.length - 1];
      if (!prev || String(prev.id) !== String(m.team_id)) {
        chain.push(getTeam(m.team_id, m.team_name));
      }
    });
    if (chain.length === 0 && team) {
      chain.push(team);
    }
    return chain;
  }, [matches, team]);

  const appearances = Number(stats.appearances || 0);
  const minutes = Number(stats.minutes || 0);
  const goals = Number(stats.goals || 0);
  const assists = Number(stats.assists || 0);
  const ga = goals + assists;
  const startsCount = useMemo(() => matches.filter((m) => Boolean(m.started)).length, [matches]);
  const minsPerMatch = appearances > 0 ? Math.round(minutes / appearances) : 0;
  const gaPer90 = minutes > 0 ? ((ga * 90) / minutes).toFixed(2) : '0.00';
  const goalsPer90 = minutes > 0 ? ((goals * 90) / minutes).toFixed(2) : '0.00';
  const avgRating = stats.average_rating != null ? Number(stats.average_rating) : null;

  return (
    <Card padding="md" className="space-y-5">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex flex-col items-center gap-4 text-center sm:flex-row sm:items-start sm:text-left min-w-0">
          <PlayerAvatar player={player} size="xl" shape="circle" className="h-16 w-16 shrink-0" />
          <div className="min-w-0 space-y-2">
            <div className="flex flex-wrap items-center justify-center gap-2 sm:justify-start">
              <h1 className="text-2xl font-semibold text-text-primary tracking-tight">
                {player.name}
              </h1>
              {position && <Badge variant="neutral">{position.label}</Badge>}
              {player.shirt && (
                <Badge variant="neutral" className="font-mono tabular-nums">
                  #{player.shirt}
                </Badge>
              )}
            </div>

            <div className="flex flex-wrap items-center justify-center gap-x-2 gap-y-1 text-sm text-text-secondary sm:justify-start">
              {clubChain.map((club, idx) => (
                <React.Fragment key={`${club.id}-${idx}`}>
                  {idx > 0 && <ChevronRight className="h-3.5 w-3.5 text-text-muted shrink-0" aria-hidden="true" />}
                  <span className="inline-flex items-center gap-1.5 font-medium text-text-primary">
                    <img
                      src={club.badge}
                      alt=""
                      className="h-4 w-4 shrink-0 object-contain"
                      onError={handleTeamBadgeError}
                    />
                    <span>{club.name}</span>
                  </span>
                </React.Fragment>
              ))}
              {player.country && (
                <>
                  {clubChain.length > 0 && <span aria-hidden="true">·</span>}
                  <span>{player.country}</span>
                </>
              )}
            </div>

            <p className="text-xs text-text-tertiary tabular-nums">
              {hasRichData ? `${activeCompetition.name} kariyeri` : `${activeCompetition.name} · ${formatSeasonLabel(season)}`}
              <span className="mx-1.5">·</span>
              {(hasRichData ? player.total_appearances : appearances) || 0} maç
              <span className="mx-1.5">·</span>
              {(hasRichData ? player.total_goals : goals) || 0} gol
              <span className="mx-1.5">·</span>
              {(hasRichData ? player.total_assists : assists) || 0} asist
              {europeanStats && (
                <>
                  <span className="mx-1.5">·</span>
                  <span>
                    Avrupa: {europeanStats.appearances} maç, {europeanStats.goals}G/{europeanStats.assists}A
                  </span>
                </>
              )}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap shrink-0 items-center justify-center gap-2 sm:justify-end">
          {onCompare && (
            <Button
              variant="secondary"
              size="md"
              leftIcon={<ArrowLeftRight className="h-3.5 w-3.5" strokeWidth={1.5} aria-hidden="true" />}
              onClick={() => onCompare(player.id)}
              title={`${player.name} ile başka bir oyuncuyu karşılaştır`}
            >
              Karşılaştır
            </Button>
          )}
          <div className="w-40">
            <Select
              id="player-season-select"
              aria-label="Sezon seç"
              value={season}
              onChange={(event) => onSeasonChange(event.target.value)}
              options={seasonChoices}
            />
          </div>
        </div>
      </div>

      {/* Tier 1: 4 Primary KPI Tiles */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <div className="rounded border border-border bg-background-secondary p-4">
          <span className="block text-xs font-medium text-text-secondary">Maç</span>
          <span className="mt-1 block text-2xl font-semibold text-text-primary tabular-nums">
            {appearances}
          </span>
          <span className="mt-1 block text-xs text-text-tertiary tabular-nums">
            {startsCount} ilk 11 · {Math.max(0, appearances - startsCount)} yedek
          </span>
        </div>

        <div className="rounded border border-border bg-background-secondary p-4">
          <span className="block text-xs font-medium text-text-secondary">Gol</span>
          <span className="mt-1 block text-2xl font-semibold text-text-primary tabular-nums">
            {goals}
          </span>
          <span className="mt-1 block text-xs text-text-tertiary tabular-nums">
            90 dk başı: {goalsPer90}
          </span>
        </div>

        <div className="rounded border border-border bg-background-secondary p-4">
          <span className="block text-xs font-medium text-text-secondary">Asist</span>
          <span className="mt-1 block text-2xl font-semibold text-text-primary tabular-nums">
            {assists}
          </span>
          <span className="mt-1 block text-xs text-text-tertiary tabular-nums">
            G+A katkısı: {ga}
          </span>
        </div>

        <div className="rounded border border-border bg-background-secondary p-4">
          <div className="flex items-center gap-1.5">
            <span className="block text-xs font-medium text-text-secondary">Ort. Reyting</span>
            <Star className="h-3.5 w-3.5 text-status-warning fill-status-warning" aria-hidden="true" />
          </div>
          <div className="mt-1 flex items-baseline gap-1">
            <span className={`text-2xl font-semibold tabular-nums ${ratingColor(avgRating)}`}>
              {avgRating != null ? avgRating.toFixed(1) : '—'}
            </span>
            {avgRating != null && <span className="text-xs text-text-tertiary">/ 10</span>}
          </div>
          <span className="mt-1 block text-xs text-text-tertiary tabular-nums">
            {stats.rated_matches_count ? `${stats.rated_matches_count} maçlık puan` : 'Reyting verisi yok'}
          </span>
        </div>
      </div>

      {/* Tier 2: 6 Secondary Metrics + Single Market Value CTA */}
      <div className="grid grid-cols-2 gap-px overflow-hidden rounded border border-border bg-border sm:grid-cols-3 lg:grid-cols-6">
        <div className="bg-background-primary p-3.5">
          <span className="block text-xs text-text-secondary">İlk 11</span>
          <span className="mt-0.5 block text-base font-semibold text-text-primary tabular-nums">
            {startsCount}
          </span>
        </div>

        <div className="bg-background-primary p-3.5">
          <span className="block text-xs text-text-secondary">Toplam Dakika</span>
          <span className="mt-0.5 block text-base font-semibold text-text-primary tabular-nums">
            {minutes.toLocaleString('tr-TR')}'
          </span>
        </div>

        <div className="bg-background-primary p-3.5">
          <span className="block text-xs text-text-secondary">Dk / Maç</span>
          <span className="mt-0.5 block text-base font-semibold text-text-primary tabular-nums">
            {minsPerMatch}'
          </span>
        </div>

        <div className="bg-background-primary p-3.5">
          <span className="block text-xs text-text-secondary">Gol + Asist</span>
          <span className="mt-0.5 block text-base font-semibold text-text-primary tabular-nums">
            {ga}
          </span>
        </div>

        <div className="bg-background-primary p-3.5">
          <span className="block text-xs text-text-secondary">G+A / 90 Dk</span>
          <span className="mt-0.5 block text-base font-semibold text-text-primary tabular-nums">
            {gaPer90}
          </span>
        </div>

        <button
          type="button"
          onClick={() => player.market_value && onOpenMarketValue?.()}
          disabled={!player.market_value}
          title={player.market_value ? `${player.name} piyasa değeri geçmişini görüntüle` : undefined}
          className={`bg-background-primary p-3.5 text-left transition-colors ${
            player.market_value
              ? 'cursor-pointer hover:bg-background-secondary'
              : 'cursor-default'
          }`}
        >
          <div className="flex items-center justify-between gap-1">
            <span className="block text-xs text-text-secondary">Piyasa Değeri</span>
            {player.market_value && <TrendingUp className="h-3.5 w-3.5 text-text-tertiary" aria-hidden="true" />}
          </div>
          <span className="mt-0.5 block text-base font-semibold text-text-primary tabular-nums">
            {player.market_value ? player.market_value.formatted : '—'}
          </span>
        </button>
      </div>
    </Card>
  );
}
