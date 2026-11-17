import React, { useMemo, useState } from 'react';
import { ArrowDown, ArrowUp, ArrowUpDown, SearchX, Users } from 'lucide-react';
import { getTeam } from '../../data/teams';
import { formatSeasonLabel } from '../../utils/dateFormatters';
import { handleTeamBadgeError } from '../../utils/imageFallbacks';
import PlayerAvatar from '../PlayerAvatar';
import { Card } from '../common/Card';
import { Button } from '../common/Button';
import EmptyState from '../common/EmptyState';
import InlineError from '../common/InlineError';
import { Select } from '../common/Select';
import Skeleton from '../common/Skeleton';

const POSITION_LABELS = {
  G: 'Kaleci',
  GK: 'Kaleci',
  D: 'Defans',
  DEF: 'Defans',
  M: 'Orta Saha',
  MID: 'Orta Saha',
  F: 'Forvet',
  FWD: 'Forvet',
};

const POSITION_GROUPS = {
  G: 'G',
  GK: 'G',
  D: 'D',
  DEF: 'D',
  M: 'M',
  MID: 'M',
  F: 'F',
  FWD: 'F',
};

const PAGE_SIZE = 25;

function ratingTone(value) {
  if (value == null) return 'text-text-muted';
  if (value >= 7.4) return 'text-status-success font-semibold';
  if (value >= 6.8) return 'text-status-info font-medium';
  if (value >= 6.2) return 'text-text-primary';
  return 'text-status-warning';
}

function formatMoneyShort(eurMillions) {
  if (eurMillions == null || Number.isNaN(Number(eurMillions)) || Number(eurMillions) <= 0) return '—';
  const val = Number(eurMillions);
  return val >= 1000 ? `€${(val / 1000).toFixed(2)}B` : `€${val.toFixed(1)}M`;
}

function DiscoverySkeleton() {
  return (
    <Card padding="md" className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Skeleton className="h-6 w-48" />
        <div className="flex gap-2">
          <Skeleton className="h-9 w-32" />
          <Skeleton className="h-9 w-36" />
          <Skeleton className="h-9 w-32" />
        </div>
      </div>
      <div className="space-y-2">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    </Card>
  );
}

export default function PlayerDiscoveryGrid({
  compareData,
  loading,
  error,
  onRetry,
  season,
  onSeasonChange,
  onSelectPlayer,
}) {
  const [teamFilter, setTeamFilter] = useState('all');
  const [positionFilter, setPositionFilter] = useState('all');
  const [sortBy, setSortBy] = useState('goals');
  const [sortDir, setSortDir] = useState('desc');
  const [visibleLimit, setVisibleLimit] = useState(PAGE_SIZE);

  const availableSeasons = useMemo(() => {
    const raw = compareData?.seasons || [];
    if (raw.length === 0) {
      return [
        { value: '2026_27', label: '2026-27' },
        { value: '2025_26', label: '2025-26' },
        { value: '2024_25', label: '2024-25' },
        { value: '2023_24', label: '2023-24' },
        { value: '2022_23', label: '2022-23' },
        { value: 'all', label: 'Tüm sezonlar' },
      ];
    }
    return raw.map((s) => ({
      value: s,
      label: s === 'all' ? 'Tüm sezonlar' : formatSeasonLabel(s),
    }));
  }, [compareData?.seasons]);

  const activeSeason = useMemo(() => {
    const keys = availableSeasons.map((s) => s.value);
    if (keys.includes(season)) return season;
    return keys[0] || '2026_27';
  }, [availableSeasons, season]);

  const rows = useMemo(() => {
    const profiles = compareData?.profiles || [];
    const averages = compareData?.averages || {};
    const list = [];
    profiles.forEach((profile) => {
      const seasonMap = averages[String(profile.id)] || {};
      const stats = seasonMap[activeSeason];
      if (!stats || !stats.appearances) return;
      const teamIds = stats.teams || [];
      const latestTeamId = teamIds.length > 0 ? teamIds[teamIds.length - 1] : profile.teamId;
      const teamNames = stats.team_names || [];
      const latestTeamName = teamNames.length > 0 ? teamNames[teamNames.length - 1] : profile.teamName;
      list.push({
        id: profile.id,
        name: profile.name,
        photo_url: profile.photo_url,
        shirt: profile.shirt,
        position: profile.position,
        posGroup: POSITION_GROUPS[profile.position] || '',
        posLabel: POSITION_LABELS[profile.position] || profile.position || '—',
        teamId: latestTeamId,
        teamName: latestTeamName || profile.teamName,
        appearances: Number(stats.appearances || 0),
        starts: Number(stats.starts || 0),
        minutes: Number(stats.minutes || 0),
        goals: Number(stats.goals || 0),
        assists: Number(stats.assists || 0),
        goals_plus_assists: Number(stats.goals_plus_assists ?? (Number(stats.goals || 0) + Number(stats.assists || 0))),
        ga_per_90: Number(stats.ga_per_90 || 0),
        expected_goals: stats.expected_goals != null ? Number(stats.expected_goals) : null,
        avg_rating: stats.avg_rating != null ? Number(stats.avg_rating) : null,
        market_value_eur: profile.market_value_eur != null ? Number(profile.market_value_eur) : null,
      });
    });
    return list;
  }, [compareData, activeSeason]);

  const hasXg = useMemo(() => rows.some((r) => r.expected_goals != null && r.expected_goals > 0), [rows]);

  const teamOptions = useMemo(() => {
    const map = new Map();
    rows.forEach((r) => {
      if (r.teamId && r.teamName && !map.has(String(r.teamId))) {
        map.set(String(r.teamId), r.teamName);
      }
    });
    return [...map.entries()]
      .sort((a, b) => a[1].localeCompare(b[1], 'tr'))
      .map(([id, name]) => ({ value: id, label: name }));
  }, [rows]);

  const filteredAndSorted = useMemo(() => {
    let list = rows;
    if (teamFilter !== 'all') {
      list = list.filter((r) => String(r.teamId) === String(teamFilter));
    }
    if (positionFilter !== 'all') {
      list = list.filter((r) => r.posGroup === positionFilter);
    }
    const mult = sortDir === 'asc' ? 1 : -1;
    return [...list].sort((a, b) => {
      const av = a[sortBy] ?? -1;
      const bv = b[sortBy] ?? -1;
      if (av !== bv) return (av - bv) * mult;
      if (a.goals_plus_assists !== b.goals_plus_assists) return b.goals_plus_assists - a.goals_plus_assists;
      return b.minutes - a.minutes;
    });
  }, [rows, teamFilter, positionFilter, sortBy, sortDir]);

  const visibleRows = filteredAndSorted.slice(0, visibleLimit);

  const toggleSort = (key) => {
    if (sortBy === key) {
      setSortDir((prev) => (prev === 'desc' ? 'asc' : 'desc'));
    } else {
      setSortBy(key);
      setSortDir('desc');
    }
    setVisibleLimit(PAGE_SIZE);
  };

  if (loading) return <DiscoverySkeleton />;

  if (error) {
    return (
      <InlineError
        message="Oyuncu istatistik dizini yüklenemedi. Tekrar deneyin."
        onRetry={onRetry}
      />
    );
  }

  const columns = [
    { key: 'goals', label: 'Gol' },
    { key: 'assists', label: 'Asist' },
    { key: 'goals_plus_assists', label: 'G+A' },
    { key: 'avg_rating', label: 'Reyting' },
    { key: 'ga_per_90', label: 'G+A/90' },
    ...(hasXg ? [{ key: 'expected_goals', label: 'xG' }] : []),
    { key: 'appearances', label: 'Maç' },
    { key: 'minutes', label: 'Dk' },
    { key: 'market_value_eur', label: 'Değer' },
  ];

  return (
    <Card padding="none" className="overflow-hidden">
      <div className="flex flex-col gap-3 border-b border-border-light p-4 sm:flex-row sm:items-center sm:justify-between sm:px-5">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <Users className="h-4 w-4 text-text-secondary shrink-0" strokeWidth={1.5} aria-hidden="true" />
            <h2 className="text-base font-semibold text-text-primary">Lig liderleri</h2>
          </div>
          <p className="mt-0.5 text-xs text-text-secondary tabular-nums">
            {filteredAndSorted.length} oyuncu · Bir oyuncuya tıklayarak profilini ve form trendini açın
          </p>
        </div>

        <div className="grid grid-cols-1 gap-2 sm:flex sm:flex-wrap sm:items-center">
          <div className="w-full sm:w-36">
            <Select
              aria-label="Sezon seç"
              value={activeSeason}
              onChange={(e) => {
                onSeasonChange?.(e.target.value);
                setVisibleLimit(PAGE_SIZE);
              }}
              options={availableSeasons}
            />
          </div>
          <div className="w-full sm:w-44">
            <Select
              aria-label="Kulüp filtresi"
              value={teamFilter}
              onChange={(e) => {
                setTeamFilter(e.target.value);
                setVisibleLimit(PAGE_SIZE);
              }}
              options={[{ value: 'all', label: 'Tüm kulüpler' }, ...teamOptions]}
            />
          </div>
          <div className="w-full sm:w-36">
            <Select
              aria-label="Mevki filtresi"
              value={positionFilter}
              onChange={(e) => {
                setPositionFilter(e.target.value);
                setVisibleLimit(PAGE_SIZE);
              }}
              options={[
                { value: 'all', label: 'Tüm mevkiler' },
                { value: 'F', label: 'Forvet' },
                { value: 'M', label: 'Orta Saha' },
                { value: 'D', label: 'Defans' },
                { value: 'G', label: 'Kaleci' },
              ]}
            />
          </div>
        </div>
      </div>

      {filteredAndSorted.length === 0 ? (
        <EmptyState
          icon={SearchX}
          action={
            (teamFilter !== 'all' || positionFilter !== 'all') && (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  setTeamFilter('all');
                  setPositionFilter('all');
                }}
              >
                Filtreleri sıfırla
              </Button>
            )
          }
        >
          Seçili sezon ve filtrelere göre süre almış oyuncu bulunamadı.
        </EmptyState>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-border bg-background-tertiary text-xs text-text-secondary">
                  <th scope="col" className="py-2.5 pl-4 pr-2 font-medium w-10">#</th>
                  <th scope="col" className="py-2.5 px-3 font-medium">Oyuncu</th>
                  {columns.map((col) => {
                    const active = sortBy === col.key;
                    const Icon = !active ? ArrowUpDown : sortDir === 'asc' ? ArrowUp : ArrowDown;
                    return (
                      <th key={col.key} scope="col" className="py-2.5 px-3 font-medium text-right whitespace-nowrap">
                        <button
                          type="button"
                          onClick={() => toggleSort(col.key)}
                          className={`inline-flex items-center justify-end gap-1 cursor-pointer transition-colors hover:text-text-primary ${
                            active ? 'text-text-primary font-semibold' : 'text-text-secondary'
                          }`}
                        >
                          <span>{col.label}</span>
                          <Icon className="h-3 w-3 shrink-0" strokeWidth={1.75} aria-hidden="true" />
                        </button>
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody className="divide-y divide-border-light">
                {visibleRows.map((row, index) => {
                  const club = row.teamId ? getTeam(row.teamId, row.teamName) : null;
                  return (
                    <tr
                      key={row.id}
                      onClick={() => onSelectPlayer(row.id)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          onSelectPlayer(row.id);
                        }
                      }}
                      tabIndex={0}
                      className="cursor-pointer transition-colors hover:bg-background-secondary focus-visible:outline-none focus-visible:bg-background-secondary"
                    >
                      <td className="py-2.5 pl-4 pr-2 text-xs text-text-tertiary tabular-nums">
                        {index + 1}
                      </td>
                      <td className="py-2.5 px-3 min-w-52">
                        <div className="flex items-center gap-2.5">
                          <PlayerAvatar player={row} size="sm" shape="circle" className="w-8 h-8 shrink-0" />
                          <div className="min-w-0">
                            <p className="font-medium text-text-primary truncate max-w-48">{row.name}</p>
                            <div className="flex items-center gap-1.5 text-xs text-text-secondary truncate">
                              {club?.badge && (
                                <img
                                  src={club.badge}
                                  alt=""
                                  className="h-3.5 w-3.5 shrink-0 object-contain"
                                  onError={handleTeamBadgeError}
                                />
                              )}
                              <span className="truncate">{club?.short || row.teamName}</span>
                              <span aria-hidden="true">·</span>
                              <span className="text-text-tertiary">{row.posLabel}</span>
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className={`py-2.5 px-3 text-right tabular-nums ${sortBy === 'goals' ? 'font-semibold text-text-primary' : 'text-text-primary'}`}>
                        {row.goals}
                      </td>
                      <td className={`py-2.5 px-3 text-right tabular-nums ${sortBy === 'assists' ? 'font-semibold text-text-primary' : 'text-text-secondary'}`}>
                        {row.assists}
                      </td>
                      <td className={`py-2.5 px-3 text-right tabular-nums ${sortBy === 'goals_plus_assists' ? 'font-semibold text-text-primary' : 'text-text-primary'}`}>
                        {row.goals_plus_assists}
                      </td>
                      <td className={`py-2.5 px-3 text-right tabular-nums ${ratingTone(row.avg_rating)}`}>
                        {row.avg_rating != null ? row.avg_rating.toFixed(1) : '—'}
                      </td>
                      <td className="py-2.5 px-3 text-right tabular-nums text-text-secondary">
                        {row.ga_per_90.toFixed(2)}
                      </td>
                      {hasXg && (
                        <td className="py-2.5 px-3 text-right tabular-nums text-text-secondary">
                          {row.expected_goals != null ? row.expected_goals.toFixed(1) : '—'}
                        </td>
                      )}
                      <td className="py-2.5 px-3 text-right tabular-nums text-text-secondary">
                        {row.appearances}
                      </td>
                      <td className="py-2.5 px-3 text-right tabular-nums text-text-secondary">
                        {row.minutes.toLocaleString('tr-TR')}
                      </td>
                      <td className="py-2.5 px-3 text-right tabular-nums text-text-secondary whitespace-nowrap">
                        {formatMoneyShort(row.market_value_eur)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {visibleRows.length < filteredAndSorted.length && (
            <div className="flex items-center justify-between border-t border-border-light bg-background-secondary px-4 py-3 text-xs text-text-secondary">
              <span className="tabular-nums">
                {visibleRows.length} / {filteredAndSorted.length} oyuncu gösteriliyor
              </span>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setVisibleLimit((prev) => prev + PAGE_SIZE)}
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
