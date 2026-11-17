import React, { useMemo, useState } from 'react';
import { Calendar, ChevronRight, Search } from 'lucide-react';
import { useCompetition } from '../../context/competitionState';
import { getTeam } from '../../data/teams';
import { formatSeasonLabel, parseKickoff } from '../../utils/dateFormatters';
import { handleTeamBadgeError } from '../../utils/imageFallbacks';
import CompetitionBadge from '../team-profile/CompetitionBadge';
import { COMPETITIONS, competitionOf } from '../team-profile/teamProfileUtils';
import { Badge } from '../common/Badge';
import { Button } from '../common/Button';
import { Card } from '../common/Card';
import { Input } from '../common/Input';
import { Select } from '../common/Select';
import Skeleton from '../common/Skeleton';

const PAGE_SIZE = 20;

function foldText(s) {
  return String(s || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/ı/g, 'i')
    .replace(/İ/g, 'i')
    .toLowerCase()
    .trim();
}

function ratingBadgeClass(rating) {
  if (rating == null) return 'bg-background-tertiary text-text-muted border-border';
  if (rating >= 8.0) return 'bg-status-success/15 text-status-success border-status-success/30 font-semibold';
  if (rating >= 7.0) return 'bg-status-info/10 text-status-info border-status-info/30 font-medium';
  if (rating >= 6.0) return 'bg-background-tertiary text-text-primary border-border';
  return 'bg-status-warning/10 text-status-warning border-status-warning/30';
}

function sidesOf(match) {
  if (competitionOf(match).order > 0) {
    const home = getTeam(match.home_id, match.home_name);
    const away = getTeam(match.away_id, match.away_name);
    return { home, away, homeScore: match.home_score, awayScore: match.away_score };
  }
  const opponent = getTeam(match.opponent_id, match.opponent_name);
  const team = getTeam(match.team_id, match.team_name);
  const home = match.is_home ? team : opponent;
  const away = match.is_home ? opponent : team;
  return {
    home,
    away,
    homeScore: match.is_home ? match.team_score : match.opp_score,
    awayScore: match.is_home ? match.opp_score : match.team_score,
  };
}

function toMatchModalData(match) {
  if (competitionOf(match).order > 0) {
    return {
      match_id: match.match_id,
      status: match.team_score !== null && match.team_score !== undefined ? 'COMPLETED' : 'UNPLAYED',
      gameweek: match.gameweek,
      kickoff_label: match.kickoff,
      home_id: match.home_id,
      home_name: match.home_name,
      home_score: match.home_score,
      away_id: match.away_id,
      away_name: match.away_name,
      away_score: match.away_score,
      ground_name: match.ground_name || '',
      stage: match.stage,
      group: match.group,
    };
  }
  const opponent = getTeam(match.opponent_id, match.opponent_name);
  const team = getTeam(match.team_id, match.team_name);
  const home = match.is_home ? team : opponent;
  const away = match.is_home ? opponent : team;
  return {
    match_id: match.match_id,
    status: match.team_score !== null && match.team_score !== undefined ? 'COMPLETED' : 'UNPLAYED',
    gameweek: match.gameweek,
    kickoff_label: match.kickoff,
    home_id: home.id,
    home_name: home.name,
    home_score: match.is_home ? match.team_score : match.opp_score,
    away_id: away.id,
    away_name: away.name,
    away_score: match.is_home ? match.opp_score : match.team_score,
    ground_name: competitionOf(match).name,
  };
}

export default function PlayerMatchHistory({
  matches = [],
  playedMatchCount = 0,
  weeks = [],
  selectedWeek = 'all',
  onWeekChange,
  loading,
  season,
  onSelectMatch,
  hasEuropean = false,
  europeanStats = null,
  selectedCompetition = 'all',
  onCompetitionChange,
}) {
  const { competitionKey } = useCompetition();
  const [opponentQuery, setOpponentQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState('all');
  const [venueFilter, setVenueFilter] = useState('all');
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);

  const hasXg = useMemo(
    () => matches.some((m) => m.expected_goals != null),
    [matches],
  );

  const localFiltered = useMemo(() => {
    const q = foldText(opponentQuery);
    return matches.filter((m) => {
      if (roleFilter === 'starter' && !m.started) return false;
      if (roleFilter === 'sub' && m.started) return false;
      if (venueFilter === 'home' && !m.is_home) return false;
      if (venueFilter === 'away' && m.is_home) return false;
      if (q) {
        const opp = foldText(m.opponent_name || `${m.home_name || ''} ${m.away_name || ''}`);
        if (!opp.includes(q)) return false;
      }
      return true;
    });
  }, [matches, opponentQuery, roleFilter, venueFilter]);

  const orderedDescending = useMemo(() => [...localFiltered].reverse(), [localFiltered]);
  const visibleMatches = orderedDescending.slice(0, visibleCount);
  const colSpan = hasXg ? 8 : 7;

  return (
    <Card padding="none" className="overflow-hidden">
      <div className="flex flex-col gap-3 border-b border-border-light p-4 sm:px-5">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-start gap-2.5">
            <Calendar className="mt-0.5 h-4 w-4 shrink-0 text-text-secondary" strokeWidth={1.5} aria-hidden="true" />
            <div>
              <h2 className="text-base font-semibold text-text-primary">Maç günlüğü</h2>
              <p className="text-xs text-text-secondary tabular-nums">
                {playedMatchCount} oynanmış maç · {season === 'all' ? 'Tüm sezonlar' : formatSeasonLabel(season)}
                {localFiltered.length !== matches.length && ` · ${localFiltered.length} eşleşme`}
              </p>
              {europeanStats && (
                <p className="mt-0.5 text-xs text-text-secondary tabular-nums">
                  Avrupa: {europeanStats.appearances} maç · {europeanStats.minutes}' · {europeanStats.goals} gol · {europeanStats.assists} asist
                  {europeanStats.average_rating != null && ` · ort. ${europeanStats.average_rating.toFixed(1)}`}
                </p>
              )}
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="w-44">
              <Input
                value={opponentQuery}
                onChange={(e) => {
                  setOpponentQuery(e.target.value);
                  setVisibleCount(PAGE_SIZE);
                }}
                placeholder="Rakip ara..."
                aria-label="Rakip takıma göre filtrele"
                leftIcon={<Search className="h-3.5 w-3.5" aria-hidden="true" />}
              />
            </div>

            {hasEuropean && (
              <div className="w-40">
                <Select
                  id="competition-filter-select"
                  aria-label="Turnuva filtresi"
                  value={selectedCompetition}
                  onChange={(event) => {
                    onCompetitionChange?.(event.target.value);
                    setVisibleCount(PAGE_SIZE);
                  }}
                  options={[
                    { value: 'all', label: 'Tüm turnuvalar' },
                    ...Object.entries(COMPETITIONS)
                      .filter(([key, competition]) => competition.order > 0 || key === competitionKey)
                      .map(([key, competition]) => ({ value: key, label: competition.name })),
                  ]}
                />
              </div>
            )}

            {weeks.length > 0 && (
              <div className="w-36">
                <Select
                  id="gameweek-filter-select"
                  aria-label="Hafta filtresi"
                  value={selectedWeek}
                  onChange={(event) => {
                    onWeekChange?.(event.target.value);
                    setVisibleCount(PAGE_SIZE);
                  }}
                  options={[
                    { value: 'all', label: 'Tüm haftalar' },
                    ...weeks.map((w) => ({ value: String(w), label: `Hafta ${w}` })),
                  ]}
                />
              </div>
            )}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-1.5">
          {[
            { id: 'all', label: 'Tümü' },
            { id: 'starter', label: 'İlk 11' },
            { id: 'sub', label: 'Yedek' },
          ].map((pill) => (
            <button
              key={pill.id}
              type="button"
              aria-pressed={roleFilter === pill.id}
              onClick={() => {
                setRoleFilter(pill.id);
                setVisibleCount(PAGE_SIZE);
              }}
              className={`h-7 rounded border px-2.5 text-xs font-medium transition-colors cursor-pointer ${
                roleFilter === pill.id
                  ? 'border-primary bg-primary text-white'
                  : 'border-border bg-background-primary text-text-secondary hover:text-text-primary'
              }`}
            >
              {pill.label}
            </button>
          ))}
          <span className="mx-1 h-4 w-px bg-border-light" aria-hidden="true" />
          {[
            { id: 'all', label: 'İç/Dep' },
            { id: 'home', label: 'İç Saha' },
            { id: 'away', label: 'Deplasman' },
          ].map((pill) => (
            <button
              key={pill.id}
              type="button"
              aria-pressed={venueFilter === pill.id}
              onClick={() => {
                setVenueFilter(pill.id);
                setVisibleCount(PAGE_SIZE);
              }}
              className={`h-7 rounded border px-2.5 text-xs font-medium transition-colors cursor-pointer ${
                venueFilter === pill.id
                  ? 'border-primary bg-primary text-white'
                  : 'border-border bg-background-primary text-text-secondary hover:text-text-primary'
              }`}
            >
              {pill.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="space-y-2 p-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-11 w-full" />
          ))}
        </div>
      ) : !playedMatchCount ? (
        <div className="py-12 text-center text-xs font-medium text-text-secondary">
          Seçilen sezonda oyuncunun süre aldığı maç bulunamadı.
        </div>
      ) : visibleMatches.length === 0 ? (
        <div className="m-4 rounded border border-border bg-background-secondary py-10 text-center text-xs font-medium text-text-secondary">
          Seçili filtrelere uygun karşılaşma kaydı bulunmuyor.
        </div>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-border bg-background-tertiary text-xs text-text-secondary">
                  <th scope="col" className="py-2.5 pl-4 pr-3 font-medium whitespace-nowrap">Tarih / Tur</th>
                  <th scope="col" className="py-2.5 px-3 font-medium">Karşılaşma</th>
                  <th scope="col" className="py-2.5 px-3 font-medium whitespace-nowrap">Süre &amp; Rol</th>
                  <th scope="col" className="py-2.5 px-3 font-medium text-right">Gol</th>
                  <th scope="col" className="py-2.5 px-3 font-medium text-right">Asist</th>
                  {hasXg && <th scope="col" className="py-2.5 px-3 font-medium text-right">xG</th>}
                  <th scope="col" className="py-2.5 px-3 font-medium text-right">Reyting</th>
                  <th scope="col" className="py-2.5 pl-2 pr-4 w-8" />
                </tr>
              </thead>
              <tbody className="divide-y divide-border-light">
                {visibleMatches.map((match, idx) => {
                  const prevMatch = idx > 0 ? visibleMatches[idx - 1] : null;
                  const teamChanged = Boolean(
                    prevMatch && prevMatch.team_id && match.team_id && String(prevMatch.team_id) !== String(match.team_id),
                  );
                  const modalMatch = toMatchModalData(match);
                  const { home, away, homeScore, awayScore } = sidesOf(match);
                  const competition = competitionOf(match, competitionKey);
                  const played = match.team_score !== null && match.team_score !== undefined;
                  const kickoff = parseKickoff(match.kickoff);

                  return (
                    <React.Fragment key={`${match.match_id}-${idx}`}>
                      {teamChanged && (
                        <tr className="bg-background-tertiary">
                          <td colSpan={colSpan} className="px-4 py-1.5 text-xs font-medium text-text-secondary">
                            Kulüp değişimi: {match.team_name} → {prevMatch.team_name}
                          </td>
                        </tr>
                      )}
                      <tr
                        onClick={() => onSelectMatch(modalMatch)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            onSelectMatch(modalMatch);
                          }
                        }}
                        tabIndex={0}
                        className="group cursor-pointer transition-colors hover:bg-background-secondary focus-visible:outline-none focus-visible:bg-background-secondary"
                      >
                        <td className="py-2.5 pl-4 pr-3 whitespace-nowrap">
                          <span className="block text-xs font-medium text-text-primary tabular-nums">
                            {kickoff.date}
                          </span>
                          <div className="mt-0.5 flex items-center gap-1.5 text-xs text-text-tertiary tabular-nums">
                            {season === 'all' && <span>{formatSeasonLabel(match.season)}</span>}
                            {hasEuropean && <CompetitionBadge competition={competition} />}
                            <span>{competition.order > 0 ? match.round_label : `H${Math.round(Number(match.gameweek) || 1)}`}</span>
                            <span>·</span>
                            <span>{match.is_home ? 'İç' : 'Dep'}</span>
                          </div>
                        </td>

                        <td className="py-2.5 px-3 min-w-60">
                          <div className="flex items-center gap-2 text-xs">
                            <div className="flex min-w-0 flex-1 items-center justify-end gap-1.5 text-right">
                              <span className={`truncate ${match.is_home ? 'font-semibold text-text-primary' : 'text-text-secondary'}`}>
                                {home.short || home.name}
                              </span>
                              <img src={home.badge} alt="" className="h-4 w-4 shrink-0 object-contain" onError={handleTeamBadgeError} />
                            </div>
                            <span className="min-w-11 shrink-0 rounded-sm border border-border-light bg-background-secondary px-1.5 py-0.5 text-center font-semibold text-text-primary tabular-nums">
                              {played ? `${homeScore}-${awayScore}` : kickoff.time || 'vs'}
                            </span>
                            <div className="flex min-w-0 flex-1 items-center gap-1.5">
                              <img src={away.badge} alt="" className="h-4 w-4 shrink-0 object-contain" onError={handleTeamBadgeError} />
                              <span className={`truncate ${!match.is_home ? 'font-semibold text-text-primary' : 'text-text-secondary'}`}>
                                {away.short || away.name}
                              </span>
                            </div>
                          </div>
                        </td>

                        <td className="py-2.5 px-3 whitespace-nowrap">
                          <div className="flex items-center gap-1.5">
                            <span className="text-xs font-semibold text-text-primary tabular-nums">
                              {match.minutes_played || 0}'
                            </span>
                            <Badge variant={match.started ? 'neutral' : 'info'} size="sm">
                              {match.started ? 'İlk 11' : 'Yedek'}
                            </Badge>
                          </div>
                        </td>

                        <td className={`py-2.5 px-3 text-right tabular-nums ${Number(match.goals) > 0 ? 'font-semibold text-text-primary' : 'text-text-secondary'}`}>
                          {match.goals || 0}
                        </td>

                        <td className={`py-2.5 px-3 text-right tabular-nums ${Number(match.assists) > 0 ? 'font-semibold text-text-primary' : 'text-text-secondary'}`}>
                          {match.assists || 0}
                        </td>

                        {hasXg && (
                          <td className="py-2.5 px-3 text-right tabular-nums text-text-secondary">
                            {match.expected_goals != null ? Number(match.expected_goals).toFixed(2) : '—'}
                          </td>
                        )}

                        <td className="py-2.5 px-3 text-right tabular-nums">
                          <span className={`inline-block min-w-10 rounded-sm border px-1.5 py-0.5 text-center text-xs ${ratingBadgeClass(match.rating)}`}>
                            {match.rating != null ? match.rating.toFixed(1) : '—'}
                          </span>
                        </td>

                        <td className="py-2.5 pl-2 pr-4 text-right">
                          <ChevronRight className="h-4 w-4 text-text-muted transition-transform group-hover:translate-x-0.5" strokeWidth={1.5} aria-hidden="true" />
                        </td>
                      </tr>
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>

          {visibleMatches.length < orderedDescending.length && (
            <div className="flex items-center justify-between border-t border-border-light bg-background-secondary px-4 py-3 text-xs text-text-secondary">
              <span className="tabular-nums">
                {visibleMatches.length} / {orderedDescending.length} maç gösteriliyor
              </span>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setVisibleCount((prev) => prev + PAGE_SIZE)}
              >
                Daha fazla göster
              </Button>
            </div>
          )}
        </>
      )}
    </Card>
  );
}
