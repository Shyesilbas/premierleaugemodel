import { handleTeamBadgeError } from '../utils/imageFallbacks';
import { formatSeasonLabel } from '../utils/dateFormatters';
import React, { useState, useEffect, useMemo } from 'react';
import { 
  Search, 
  Scale, 
  ChevronRight, 
  X, 
  Calendar, 
  Flame, 
  ArrowUpDown,
  Trophy
} from 'lucide-react';
import { getTeam } from '../data/teams';
import MatchDetailModal from './MatchDetailModal';
import { getRefereeDetails, getReferees } from '../services/refereeService';
import { useCompetition } from '../context/CompetitionContext';
import CompetitionBadge from './team-profile/CompetitionBadge';
import { COMPETITIONS } from './team-profile/teamProfileUtils';

export default function RefereesTab({ selectedSeason, onSelectMatch }) {
  const { competitionKey, activeCompetition } = useCompetition();
  const [referees, setReferees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState('matches');
  const [activeSeason, setActiveSeason] = useState(selectedSeason || '2026_27');
  const [selectedReferee, setSelectedReferee] = useState(null);
  const [refereeDetail, setRefereeDetail] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [activeModalMatch, setActiveModalMatch] = useState(null);

  // Sync with prop when changed
  useEffect(() => {
    if (selectedSeason) {
      setActiveSeason(selectedSeason);
    }
  }, [selectedSeason]);

  useEffect(() => {
    setSelectedReferee(null);
    setRefereeDetail(null);
  }, [competitionKey]);

  // Fetch Referees list
  useEffect(() => {
    setLoading(true);
    getReferees(activeSeason, competitionKey)
      .then(data => {
        setReferees(data?.referees || []);
        setLoading(false);
      })
      .catch(err => {
        console.error('Error fetching referees:', err);
        setLoading(false);
      });
  }, [activeSeason, competitionKey]);

  // Fetch Referee Detail when a referee is clicked
  const handleOpenDetail = (refName) => {
    setSelectedReferee(refName);
    setRefereeDetail(null);
    setLoadingDetail(true);
    getRefereeDetails(refName, activeSeason, competitionKey)
      .then(data => {
        setRefereeDetail(data);
        setLoadingDetail(false);
      })
      .catch(err => {
        console.error('Error fetching referee detail:', err);
        setLoadingDetail(false);
      });
  };

  // Filtered referees by search term
  const filteredReferees = useMemo(() => {
    if (!search.trim()) return referees;
    const q = search.toLowerCase();
    return referees.filter(r => (r.referee_name || '').toLowerCase().includes(q));
  }, [referees, search]);

  const sortedReferees = useMemo(() => [...filteredReferees].sort((a, b) => {
    if (sortBy === 'cards') return (b.avg_cards || 0) - (a.avg_cards || 0);
    if (sortBy === 'fouls') return (b.avg_fouls || 0) - (a.avg_fouls || 0);
    return (b.matches_count || 0) - (a.matches_count || 0);
  }), [filteredReferees, sortBy]);

  // Aggregate summary
  const summaryStats = useMemo(() => {
    if (!referees.length) return null;
    const totalMatches = referees.reduce((acc, r) => acc + (r.matches_count || 0), 0);
    const totalCards = referees.reduce((acc, r) => acc + (r.total_cards || 0), 0);
    const totalFouls = referees.reduce((acc, r) => acc + (r.total_fouls || 0), 0);
    const avgCards = totalMatches > 0 ? (totalCards / totalMatches).toFixed(2) : '4.15';
    const avgFouls = totalMatches > 0 ? (totalFouls / totalMatches).toFixed(1) : '21.5';
    const topStrict = [...referees].sort((a, b) => (b.avg_cards || 0) - (a.avg_cards || 0))[0];

    return {
      count: referees.length,
      totalMatches,
      avgCards,
      avgFouls,
      topStrict
    };
  }, [referees]);

  // Strictness status renderer (using 6px status dot + text rule)
  const renderStrictnessBadge = (label) => {
    if (label === 'Yüksek Kart Eğilimi') {
      return (
        <span className="inline-flex items-center gap-1.5 text-xs font-medium text-status-error">
          <span className="w-1.5 h-1.5 rounded-full bg-status-error" />
          Yüksek Kart Eğilimi
        </span>
      );
    }
    if (label === 'Akıcı Oyun / Az Kart') {
      return (
        <span className="inline-flex items-center gap-1.5 text-xs font-medium text-status-success">
          <span className="w-1.5 h-1.5 rounded-full bg-status-success" />
          Akıcı Oyun / Az Kart
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 text-xs font-medium text-status-warning">
        <span className="w-1.5 h-1.5 rounded-full bg-status-warning" />
        Dengeli Yönetim
      </span>
    );
  };

  return (
    <div className="space-y-6">
      
      {/* Top Header Section */}
      <div className="rounded border border-border bg-background-primary">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-5 sm:p-6">
          <div>
            <div className="flex items-center gap-2 mb-1.5 text-text-secondary">
              <Scale className="w-4 h-4 text-text-tertiary" />
              <span className="text-xs font-medium">{activeCompetition.name} · Hakem Merkezi</span>
            </div>
            <h1 className="text-2xl font-semibold tracking-tight text-text-primary">Hakem Profilleri</h1>
            <p className="max-w-2xl mt-1 text-sm text-text-secondary">
              Sezon performansını karşılaştırın, maç yönetim kayıtlarına göz atın.
            </p>
          </div>

          {/* Season Selector */}
          <div className="flex items-center gap-2">
            <label htmlFor="referee-season-select" className="text-xs font-medium text-text-secondary">
              Sezon:
            </label>
            <select
              id="referee-season-select"
              value={activeSeason}
              onChange={(e) => setActiveSeason(e.target.value)}
              className="h-9 min-w-44 bg-background-primary border border-border text-sm font-medium text-text-primary rounded px-3 outline-none focus:border-border-focus transition-colors"
            >
              <option value="2026_27">2026-27 (Güncel Sezon)</option>
              <option value="2025_26">2025-26 Sezonu</option>
              <option value="2024_25">2024-25 Sezonu</option>
              <option value="2023_24">2023-24 Sezonu</option>
              <option value="2022_23">2022-23 Sezonu</option>
              <option value="all">Tüm Sezonlar (Kariyer)</option>
            </select>
          </div>
        </div>

        {/* Global Summary Metrics */}
        {summaryStats && (
          <div className="grid grid-cols-2 lg:grid-cols-4 border-t border-border-light divide-y sm:divide-y-0 divide-x divide-border-light">
            <div className="p-4 sm:p-5">
              <span className="text-xs font-medium text-text-secondary block">Listelenen Hakem</span>
              <span className="mt-1 block text-xl font-semibold tabular-nums text-text-primary">{summaryStats.count}</span>
            </div>
            <div className="p-4 sm:p-5">
              <span className="text-xs font-medium text-text-secondary block">Lig Kart Ortalaması</span>
              <span className="mt-1 block text-xl font-semibold tabular-nums text-text-primary">
                {summaryStats.avgCards}
                <span className="ml-1 text-xs font-normal text-text-secondary">/ maç</span>
              </span>
            </div>
            <div className="p-4 sm:p-5">
              <span className="text-xs font-medium text-text-secondary block">Lig Faul Ortalaması</span>
              <span className="mt-1 block text-xl font-semibold tabular-nums text-text-primary">
                {summaryStats.avgFouls}
                <span className="ml-1 text-xs font-normal text-text-secondary">/ maç</span>
              </span>
            </div>
            <div className="p-4 sm:p-5 min-w-0">
              <span className="text-xs font-medium text-text-secondary block">En Yüksek Kart Ortalaması</span>
              <span className="mt-1 block truncate text-base font-semibold text-text-primary" title={summaryStats.topStrict?.referee_name}>
                {summaryStats.topStrict?.referee_name || '—'}
                <span className="tabular-nums text-xs font-normal text-text-secondary ml-1">({summaryStats.topStrict?.avg_cards} / maç)</span>
              </span>
            </div>
          </div>
        )}
      </div>

      <section className="rounded border border-border bg-background-primary">
        <div className="flex flex-col gap-3 border-b border-border-light p-4 sm:flex-row sm:items-center sm:justify-between sm:px-5">
          <div>
            <h2 className="text-base font-semibold text-text-primary">Hakem Listesi</h2>
            <p className="mt-0.5 text-xs text-text-secondary">
              {loading ? 'Hakem verileri yükleniyor...' : `${sortedReferees.length} hakem · ${activeSeason === 'all' ? 'Kariyer istatistikleri' : `${formatSeasonLabel(activeSeason)} sezonu`}`}
            </p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <div className="relative sm:w-64">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-tertiary pointer-events-none" />
              <input
                type="search"
                placeholder="Hakem ara..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full h-9 rounded border border-border bg-background-primary py-2 pl-9 pr-3 text-sm text-text-primary placeholder:text-text-muted outline-none focus:border-border-focus transition-colors"
              />
            </div>
            <div className="flex items-center gap-1.5">
              <label htmlFor="referee-sort-select" className="text-xs font-medium text-text-secondary shrink-0">
                Sırala:
              </label>
              <div className="relative flex items-center">
                <select
                  id="referee-sort-select"
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  className="h-9 rounded border border-border bg-background-primary pl-3 pr-8 text-sm font-medium text-text-primary outline-none focus:border-border-focus transition-colors"
                >
                  <option value="matches">Maç sayısı</option>
                  <option value="cards">Kart ortalaması</option>
                  <option value="fouls">Faul ortalaması</option>
                </select>
                <ArrowUpDown className="pointer-events-none absolute right-2.5 h-3.5 w-3.5 text-text-tertiary" />
              </div>
            </div>
          </div>
        </div>

        {loading ? (
          <div className="py-16 text-center space-y-2">
            <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-xs font-medium text-text-secondary">Hakem verileri yükleniyor...</p>
          </div>
        ) : sortedReferees.length === 0 ? (
          <div className="p-12 text-center">
            <Scale className="mx-auto mb-2 h-6 w-6 text-text-tertiary" />
            <p className="text-sm font-medium text-text-primary">Hakem bulunamadı</p>
            <p className="mt-1 text-xs text-text-secondary">Arama terimini değiştirip tekrar deneyin.</p>
          </div>
        ) : (
          <>
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full min-w-max border-collapse text-left text-xs">
                <thead>
                  <tr className="bg-background-tertiary text-xs font-medium text-text-secondary border-b border-border">
                    <th className="px-5 py-2.5">Hakem</th>
                    <th className="px-4 py-2.5 text-right">Maç</th>
                    <th className="px-4 py-2.5 text-right">Kart / Maç</th>
                    <th className="px-4 py-2.5 text-right">Faul / Maç</th>
                    <th className="px-4 py-2.5 text-right">Kırmızı</th>
                    <th className="px-4 py-2.5">4+ Kart Oranı</th>
                    <th className="px-5 py-2.5 text-right">Detay</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-light bg-background-primary">
                  {sortedReferees.map((ref) => {
                    const initials = (ref.referee_name || '?').split(' ').map((part) => part[0]).join('').slice(0, 2);
                    const overRate = Math.min(100, Number(ref.over_3_5_pct) || 0);
                    return (
                      <tr key={ref.id || ref.referee_name} className="transition-colors hover:bg-background-secondary">
                        <td className="px-5 py-3">
                          <div className="flex items-center gap-3">
                            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-background-tertiary border border-border text-xs font-semibold text-text-primary">
                              {initials}
                            </span>
                            <div className="min-w-0">
                              <span className="block truncate text-sm font-medium text-text-primary">{ref.referee_name}</span>
                              <div className="mt-0.5">{ref.is_career_fallback ? <span className="text-xs text-text-muted">Bu sezon atama yok</span> : renderStrictnessBadge(ref.strictness_label)}</div>
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-right text-xs font-medium tabular-nums text-text-primary">{ref.matches_count ?? 0}</td>
                        <td className="px-4 py-3 text-right text-xs font-semibold tabular-nums text-text-primary">{ref.avg_cards ?? '—'}</td>
                        <td className="px-4 py-3 text-right text-xs tabular-nums text-text-secondary">{ref.avg_fouls ?? '—'}</td>
                        <td className="px-4 py-3 text-right text-xs tabular-nums text-text-secondary">{ref.total_red_cards || 0}</td>
                        <td className="px-4 py-3">
                          <div className="flex w-36 items-center gap-2">
                            <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-background-tertiary">
                              <div className="h-full rounded-full bg-primary" style={{ width: `${overRate}%` }} />
                            </div>
                            <span className="w-8 text-right text-xs tabular-nums text-text-secondary">{overRate}%</span>
                          </div>
                        </td>
                        <td className="px-5 py-3 text-right">
                          <button
                            type="button"
                            onClick={() => handleOpenDetail(ref.referee_name)}
                            className="inline-flex items-center gap-1 rounded border border-border bg-background-primary px-2.5 py-1 text-xs font-medium text-text-primary hover:bg-background-secondary transition-colors cursor-pointer"
                          >
                            Detay <ChevronRight className="h-3.5 w-3.5 text-text-tertiary" />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div className="divide-y divide-border-light md:hidden">
              {sortedReferees.map((ref) => {
                const initials = (ref.referee_name || '?').split(' ').map((part) => part[0]).join('').slice(0, 2);
                const overRate = Math.min(100, Number(ref.over_3_5_pct) || 0);
                return (
                  <article key={ref.id || ref.referee_name} className="p-4 space-y-3">
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex min-w-0 items-center gap-3">
                        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-background-tertiary border border-border text-xs font-semibold text-text-primary">
                          {initials}
                        </span>
                        <div className="min-w-0">
                          <h3 className="truncate text-sm font-medium text-text-primary">{ref.referee_name}</h3>
                          <div className="mt-0.5">{ref.is_career_fallback ? <span className="text-xs text-text-muted">Bu sezon atama yok</span> : renderStrictnessBadge(ref.strictness_label)}</div>
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => handleOpenDetail(ref.referee_name)}
                        className="shrink-0 rounded border border-border bg-background-primary px-2.5 py-1 text-xs font-medium text-text-primary hover:bg-background-secondary transition-colors"
                      >
                        Detay
                      </button>
                    </div>

                    <div className="grid grid-cols-4 divide-x divide-border-light rounded border border-border bg-background-secondary py-2 text-center text-xs">
                      <div>
                        <span className="block text-xs text-text-secondary">Maç</span>
                        <span className="text-xs font-semibold tabular-nums text-text-primary">{ref.matches_count ?? 0}</span>
                      </div>
                      <div>
                        <span className="block text-xs text-text-secondary">Kart/maç</span>
                        <span className="text-xs font-semibold tabular-nums text-text-primary">{ref.avg_cards ?? '—'}</span>
                      </div>
                      <div>
                        <span className="block text-xs text-text-secondary">Faul/maç</span>
                        <span className="text-xs tabular-nums text-text-secondary">{ref.avg_fouls ?? '—'}</span>
                      </div>
                      <div>
                        <span className="block text-xs text-text-secondary">Kırmızı</span>
                        <span className="text-xs tabular-nums text-text-secondary">{ref.total_red_cards || 0}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 text-xs text-text-secondary">
                      <span className="shrink-0">4+ kart: %{overRate}</span>
                      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-background-tertiary">
                        <div className="h-full rounded-full bg-primary" style={{ width: `${overRate}%` }} />
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          </>
        )}
      </section>

      {/* Referee Detail Modal */}
      {selectedReferee && (
        <div
          className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-3 sm:p-6"
          onMouseDown={(e) => { if (e.target === e.currentTarget) setSelectedReferee(null); }}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-label={`${selectedReferee} profil detayı`}
            className="bg-background-primary rounded-md max-w-3xl w-full max-h-screen overflow-y-auto border border-border shadow-md"
          >
            {/* Modal Header */}
            <div className="sticky top-0 z-10 flex items-center justify-between border-b border-border bg-background-primary p-5 sm:p-6">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-background-tertiary border border-border text-text-primary flex items-center justify-center font-semibold text-sm shrink-0">
                  <Scale className="w-5 h-5 text-text-secondary" />
                </div>
                <div>
                  <h2 className="text-lg sm:text-xl font-semibold text-text-primary">{selectedReferee}</h2>
                  <span className="text-xs text-text-secondary">
                    {activeCompetition.name} · {activeSeason === 'all' ? 'Kariyer' : `${formatSeasonLabel(activeSeason)} sezonu`}
                  </span>
                </div>
              </div>

              <button
                type="button"
                onClick={() => setSelectedReferee(null)}
                aria-label="Kapat"
                className="rounded border border-border bg-background-primary hover:bg-background-secondary p-2 text-text-secondary hover:text-text-primary transition-colors cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {loadingDetail ? (
              <div className="py-16 text-center space-y-2">
                <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
                <p className="text-xs font-medium text-text-secondary">Hakem detayları yükleniyor...</p>
              </div>
            ) : refereeDetail ? (
              <div className="space-y-6 p-5 sm:p-6">

                {/* Season Stats Summary */}
                <div className="grid grid-cols-2 sm:grid-cols-4 divide-x divide-y sm:divide-y-0 divide-border-light rounded border border-border bg-background-primary">
                  <div className="p-4 text-center sm:text-left">
                    <span className="text-xs font-medium text-text-secondary block">Yönettiği Maç</span>
                    <span className="mt-1 block text-xl font-semibold tabular-nums text-text-primary">{refereeDetail.matches_count}</span>
                  </div>
                  <div className="p-4 text-center sm:text-left">
                    <span className="text-xs font-medium text-text-secondary block">Kart / Maç</span>
                    <span className="mt-1 block text-xl font-semibold tabular-nums text-text-primary">{refereeDetail.season_stats?.avg_cards || '—'}</span>
                  </div>
                  <div className="p-4 text-center sm:text-left">
                    <span className="text-xs font-medium text-text-secondary block">Kırmızı Kart</span>
                    <span className="mt-1 block text-xl font-semibold tabular-nums text-text-primary">{refereeDetail.season_stats?.total_red_cards || 0}</span>
                  </div>
                  <div className="p-4 text-center sm:text-left">
                    <span className="text-xs font-medium text-text-secondary block">Faul / Maç</span>
                    <span className="mt-1 block text-xl font-semibold tabular-nums text-text-primary">{refereeDetail.season_stats?.avg_fouls || '—'}</span>
                  </div>
                </div>

                {refereeDetail.career_stats && activeSeason !== 'all' && (
                  <div className="flex flex-wrap items-center justify-between gap-3 rounded border border-border bg-background-secondary p-4">
                    <div>
                      <span className="block text-xs font-semibold text-text-primary">Kariyer Ortalaması</span>
                      <span className="text-xs text-text-tertiary">Tüm kayıtlı sezonlar</span>
                    </div>
                    <div className="flex items-center gap-4 text-xs">
                      <span className="text-text-secondary"><strong className="text-text-primary font-medium">{refereeDetail.career_stats.matches_count || 0}</strong> maç</span>
                      <span className="text-text-secondary"><strong className="text-text-primary font-medium tabular-nums">{refereeDetail.career_stats.avg_cards ?? '—'}</strong> kart/maç</span>
                      <span className="text-text-secondary"><strong className="text-text-primary font-medium tabular-nums">{refereeDetail.career_stats.avg_fouls ?? '—'}</strong> faul/maç</span>
                    </div>
                  </div>
                )}

                {/* Team Disciplinary Breakdown */}
                {refereeDetail.team_breakdown && refereeDetail.team_breakdown.length > 0 && (
                  <div className="space-y-2">
                    <div className="flex items-center gap-1.5 text-text-primary">
                      <Flame className="h-4 w-4 text-status-error" />
                      <h3 className="text-sm font-semibold">En Çok Kart Gösterdiği Takımlar</h3>
                    </div>
                    <div className="overflow-hidden rounded border border-border divide-y divide-border-light">
                      {refereeDetail.team_breakdown.map((t, index) => (
                        <div key={t.team_name} className="flex items-center justify-between gap-3 p-3 bg-background-primary hover:bg-background-secondary transition-colors">
                          <span className="flex min-w-0 items-center gap-2 text-xs font-medium text-text-primary">
                            <span className="w-5 text-right tabular-nums text-xs text-text-tertiary">{index + 1}</span>
                            <span className="truncate">{t.team_name}</span>
                          </span>
                          <span className="shrink-0 tabular-nums text-xs text-text-secondary">
                            <span className="font-medium text-text-primary">{t.yellows} sarı</span>
                            {t.reds > 0 && <span className="ml-2 font-medium text-status-error">{t.reds} kırmızı</span>}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Match History List */}
                <div className="space-y-2">
                  <div className="flex items-center gap-1.5 text-text-primary">
                    <Calendar className="h-4 w-4 text-text-tertiary" />
                    <h3 className="text-sm font-semibold">
                      Yönettiği Maçlar <span className="text-xs font-normal text-text-secondary">({refereeDetail.matches?.length || 0})</span>
                    </h3>
                  </div>

                  {refereeDetail.matches && refereeDetail.matches.length > 0 ? (
                    <div className="overflow-hidden rounded border border-border divide-y divide-border-light">
                      {refereeDetail.matches.map((m) => {
                        const homeTeam = getTeam(m.home_id, m.home_name);
                        const awayTeam = getTeam(m.away_id, m.away_name);
                        const detailMatch = {
                          match_id: m.match_id,
                          status: 'COMPLETED',
                          gameweek: m.gameweek,
                          kickoff_label: m.kickoff_label || m.match_date || '',
                          home_id: Number(m.home_id),
                          home_name: m.home_name,
                          home_score: m.home_score,
                          away_id: Number(m.away_id),
                          away_name: m.away_name,
                          away_score: m.away_score,
                          ground_name: m.ground_name || m.ground || '',
                        };

                        return (
                          <button
                            key={m.match_id}
                            type="button"
                            onClick={() => {
                              if (onSelectMatch) {
                                onSelectMatch(detailMatch);
                              } else {
                                setActiveModalMatch(detailMatch);
                              }
                            }}
                            className="group flex w-full flex-col gap-2.5 px-4 py-3 text-left transition-colors hover:bg-background-secondary sm:flex-row sm:items-center sm:gap-3 cursor-pointer"
                          >
                            <div className="flex items-center justify-between text-xs text-text-secondary sm:w-16 sm:shrink-0 sm:flex-col sm:items-start sm:gap-0.5">
                              <span className="tabular-nums font-medium text-text-primary">H{m.gameweek ?? '—'}</span>
                              {activeSeason === 'all' && <span>{formatSeasonLabel(m.season || '')}</span>}
                            </div>

                            <div className="flex min-w-0 flex-1 items-center justify-center gap-1.5 sm:gap-3">
                              <div className="flex min-w-0 flex-1 items-center justify-end gap-1.5 text-right">
                                <span className="truncate text-xs font-medium text-text-primary">{homeTeam.short || m.home_name}</span>
                                <img src={homeTeam.badge} alt={m.home_name} className="h-5 w-5 shrink-0 object-contain" onError={handleTeamBadgeError} />
                              </div>
                              <span className="min-w-16 shrink-0 text-center tabular-nums text-xs font-semibold text-text-primary">
                                {m.home_score ?? '—'} - {m.away_score ?? '—'}
                              </span>
                              <div className="flex min-w-0 flex-1 items-center gap-1.5">
                                <img src={awayTeam.badge} alt={m.away_name} className="h-5 w-5 shrink-0 object-contain" onError={handleTeamBadgeError} />
                                <span className="truncate text-xs font-medium text-text-primary">{awayTeam.short || m.away_name}</span>
                              </div>
                            </div>

                            <div className="flex items-center justify-between gap-3 border-t border-border-light pt-2 text-xs text-text-secondary sm:w-44 sm:shrink-0 sm:justify-end sm:border-0 sm:pt-0">
                              <span className="whitespace-nowrap">Sarı <strong className="font-medium text-text-primary tabular-nums">{m.total_yellow_cards || 0}</strong></span>
                              <span className="whitespace-nowrap">Kırmızı <strong className="font-medium text-text-primary tabular-nums">{m.total_red_cards || 0}</strong></span>
                              <span className="whitespace-nowrap">Faul <strong className="font-medium text-text-primary tabular-nums">{m.total_fouls || 0}</strong></span>
                              <ChevronRight className="hidden h-4 w-4 shrink-0 text-text-tertiary transition-transform group-hover:translate-x-0.5 sm:block" />
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="bg-background-secondary border border-border rounded p-6 text-center text-text-muted text-xs">
                      Bu hakemin seçili sezonda tamamlanmış maçı bulunmuyor.
                    </div>
                  )}
                </div>

                {/* European matches this referee took charge of in the selected season */}
                {refereeDetail.european?.matches?.length > 0 && (() => {
                  const european = refereeDetail.european;
                  const eStats = european.stats || {};
                  const value = (number, digits = 0) => (number == null ? '—' : Number(number).toFixed(digits));
                  return (
                    <div className="space-y-2">
                      <div className="flex items-center gap-1.5 text-text-primary">
                        <Trophy className="h-4 w-4 text-text-tertiary" />
                        <h3 className="text-sm font-semibold">
                          Avrupa Maçları <span className="text-xs font-normal text-text-secondary">({european.matches.length})</span>
                        </h3>
                      </div>

                      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
                        {[
                          ['Maç', eStats.matches_count],
                          ['Sarı kart', eStats.matches_with_stats ? value(eStats.total_yellow_cards) : null],
                          ['Kırmızı kart', eStats.matches_with_stats ? value(eStats.total_red_cards) : null],
                          ['Kart / maç', value(eStats.avg_cards, 2)],
                          ['Faul / maç', value(eStats.avg_fouls, 1)],
                        ].map(([label, figure]) => (
                          <div key={label} className="rounded border border-border bg-background-primary px-3 py-2">
                            <span className="block text-xs text-text-secondary">{label}</span>
                            <span className="mt-0.5 block text-base font-semibold tabular-nums text-text-primary">{figure ?? '—'}</span>
                          </div>
                        ))}
                      </div>
                      {eStats.matches_with_stats < eStats.matches_count && (
                        <p className="text-xs text-text-secondary">
                          Kart ve faul sayıları istatistiği bulunan {eStats.matches_with_stats} maç üzerinden hesaplandı.
                        </p>
                      )}

                      <div className="overflow-hidden rounded border border-border divide-y divide-border-light">
                        {european.matches.map((m) => {
                          const homeTeam = getTeam(m.home_id, m.home_name);
                          const awayTeam = getTeam(m.away_id, m.away_name);
                          const competition = COMPETITIONS[m.competition?.key] || COMPETITIONS.champions_league;
                          const detailMatch = {
                            match_id: m.match_id, status: 'COMPLETED', gameweek: m.gameweek, kickoff_label: m.kickoff_label || '',
                            home_id: m.home_id, home_name: m.home_name, home_score: m.home_score,
                            away_id: m.away_id, away_name: m.away_name, away_score: m.away_score,
                            ground_name: m.ground_name || '', stage: m.stage, group: m.group,
                          };
                          const shootout = m.home_penalties != null && m.away_penalties != null ? ` (P ${m.home_penalties}-${m.away_penalties})` : '';
                          return (
                            <button
                              key={m.match_id}
                              type="button"
                              onClick={() => (onSelectMatch ? onSelectMatch(detailMatch) : setActiveModalMatch(detailMatch))}
                              className="group flex w-full flex-col gap-2.5 px-4 py-3 text-left transition-colors hover:bg-background-secondary sm:flex-row sm:items-center sm:gap-3 cursor-pointer"
                            >
                              <div className="flex items-center gap-2 text-xs text-text-secondary sm:w-36 sm:shrink-0">
                                <CompetitionBadge competition={competition} />
                                <span className="truncate">{m.round_label}</span>
                              </div>
                              <div className="flex min-w-0 flex-1 items-center justify-center gap-1.5 sm:gap-3">
                                <div className="flex min-w-0 flex-1 items-center justify-end gap-1.5 text-right">
                                  <span className="truncate text-xs font-medium text-text-primary">{homeTeam.short || m.home_name}</span>
                                  <img src={homeTeam.badge} alt="" className="h-5 w-5 shrink-0 object-contain" onError={handleTeamBadgeError} />
                                </div>
                                <span className="min-w-16 shrink-0 text-center tabular-nums text-xs font-semibold text-text-primary">
                                  {m.home_score ?? '—'} - {m.away_score ?? '—'}{shootout}
                                </span>
                                <div className="flex min-w-0 flex-1 items-center gap-1.5">
                                  <img src={awayTeam.badge} alt="" className="h-5 w-5 shrink-0 object-contain" onError={handleTeamBadgeError} />
                                  <span className="truncate text-xs font-medium text-text-primary">{awayTeam.short || m.away_name}</span>
                                </div>
                              </div>
                              <div className="flex items-center justify-between gap-3 border-t border-border-light pt-2 text-xs text-text-secondary sm:w-44 sm:shrink-0 sm:justify-end sm:border-0 sm:pt-0">
                                <span className="whitespace-nowrap">Sarı <strong className="font-medium text-text-primary tabular-nums">{m.total_yellow_cards ?? '—'}</strong></span>
                                <span className="whitespace-nowrap">Kırmızı <strong className="font-medium text-text-primary tabular-nums">{m.total_red_cards ?? '—'}</strong></span>
                                <span className="whitespace-nowrap">Faul <strong className="font-medium text-text-primary tabular-nums">{m.total_fouls ?? '—'}</strong></span>
                                <ChevronRight className="hidden h-4 w-4 shrink-0 text-text-tertiary transition-transform group-hover:translate-x-0.5 sm:block" />
                              </div>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  );
                })()}

              </div>
            ) : null}

          </div>
        </div>
      )}

      {activeModalMatch && (
        <MatchDetailModal
          match={activeModalMatch}
          onClose={() => setActiveModalMatch(null)}
        />
      )}

    </div>
  );
}
