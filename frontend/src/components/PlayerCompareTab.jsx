import React, { useEffect, useMemo, useRef, useState } from 'react';
import { ArrowLeftRight, ArrowUpRight, Search, UserRound, X } from 'lucide-react';
import { useCompetition } from '../context/competitionState';
import { getTeam } from '../data/teams';
import { getPlayersCompareData } from '../services/playerService';
import { formatSeasonLabel } from '../utils/dateFormatters';
import { handleTeamBadgeError } from '../utils/imageFallbacks';
import { updateUrlRoute } from '../utils/router';
import PlayerAvatar from './PlayerAvatar';
import { Badge } from './common/Badge';
import { Button } from './common/Button';
import { Card } from './common/Card';
import EmptyState from './common/EmptyState';
import InlineError from './common/InlineError';
import { Select } from './common/Select';
import Skeleton from './common/Skeleton';

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

function foldText(s) {
  return String(s || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/ı/g, 'i')
    .replace(/İ/g, 'i')
    .toLowerCase()
    .trim();
}

const fmtInt = (v) => String(Math.round(v));
const fmtOne = (v) => Number(v).toFixed(1);
const fmtTwo = (v) => Number(v).toFixed(2);
const fmtPct = (v) => `${Number(v).toFixed(1)}%`;
const fmtMins = (v) => `${Math.round(v)} dk`;
const fmtMoney = (v) => (v >= 1000 ? `€${(v / 1000).toFixed(2)}B` : `€${Number(v).toFixed(1)}M`);

const ALL_METRICS = [
  { key: 'avg_rating', label: 'Ortalama Puan', category: 'impact', higherIsBetter: true, leadCounted: true, format: fmtOne },
  { key: 'goals', label: 'Gol', category: 'attack', higherIsBetter: true, leadCounted: true, format: fmtInt },
  { key: 'assists', label: 'Asist', category: 'attack', higherIsBetter: true, leadCounted: true, format: fmtInt },
  { key: 'goals_plus_assists', label: 'Gol + Asist', category: 'attack', higherIsBetter: true, leadCounted: true, format: fmtInt },
  { key: 'goals_per_90', label: 'Gol / 90 Dk', mobileLabel: 'Gol / 90', category: 'attack', higherIsBetter: true, leadCounted: true, format: fmtTwo },
  { key: 'assists_per_90', label: 'Asist / 90 Dk', mobileLabel: 'Asist / 90', category: 'attack', higherIsBetter: true, leadCounted: true, format: fmtTwo },
  { key: 'ga_per_90', label: 'G+A / 90 Dk', mobileLabel: 'G+A / 90', category: 'attack', higherIsBetter: true, leadCounted: true, format: fmtTwo },
  { key: 'expected_goals', label: 'Beklenen Gol (xG)', mobileLabel: 'xG', category: 'attack', higherIsBetter: true, leadCounted: true, format: fmtTwo },
  { key: 'expected_assists', label: 'Beklenen Asist (xA)', mobileLabel: 'xA', category: 'attack', higherIsBetter: true, leadCounted: true, format: fmtTwo },
  { key: 'shots', label: 'Toplam Şut', category: 'attack', higherIsBetter: true, leadCounted: false, format: fmtInt },
  { key: 'shots_ontarget', label: 'İsabetli Şut', category: 'attack', higherIsBetter: true, leadCounted: true, format: fmtInt },
  { key: 'key_passes', label: 'Kilit Pas', category: 'attack', higherIsBetter: true, leadCounted: true, format: fmtInt },
  { key: 'clean_sheets', label: 'Gol Yemeden', category: 'defense', higherIsBetter: true, leadCounted: true, format: fmtInt },
  { key: 'saves', label: 'Kurtarış', category: 'defense', higherIsBetter: true, leadCounted: true, format: fmtInt },
  { key: 'tackles', label: 'Top Çalma', category: 'defense', higherIsBetter: true, leadCounted: true, format: fmtInt },
  { key: 'interceptions', label: 'Pas Arası', category: 'defense', higherIsBetter: true, leadCounted: true, format: fmtInt },
  { key: 'win_pct', label: 'Galibiyet %', category: 'impact', higherIsBetter: true, leadCounted: true, format: fmtPct },
  { key: 'yellow_cards', label: 'Sarı Kart', category: 'defense', higherIsBetter: false, leadCounted: true, format: fmtInt },
  { key: 'red_cards', label: 'Kırmızı Kart', category: 'defense', higherIsBetter: false, leadCounted: true, format: fmtInt },
  { key: 'cards_per_90', label: 'Kart / 90 Dk', mobileLabel: 'Kart / 90', category: 'defense', higherIsBetter: false, leadCounted: false, format: fmtTwo },
  { key: 'appearances', label: 'Oynadığı Maç', category: 'impact', informational: true, higherIsBetter: true, leadCounted: false, format: fmtInt },
  { key: 'starts', label: 'İlk 11', category: 'impact', informational: true, higherIsBetter: true, leadCounted: false, format: fmtInt },
  { key: 'minutes', label: 'Toplam Süre', category: 'impact', informational: true, higherIsBetter: true, leadCounted: false, format: fmtMins },
  { key: 'minutes_per_match', label: 'Maç Başı Dakika', mobileLabel: 'Dk / Maç', category: 'impact', informational: true, higherIsBetter: true, leadCounted: false, format: fmtOne },
  { key: 'market_value_eur', label: 'Piyasa Değeri', category: 'impact', informational: true, higherIsBetter: true, leadCounted: false, format: fmtMoney },
];

const CATEGORIES = [
  { id: 'all', label: 'Tümü' },
  { id: 'attack', label: 'Hücum & Üretim' },
  { id: 'impact', label: 'Puan & Katılım' },
  { id: 'defense', label: 'Savunma & Disiplin' },
];

function pickLeader(metric, a, b) {
  if (metric.informational || a == null || b == null || a === b) return null;
  const firstWins = metric.higherIsBetter ? a > b : a < b;
  return firstWins ? 1 : 2;
}

function PlayerCompareCard({
  slot,
  player,
  avgs,
  season,
  averagesMap,
  profiles,
  excludeId,
  onPick,
  onOpenProfile,
  isLeadingOverall,
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const wrapRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const onOutside = (e) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    const onEsc = (e) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onOutside);
    document.addEventListener('keydown', onEsc);
    return () => {
      document.removeEventListener('mousedown', onOutside);
      document.removeEventListener('keydown', onEsc);
    };
  }, [open]);

  const candidates = useMemo(() => {
    const q = foldText(query);
    const terms = q.split(/\s+/).filter(Boolean);
    const matches = [];
    for (const p of profiles) {
      if (String(p.id) === String(excludeId)) continue;
      if (terms.length > 0) {
        const haystack = foldText(`${p.name} ${p.teamName || ''}`);
        if (!terms.every((t) => haystack.includes(t))) continue;
      }
      matches.push(p);
    }

    matches.sort((a, b) => {
      const aActive = averagesMap[String(a.id)]?.[season] ? 0 : 1;
      const bActive = averagesMap[String(b.id)]?.[season] ? 0 : 1;
      if (aActive !== bActive) return aActive - bActive;
      if (q) {
        const aStarts = foldText(a.name).startsWith(q) ? 0 : 1;
        const bStarts = foldText(b.name).startsWith(q) ? 0 : 1;
        if (aStarts !== bStarts) return aStarts - bStarts;
      }
      const aGa = averagesMap[String(a.id)]?.[season]?.goals_plus_assists ?? 0;
      const bGa = averagesMap[String(b.id)]?.[season]?.goals_plus_assists ?? 0;
      if (aGa !== bGa) return bGa - aGa;
      return String(a.name || '').localeCompare(String(b.name || ''));
    });
    return matches.slice(0, 60);
  }, [profiles, excludeId, query, season, averagesMap]);

  const openPicker = () => {
    setOpen(true);
    setQuery('');
    window.setTimeout(() => inputRef.current?.focus(), 20);
  };

  const teamId = avgs?.teams?.length ? avgs.teams[avgs.teams.length - 1] : player?.teamId;
  const teamName = avgs?.team_names?.length ? avgs.team_names[avgs.team_names.length - 1] : player?.teamName;
  const team = teamId ? getTeam(teamId, teamName || 'Kulüp') : null;
  const posLabel = POSITION_LABELS[player?.position] || player?.position || '';

  return (
    <Card ref={wrapRef} padding="sm" className="relative flex flex-col justify-between gap-2.5">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-3 min-w-0">
          {player ? (
            <PlayerAvatar player={player} size="lg" shape="circle" className="shrink-0" />
          ) : (
            <div className="w-14 h-14 rounded-full bg-background-tertiary border border-border flex items-center justify-center shrink-0">
              <UserRound className="w-6 h-6 text-text-muted" strokeWidth={1.5} aria-hidden="true" />
            </div>
          )}

          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-xs font-medium text-text-muted">{slot}</span>
              {isLeadingOverall && <Badge variant="primary" size="sm">Önde</Badge>}
            </div>

            {player ? (
              <>
                <p className="text-base font-semibold text-text-primary truncate">{player.name}</p>
                <div className="mt-0.5 flex flex-wrap items-center gap-1.5 text-xs text-text-secondary">
                  {team && (
                    <span className="inline-flex items-center gap-1 min-w-0">
                      <img
                        src={team.badge}
                        alt=""
                        className="w-4 h-4 object-contain shrink-0"
                        onError={handleTeamBadgeError}
                      />
                      <span className="truncate">{team.short || team.name}</span>
                    </span>
                  )}
                  {posLabel && (
                    <>
                      <span aria-hidden="true">·</span>
                      <span>{posLabel}</span>
                    </>
                  )}
                  {player.shirt ? (
                    <>
                      <span aria-hidden="true">·</span>
                      <span className="tabular-nums">#{player.shirt}</span>
                    </>
                  ) : null}
                </div>
              </>
            ) : (
              <p className="text-sm text-text-secondary">Oyuncu seçin</p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-1 shrink-0">
          {player && onOpenProfile && (
            <button
              type="button"
              onClick={() => onOpenProfile(player.id)}
              title={`${player.name} profilini aç`}
              aria-label={`${player.name} profilini aç`}
              className="inline-flex h-8 w-8 items-center justify-center rounded border border-border bg-background-primary text-text-secondary hover:bg-background-tertiary hover:text-text-primary transition-colors cursor-pointer"
            >
              <ArrowUpRight className="w-4 h-4" strokeWidth={1.5} aria-hidden="true" />
            </button>
          )}
        </div>
      </div>

      <div className="flex items-center justify-between gap-2 pt-2 border-t border-border-light">
        <div className="text-xs text-text-secondary tabular-nums truncate">
          {avgs ? (
            <span>
              {avgs.appearances} maç · {avgs.goals} gol · {avgs.assists} asist
            </span>
          ) : (
            <span className="text-text-muted">Seçili sezonda maç yok</span>
          )}
        </div>
        <button
          type="button"
          onClick={() => (open ? setOpen(false) : openPicker())}
          className="inline-flex items-center gap-1.5 rounded border border-border bg-background-tertiary hover:bg-background-secondary px-2.5 py-1 text-xs font-medium text-text-primary transition-colors cursor-pointer shrink-0"
        >
          <Search className="w-3.5 h-3.5 text-text-secondary" strokeWidth={1.5} aria-hidden="true" />
          <span>Değiştir</span>
        </button>
      </div>

      {open && (
        <div className="absolute left-0 right-0 top-full mt-1.5 z-30 rounded border border-border bg-background-primary shadow-md overflow-hidden">
          <div className="flex items-center gap-2 border-b border-border px-3 py-2">
            <Search className="w-4 h-4 text-text-muted shrink-0" strokeWidth={1.5} aria-hidden="true" />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Oyuncu veya kulüp ara..."
              className="flex-1 bg-transparent text-xs sm:text-sm text-text-primary placeholder:text-text-muted outline-none"
            />
            {query && (
              <button
                type="button"
                onClick={() => {
                  setQuery('');
                  inputRef.current?.focus();
                }}
                className="p-0.5 text-text-muted hover:text-text-primary cursor-pointer"
                aria-label="Aramayı temizle"
              >
                <X className="w-3.5 h-3.5" strokeWidth={1.5} aria-hidden="true" />
              </button>
            )}
          </div>
          <ul className="max-h-72 overflow-y-auto p-1.5 space-y-0.5">
            {candidates.length === 0 ? (
              <li className="py-6 text-center text-xs text-text-secondary">Eşleşen oyuncu yok.</li>
            ) : (
              candidates.map((candidate) => {
                const cAvg = averagesMap[String(candidate.id)]?.[season];
                const cTeamId = cAvg?.teams?.length ? cAvg.teams[cAvg.teams.length - 1] : candidate.teamId;
                const cTeam = cTeamId ? getTeam(cTeamId, candidate.teamName || '') : null;
                const cPos = POSITION_LABELS[candidate.position] || candidate.position;
                const subParts = [
                  cPos,
                  cAvg ? `${cAvg.goals}G ${cAvg.assists}A` : null,
                  cAvg?.avg_rating != null ? `${cAvg.avg_rating.toFixed(1)} puan` : null,
                ].filter(Boolean);

                return (
                  <li key={candidate.id}>
                    <button
                      type="button"
                      onClick={() => {
                        onPick(candidate.id);
                        setOpen(false);
                      }}
                      className="flex w-full items-center justify-between gap-2.5 rounded-sm px-2.5 py-2 text-left text-sm hover:bg-background-tertiary transition-colors cursor-pointer"
                    >
                      <div className="flex items-center gap-2.5 min-w-0">
                        <PlayerAvatar player={candidate} size="sm" shape="circle" className="w-7 h-7" />
                        <div className="min-w-0">
                          <p className="font-medium text-text-primary truncate">{candidate.name}</p>
                          {subParts.length > 0 && (
                            <p className="text-xs text-text-secondary tabular-nums truncate">
                              {subParts.join(' · ')}
                            </p>
                          )}
                        </div>
                      </div>
                      {cTeam && (
                        <span className="inline-flex items-center gap-1.5 text-xs text-text-secondary shrink-0">
                          <img
                            src={cTeam.badge}
                            alt=""
                            className="w-4 h-4 object-contain"
                            onError={handleTeamBadgeError}
                          />
                          <span className="hidden sm:inline">{cTeam.short || cTeam.name}</span>
                        </span>
                      )}
                    </button>
                  </li>
                );
              })
            )}
          </ul>
        </div>
      )}
    </Card>
  );
}

function CompareRow({ metric, s1, s2, lead }) {
  const v1 = s1?.[metric.key] ?? null;
  const v2 = s2?.[metric.key] ?? null;
  const showBars =
    !metric.informational &&
    v1 != null &&
    v2 != null &&
    v1 >= 0 &&
    v2 >= 0 &&
    Math.max(v1, v2) > 0;
  const max = showBars ? Math.max(v1, v2) : 1;

  const valClass = (side, val) => {
    if (val == null) return 'text-text-muted';
    if (lead === side) return 'font-semibold text-accent';
    if (metric.informational) return 'font-medium text-text-primary';
    return 'font-medium text-text-secondary';
  };

  return (
    <div className="grid grid-cols-compare-row items-center gap-2 sm:gap-3 px-3.5 py-2.5 transition-colors hover:bg-background-tertiary/50">
      <div className="flex items-center justify-end gap-2.5 min-w-0">
        {showBars && v1 != null && (
          <div className="hidden h-1.5 w-16 overflow-hidden rounded-full bg-background-tertiary sm:flex sm:justify-end md:w-28 lg:w-36">
            <div
              className={`h-full rounded-full ${lead === 1 ? 'bg-accent' : 'bg-border'}`}
              style={{ width: `${v1 > 0 ? Math.max(6, Math.min(100, Math.round((v1 / max) * 100))) : 0}%` }}
            />
          </div>
        )}
        <div className="text-right tabular-nums">
          <span className={`text-sm ${valClass(1, v1)}`}>{v1 == null ? '—' : metric.format(v1)}</span>
        </div>
      </div>

      <div
        className="text-center"
        title={!metric.higherIsBetter && !metric.informational ? 'Düşük değer daha olumludur' : undefined}
      >
        <span className="inline-block rounded-sm bg-background-tertiary px-2 py-0.5 text-xs font-medium text-text-secondary">
          <span className={metric.mobileLabel ? 'hidden sm:inline' : undefined}>{metric.label}</span>
          {metric.mobileLabel && <span className="sm:hidden">{metric.mobileLabel}</span>}
        </span>
      </div>

      <div className="flex items-center justify-start gap-2.5 min-w-0">
        <div className="text-left tabular-nums">
          <span className={`text-sm ${valClass(2, v2)}`}>{v2 == null ? '—' : metric.format(v2)}</span>
        </div>
        {showBars && v2 != null && (
          <div className="hidden h-1.5 w-16 overflow-hidden rounded-full bg-background-tertiary sm:flex md:w-28 lg:w-36">
            <div
              className={`h-full rounded-full ${lead === 2 ? 'bg-accent' : 'bg-border'}`}
              style={{ width: `${v2 > 0 ? Math.max(6, Math.min(100, Math.round((v2 / max) * 100))) : 0}%` }}
            />
          </div>
        )}
      </div>
    </div>
  );
}

export default function PlayerCompareTab({
  selectedSeason,
  setSelectedSeason,
  initialP1Id = null,
  initialP2Id = null,
  onSelectPlayerProfile,
}) {
  const { activeCompetition, competitionKey } = useCompetition();
  const [payloadState, setPayloadState] = useState({ competition: '', data: null, error: null });
  const [reloadSeq, setReloadSeq] = useState(0);
  const [category, setCategory] = useState('all');
  const [pickedIds, setPickedIds] = useState({
    competition: competitionKey,
    p1: initialP1Id ? String(initialP1Id) : null,
    p2: initialP2Id ? String(initialP2Id) : null,
  });

  useEffect(() => {
    let active = true;
    getPlayersCompareData(competitionKey)
      .then((data) => {
        if (active) setPayloadState({ competition: competitionKey, data, error: null });
      })
      .catch((err) => {
        if (active) {
          setPayloadState({
            competition: competitionKey,
            data: null,
            error: err?.message || 'Oyuncu karşılaştırma verileri yüklenemedi.',
          });
        }
      });
    return () => {
      active = false;
    };
  }, [competitionKey, reloadSeq]);

  const loading = payloadState.competition !== competitionKey && !payloadState.error;
  const loadError = payloadState.competition === competitionKey ? payloadState.error : null;
  const data = payloadState.competition === competitionKey ? payloadState.data : null;

  const seasonsList = useMemo(
    () => (data?.seasons?.length ? data.seasons : [activeCompetition.default_season, 'all']),
    [data, activeCompetition.default_season],
  );

  const activeSeason = useMemo(() => {
    if (selectedSeason && seasonsList.includes(selectedSeason)) return selectedSeason;
    return seasonsList[0] || activeCompetition.default_season;
  }, [selectedSeason, seasonsList, activeCompetition.default_season]);

  const resolvedIds = useMemo(() => {
    const profiles = data?.profiles || [];
    if (profiles.length === 0) return { p1: null, p2: null };

    const validIds = new Set(profiles.map((p) => String(p.id)));
    const byComp = pickedIds.competition === competitionKey;
    let p1 = byComp && pickedIds.p1 && validIds.has(String(pickedIds.p1))
      ? String(pickedIds.p1)
      : (initialP1Id && validIds.has(String(initialP1Id)) ? String(initialP1Id) : String(profiles[0].id));

    let p2 = byComp && pickedIds.p2 && validIds.has(String(pickedIds.p2)) && String(pickedIds.p2) !== p1
      ? String(pickedIds.p2)
      : (initialP2Id && validIds.has(String(initialP2Id)) && String(initialP2Id) !== p1
        ? String(initialP2Id)
        : null);

    if (!p2) {
      const p1Team = profiles.find((p) => String(p.id) === p1)?.teamId;
      const diffClub = profiles.find((p) => String(p.id) !== p1 && (!p1Team || p.teamId !== p1Team));
      const fallback = diffClub || profiles.find((p) => String(p.id) !== p1);
      p2 = fallback ? String(fallback.id) : p1;
    }

    return { p1, p2 };
  }, [data?.profiles, pickedIds, competitionKey, initialP1Id, initialP2Id]);

  useEffect(() => {
    if (resolvedIds.p1 || resolvedIds.p2) {
      updateUrlRoute(
        { tab: 'player-compare', compareP1: resolvedIds.p1, compareP2: resolvedIds.p2 },
        true,
      );
    }
  }, [resolvedIds.p1, resolvedIds.p2]);

  const profileById = useMemo(() => {
    const map = new Map();
    (data?.profiles || []).forEach((p) => map.set(String(p.id), p));
    return map;
  }, [data?.profiles]);

  const player1 = resolvedIds.p1 ? profileById.get(resolvedIds.p1) : undefined;
  const player2 = resolvedIds.p2 ? profileById.get(resolvedIds.p2) : undefined;
  const stats1 = resolvedIds.p1 ? (data?.averages?.[resolvedIds.p1]?.[activeSeason] || null) : null;
  const stats2 = resolvedIds.p2 ? (data?.averages?.[resolvedIds.p2]?.[activeSeason] || null) : null;

  const { leads1, leads2 } = useMemo(() => {
    let l1 = 0;
    let l2 = 0;
    for (const metric of ALL_METRICS) {
      if (!metric.leadCounted) continue;
      const win = pickLeader(metric, stats1?.[metric.key], stats2?.[metric.key]);
      if (win === 1) l1 += 1;
      if (win === 2) l2 += 1;
    }
    return { leads1: l1, leads2: l2 };
  }, [stats1, stats2]);

  const visibleMetrics = useMemo(() => {
    return ALL_METRICS.filter((metric) => {
      if (category !== 'all' && metric.category !== category) return false;
      const v1 = stats1?.[metric.key];
      const v2 = stats2?.[metric.key];
      if (v1 == null && v2 == null) return false;
      if (metric.key === 'saves' && (v1 || 0) === 0 && (v2 || 0) === 0) return false;
      return true;
    });
  }, [category, stats1, stats2]);

  const handleSwap = () => {
    if (!resolvedIds.p1 || !resolvedIds.p2) return;
    setPickedIds({ competition: competitionKey, p1: resolvedIds.p2, p2: resolvedIds.p1 });
  };

  if (loading) {
    return (
      <div className="space-y-4" aria-busy="true" aria-label="Oyuncu karşılaştırma yükleniyor">
        <div className="grid grid-cols-versus items-center gap-3">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-9 w-20" />
          <Skeleton className="h-32 w-full" />
        </div>
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (loadError) {
    return <InlineError message={loadError} onRetry={() => setReloadSeq((s) => s + 1)} />;
  }

  if (!data?.profiles?.length) {
    return (
      <EmptyState icon={UserRound}>
        {activeCompetition.name} için henüz oyuncu karşılaştırma verisi bulunmuyor.
      </EmptyState>
    );
  }

  return (
    <div className="space-y-5 animate-fadeIn">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-text-primary tracking-tight">Oyuncu Karşılaştırma</h2>
          <p className="text-xs text-text-secondary">
            {activeCompetition.name} · İstatistik, verimlilik ve sezon liderliği kıyaslaması
          </p>
        </div>

        <div className="flex items-center gap-2.5 self-start sm:self-auto">
          <div className="w-40">
            <Select
              aria-label="Sezon seçin"
              value={activeSeason}
              onChange={(e) => setSelectedSeason?.(e.target.value)}
              options={seasonsList.map((s) => ({
                value: s,
                label: s === 'all' ? 'Tüm sezonlar' : formatSeasonLabel(s),
              }))}
            />
          </div>
          <Button
            variant="secondary"
            size="md"
            leftIcon={<ArrowLeftRight className="w-4 h-4" strokeWidth={1.5} />}
            onClick={handleSwap}
            title="Oyuncuların yerini değiştir"
          >
            Değiştir
          </Button>
        </div>
      </div>

      {/* Dual Player Selector Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <PlayerCompareCard
          slot="1. Oyuncu"
          player={player1}
          avgs={stats1}
          season={activeSeason}
          averagesMap={data.averages}
          profiles={data.profiles}
          excludeId={resolvedIds.p2}
          onPick={(id) => setPickedIds({ competition: competitionKey, p1: String(id), p2: resolvedIds.p2 })}
          onOpenProfile={onSelectPlayerProfile}
          isLeadingOverall={leads1 > leads2}
        />

        <PlayerCompareCard
          slot="2. Oyuncu"
          player={player2}
          avgs={stats2}
          season={activeSeason}
          averagesMap={data.averages}
          profiles={data.profiles}
          excludeId={resolvedIds.p1}
          onPick={(id) => setPickedIds({ competition: competitionKey, p1: resolvedIds.p1, p2: String(id) })}
          onOpenProfile={onSelectPlayerProfile}
          isLeadingOverall={leads2 > leads1}
        />
      </div>

      {/* Category Filter + Lead Score Counter */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div role="tablist" aria-label="İstatistik kategorileri" className="inline-flex flex-wrap gap-1 p-1 rounded border border-border bg-background-primary">
          {CATEGORIES.map((cat) => {
            const active = category === cat.id;
            return (
              <button
                key={cat.id}
                type="button"
                role="tab"
                aria-selected={active}
                onClick={() => setCategory(cat.id)}
                className={`px-3 py-1.5 rounded-sm text-xs font-medium transition-colors cursor-pointer ${
                  active
                    ? 'bg-accent text-white'
                    : 'text-text-secondary hover:text-text-primary hover:bg-background-tertiary'
                }`}
              >
                {cat.label}
              </button>
            );
          })}
        </div>

        <div className="inline-flex items-center gap-3 self-start sm:self-auto rounded border border-border bg-background-primary px-3.5 py-2 text-xs tabular-nums">
          <span className="font-medium text-text-secondary truncate max-w-28">{player1?.name}</span>
          <span className="rounded-sm bg-background-tertiary px-2 py-0.5 font-semibold text-text-primary">
            {leads1} - {leads2}
          </span>
          <span className="font-medium text-text-secondary truncate max-w-28">{player2?.name}</span>
        </div>
      </div>

      {/* Centered Comparison Table */}
      <Card padding="none" className="overflow-hidden">
        {visibleMetrics.length === 0 ? (
          <div className="py-12 text-center text-sm text-text-secondary">
            Seçili kategoride veya sezonda her iki oyuncu için ortak istatistik bulunamadı.
          </div>
        ) : (
          <div className="divide-y divide-border-light">
            {visibleMetrics.map((metric) => (
              <CompareRow
                key={metric.key}
                metric={metric}
                s1={stats1}
                s2={stats2}
                lead={pickLeader(metric, stats1?.[metric.key], stats2?.[metric.key])}
              />
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
