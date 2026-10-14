import React, { useState, useEffect, useMemo } from 'react';
import { 
  Search, 
  Scale, 
  ChevronRight, 
  X, 
  Calendar, 
  Flame, 
  ArrowUpDown
} from 'lucide-react';
import { getTeam } from '../data/teams';
import MatchDetailModal from './MatchDetailModal';

export default function RefereesTab({ selectedSeason }) {
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

  // Fetch Referees list
  useEffect(() => {
    setLoading(true);
    fetch(`/api/referees?season=${activeSeason}`)
      .then(res => res.json())
      .then(data => {
        setReferees(data?.referees || []);
        setLoading(false);
      })
      .catch(err => {
        console.error('Error fetching referees:', err);
        setLoading(false);
      });
  }, [activeSeason]);

  // Fetch Referee Detail when a referee is clicked
  const handleOpenDetail = (refName) => {
    setSelectedReferee(refName);
    setRefereeDetail(null);
    setLoadingDetail(true);
    fetch(`/api/referees/${encodeURIComponent(refName)}?season=${activeSeason}`)
      .then(res => res.json())
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

  // Strictness badge renderer
  const renderStrictnessBadge = (label) => {
    if (label === 'Yüksek Kart Eğilimi') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-rose-50 text-rose-700 border border-rose-200">
          <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse" />
          Yüksek Kart Eğilimi
        </span>
      );
    }
    if (label === 'Akıcı Oyun / Az Kart') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
          Akıcı Oyun / Az Kart
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
        <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
        Dengeli Yönetim
      </span>
    );
  };

  return (
    <div className="space-y-6">
      
      {/* Top Header Section */}
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-5 px-5 py-6 sm:px-7">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="w-8 h-8 rounded-lg bg-purple-50 border border-purple-100 flex items-center justify-center">
                <Scale className="w-4 h-4 text-[#38003c]" />
              </span>
              <span className="text-[11px] font-bold uppercase tracking-[0.16em] text-[#6b4b70]">Premier League · Hakem Merkezi</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-black tracking-tight text-slate-950">Hakem Profilleri</h2>
            <p className="max-w-2xl mt-1.5 text-sm text-slate-500">
              Sezon performansını karşılaştırın, maç yönetim kayıtlarına göz atın.
            </p>
          </div>

          {/* Season Selector */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-500">Sezon</span>
            <select
              value={activeSeason}
              onChange={(e) => setActiveSeason(e.target.value)}
              className="min-w-48 bg-white border border-slate-200 text-sm font-semibold text-slate-800 rounded-xl px-3 py-2.5 outline-none focus:border-[#38003c] focus:ring-2 focus:ring-[#38003c]/10"
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
          <div className="grid grid-cols-2 lg:grid-cols-4 border-t border-slate-100">
            <div className="px-5 py-4 sm:px-7 border-b lg:border-b-0 lg:border-r border-slate-100">
              <span className="text-[11px] font-semibold text-slate-500 block">Listelenen hakem</span>
              <span className="mt-1 block text-2xl font-black text-slate-900">{summaryStats.count}</span>
            </div>
            <div className="px-5 py-4 sm:px-7 border-b lg:border-b-0 lg:border-r border-slate-100">
              <span className="text-[11px] font-semibold text-slate-500 block">Lig kart ortalaması</span>
              <span className="mt-1 block text-2xl font-black text-slate-900">{summaryStats.avgCards}<span className="ml-1 text-xs font-semibold text-slate-500">/ maç</span></span>
            </div>
            <div className="px-5 py-4 sm:px-7 border-r border-slate-100">
              <span className="text-[11px] font-semibold text-slate-500 block">Lig faul ortalaması</span>
              <span className="mt-1 block text-2xl font-black text-slate-900">{summaryStats.avgFouls}<span className="ml-1 text-xs font-semibold text-slate-500">/ maç</span></span>
            </div>
            <div className="px-5 py-4 sm:px-7 min-w-0">
              <span className="text-[11px] font-semibold text-slate-500 block">En yüksek kart ortalaması</span>
              <span className="mt-1 block truncate text-base font-black text-[#38003c]" title={summaryStats.topStrict?.referee_name}>
                {summaryStats.topStrict?.referee_name || '-'} <span className="font-bold">· {summaryStats.topStrict?.avg_cards}</span>
              </span>
            </div>
          </div>
        )}
      </div>

      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="flex flex-col gap-4 border-b border-slate-100 p-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <div>
            <h3 className="text-base font-black text-slate-900">Hakem listesi</h3>
            <p className="mt-0.5 text-xs text-slate-500">
              {loading ? 'Hakem verileri yükleniyor...' : `${sortedReferees.length} hakem · ${activeSeason === 'all' ? 'Kariyer istatistikleri' : `${activeSeason.replace('_', '-')} sezonu`}`}
            </p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row">
            <div className="relative sm:w-64">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                type="search"
                placeholder="Hakem ara"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full rounded-lg border border-slate-200 bg-slate-50 py-2.5 pl-9 pr-3 text-sm outline-none transition focus:border-[#38003c] focus:bg-white"
              />
            </div>
            <label className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 text-xs text-slate-500">
              <ArrowUpDown className="h-3.5 w-3.5" />
              <span className="sr-only">Sıralama</span>
              <select value={sortBy} onChange={(e) => setSortBy(e.target.value)} className="bg-transparent py-2.5 font-semibold text-slate-800 outline-none">
                <option value="matches">Maç sayısı</option>
                <option value="cards">Kart ortalaması</option>
                <option value="fouls">Faul ortalaması</option>
              </select>
            </label>
          </div>
        </div>

        {loading ? (
          <div className="py-20 text-center">
            <div className="mb-3 inline-block h-8 w-8 animate-spin rounded-full border-4 border-slate-200 border-t-[#38003c]" />
            <p className="text-sm text-slate-500">Hakem verileri yükleniyor</p>
          </div>
        ) : sortedReferees.length === 0 ? (
          <div className="px-6 py-16 text-center">
            <Scale className="mx-auto mb-3 h-8 w-8 text-slate-300" />
            <p className="text-sm font-semibold text-slate-700">Hakem bulunamadı</p>
            <p className="mt-1 text-xs text-slate-500">Arama terimini değiştirip tekrar deneyin.</p>
          </div>
        ) : (
          <>
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full min-w-[820px] border-collapse text-left">
                <thead>
                  <tr className="bg-slate-50 text-[10px] font-bold uppercase tracking-wider text-slate-500">
                    <th className="px-6 py-3">Hakem</th>
                    <th className="px-4 py-3 text-right">Maç</th>
                    <th className="px-4 py-3 text-right">Kart / maç</th>
                    <th className="px-4 py-3 text-right">Faul / maç</th>
                    <th className="px-4 py-3 text-right">Kırmızı</th>
                    <th className="px-4 py-3">4+ kart oranı</th>
                    <th className="px-6 py-3 text-right">Profil</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {sortedReferees.map((ref) => {
                    const initials = (ref.referee_name || '?').split(' ').map((part) => part[0]).join('').slice(0, 2);
                    const overRate = Math.min(100, Number(ref.over_3_5_pct) || 0);
                    return (
                      <tr key={ref.id || ref.referee_name} className="transition-colors hover:bg-purple-50/30">
                        <td className="px-6 py-3.5">
                          <div className="flex items-center gap-3">
                            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#f3edf4] text-xs font-black text-[#38003c]">{initials}</span>
                            <div className="min-w-0">
                              <span className="block truncate text-sm font-bold text-slate-900">{ref.referee_name}</span>
                              <span className="text-[11px] text-slate-500">{ref.is_career_fallback ? 'Bu sezon atama yok' : renderStrictnessBadge(ref.strictness_label)}</span>
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3.5 text-right text-sm font-semibold tabular-nums text-slate-700">{ref.matches_count ?? 0}</td>
                        <td className="px-4 py-3.5 text-right text-sm font-bold tabular-nums text-amber-800">{ref.avg_cards ?? '-'}</td>
                        <td className="px-4 py-3.5 text-right text-sm tabular-nums text-slate-700">{ref.avg_fouls ?? '-'}</td>
                        <td className="px-4 py-3.5 text-right text-sm tabular-nums text-slate-700">{ref.total_red_cards || 0}</td>
                        <td className="px-4 py-3.5">
                          <div className="flex w-36 items-center gap-2">
                            <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-100">
                              <div className="h-full rounded-full bg-[#6f3b75]" style={{ width: `${overRate}%` }} />
                            </div>
                            <span className="w-9 text-right text-xs font-semibold tabular-nums text-slate-700">{overRate}%</span>
                          </div>
                        </td>
                        <td className="px-6 py-3.5 text-right">
                          <button onClick={() => handleOpenDetail(ref.referee_name)} className="inline-flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-bold text-[#38003c] transition hover:bg-purple-50">
                            Maçlar <ChevronRight className="h-3.5 w-3.5" />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div className="divide-y divide-slate-100 md:hidden">
              {sortedReferees.map((ref) => {
                const initials = (ref.referee_name || '?').split(' ').map((part) => part[0]).join('').slice(0, 2);
                const overRate = Math.min(100, Number(ref.over_3_5_pct) || 0);
                return (
                  <article key={ref.id || ref.referee_name} className="p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex min-w-0 items-center gap-3">
                        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#f3edf4] text-xs font-black text-[#38003c]">{initials}</span>
                        <div className="min-w-0">
                          <h4 className="truncate text-sm font-bold text-slate-900">{ref.referee_name}</h4>
                          <span className="text-[11px] text-slate-500">{ref.is_career_fallback ? 'Bu sezon atama yok' : ref.strictness_label || 'Hakem'}</span>
                        </div>
                      </div>
                      <button onClick={() => handleOpenDetail(ref.referee_name)} className="shrink-0 rounded-lg px-2 py-1.5 text-xs font-bold text-[#38003c] hover:bg-purple-50">Maçlar <ChevronRight className="inline h-3.5 w-3.5" /></button>
                    </div>
                    <div className="mt-4 grid grid-cols-4 divide-x divide-slate-100 rounded-xl border border-slate-100 bg-slate-50/70 py-2.5 text-center">
                      <div><span className="block text-[10px] text-slate-500">Maç</span><strong className="text-sm text-slate-900">{ref.matches_count ?? 0}</strong></div>
                      <div><span className="block text-[10px] text-slate-500">Kart/maç</span><strong className="text-sm text-amber-800">{ref.avg_cards ?? '-'}</strong></div>
                      <div><span className="block text-[10px] text-slate-500">Faul/maç</span><strong className="text-sm text-slate-900">{ref.avg_fouls ?? '-'}</strong></div>
                      <div><span className="block text-[10px] text-slate-500">Kırmızı</span><strong className="text-sm text-slate-900">{ref.total_red_cards || 0}</strong></div>
                    </div>
                    <div className="mt-3 flex items-center gap-2 text-[11px] text-slate-500">
                      <span className="shrink-0">4+ kart %{overRate}</span>
                      <div className="h-1 flex-1 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-[#6f3b75]" style={{ width: `${overRate}%` }} /></div>
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
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-3xl max-w-4xl w-full max-h-[90vh] overflow-y-auto border border-slate-200 shadow-2xl">
            
            {/* Modal Header */}
            <div className="sticky top-0 z-10 flex items-start justify-between border-b border-slate-100 bg-white/95 backdrop-blur px-5 py-4 sm:px-7">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-2xl bg-[#38003c] text-white flex items-center justify-center font-black text-base shadow-sm shrink-0">
                  <Scale className="w-6 h-6 text-[#00ff87]" />
                </div>
                <div>
                  <h3 className="text-lg sm:text-xl font-black text-slate-900">{selectedReferee}</h3>
                  <span className="text-xs text-slate-500">Premier League • {activeSeason === 'all' ? 'Kariyer' : `${activeSeason.replace('_', '-')} sezonu`}</span>
                </div>
              </div>

              <button
                onClick={() => setSelectedReferee(null)}
                aria-label="Profili kapat"
                className="p-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-600 transition-colors shrink-0"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {loadingDetail ? (
              <div className="py-20 text-center">
                <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-slate-300 border-t-[#38003c] mb-3" />
                <p className="text-xs text-slate-500">Hakemin yönettiği maçlar ve detaylar getiriliyor...</p>
              </div>
            ) : refereeDetail ? (
              <div className="space-y-7 p-5 sm:p-7">

                {/* Season & Career Stats Comparison Cards */}
                <div className="grid grid-cols-2 lg:grid-cols-4 divide-x divide-y lg:divide-y-0 divide-slate-200 overflow-hidden rounded-2xl border border-slate-200">
                  <div className="bg-white px-4 py-3.5">
                    <span className="text-[10px] font-bold text-slate-500 block uppercase tracking-wide">Yönettiği maç</span>
                    <strong className="mt-1 block text-2xl font-black tabular-nums text-slate-900">{refereeDetail.matches_count}</strong>
                  </div>
                  <div className="bg-white px-4 py-3.5">
                    <span className="text-[10px] font-bold text-slate-500 block uppercase tracking-wide">Kart / maç</span>
                    <strong className="mt-1 block text-2xl font-black tabular-nums text-amber-800">{refereeDetail.season_stats?.avg_cards || '-'}</strong>
                  </div>
                  <div className="bg-white px-4 py-3.5">
                    <span className="text-[10px] font-bold text-slate-500 block uppercase tracking-wide">Kırmızı kart</span>
                    <strong className="mt-1 block text-2xl font-black tabular-nums text-slate-900">{refereeDetail.season_stats?.total_red_cards || 0}</strong>
                  </div>
                  <div className="bg-white px-4 py-3.5">
                    <span className="text-[10px] font-bold text-slate-500 block uppercase tracking-wide">Faul / maç</span>
                    <strong className="mt-1 block text-2xl font-black tabular-nums text-slate-900">{refereeDetail.season_stats?.avg_fouls || '-'}</strong>
                  </div>
                </div>

                {refereeDetail.career_stats && activeSeason !== 'all' && (
                  <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                    <div>
                      <span className="block text-xs font-bold text-slate-800">Kariyer ortalaması</span>
                      <span className="text-[11px] text-slate-500">Tüm kayıtlı sezonlar</span>
                    </div>
                    <div className="flex items-center gap-4 text-xs">
                      <span className="text-slate-600"><strong className="text-slate-900">{refereeDetail.career_stats.matches_count || 0}</strong> maç</span>
                      <span className="text-amber-800"><strong>{refereeDetail.career_stats.avg_cards ?? '-'}</strong> kart/maç</span>
                      <span className="text-sky-800"><strong>{refereeDetail.career_stats.avg_fouls ?? '-'}</strong> faul/maç</span>
                    </div>
                  </div>
                )}

                {/* Team Disciplinary Breakdown */}
                {refereeDetail.team_breakdown && refereeDetail.team_breakdown.length > 0 && (
                  <div className="space-y-2.5">
                    <div className="flex items-center gap-2">
                      <Flame className="h-4 w-4 text-rose-500" />
                      <h4 className="text-sm font-bold text-slate-900">En çok kart gösterdiği takımlar</h4>
                    </div>
                    <div className="overflow-hidden rounded-xl border border-slate-200">
                      {refereeDetail.team_breakdown.map((t, index) => (
                        <div key={t.team_name} className="flex items-center justify-between gap-3 border-b border-slate-100 px-3 py-2.5 last:border-0">
                          <span className="flex min-w-0 items-center gap-2 text-xs font-semibold text-slate-700">
                            <span className="w-5 text-right font-mono text-[10px] text-slate-400">{index + 1}</span>
                            <span className="truncate">{t.team_name}</span>
                          </span>
                          <span className="shrink-0 font-mono text-xs font-semibold text-slate-700">
                            <span className="text-amber-700">{t.yellows} sarı</span>
                            {t.reds > 0 && <span className="ml-2 text-rose-700">{t.reds} kırmızı</span>}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Match History List */}
                <div className="space-y-3">
                  <h4 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-[#38003c]" />
                    Yönettiği maçlar <span className="text-xs font-medium text-slate-500">({refereeDetail.matches?.length || 0})</span>
                  </h4>

                  {refereeDetail.matches && refereeDetail.matches.length > 0 ? (
                    <div className="overflow-hidden rounded-xl border border-slate-200 divide-y divide-slate-100">
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
                            onClick={() => setActiveModalMatch(detailMatch)}
                            className="group flex w-full flex-col gap-2.5 px-3.5 py-3 text-left transition-colors hover:bg-slate-50 sm:flex-row sm:items-center sm:gap-3 sm:px-4"
                          >
                            <div className="flex items-center justify-between text-[11px] text-slate-500 sm:w-16 sm:shrink-0 sm:flex-col sm:items-start sm:gap-1">
                              <span className="font-mono font-semibold">H{m.gameweek ?? '-'}</span>
                              {activeSeason === 'all' && <span>{String(m.season || '').replace('_', '-')}</span>}
                            </div>

                            <div className="flex min-w-0 flex-1 items-center justify-center gap-1.5 sm:gap-3">
                              <div className="flex min-w-0 flex-1 items-center justify-end gap-1.5 text-right">
                                <span className="truncate text-xs font-semibold text-slate-800">{homeTeam.short || m.home_name}</span>
                                <img src={homeTeam.badge} alt={m.home_name} className="h-6 w-6 shrink-0 object-contain" onError={(e) => { e.currentTarget.src = '/badges/1.svg'; }} />
                              </div>
                              <span className="min-w-[64px] shrink-0 text-center font-mono text-xs font-black text-slate-900">
                                {m.home_score ?? '-'} - {m.away_score ?? '-'}
                              </span>
                              <div className="flex min-w-0 flex-1 items-center gap-1.5">
                                <img src={awayTeam.badge} alt={m.away_name} className="h-6 w-6 shrink-0 object-contain" onError={(e) => { e.currentTarget.src = '/badges/1.svg'; }} />
                                <span className="truncate text-xs font-semibold text-slate-800">{awayTeam.short || m.away_name}</span>
                              </div>
                            </div>

                            <div className="flex items-center justify-between gap-3 border-t border-slate-100 pt-2 text-[11px] text-slate-600 sm:w-40 sm:shrink-0 sm:justify-end sm:border-0 sm:pt-0">
                              <span className="whitespace-nowrap">Sarı <strong className="text-slate-900">{m.total_yellow_cards || 0}</strong></span>
                              <span className="whitespace-nowrap">Kırmızı <strong className="text-slate-900">{m.total_red_cards || 0}</strong></span>
                              <span className="whitespace-nowrap">Faul <strong className="text-slate-900">{m.total_fouls || 0}</strong></span>
                              <ChevronRight className="hidden h-4 w-4 shrink-0 text-slate-300 transition group-hover:translate-x-0.5 group-hover:text-slate-600 sm:block" />
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="bg-slate-50 border border-slate-200 rounded-2xl p-6 text-center text-slate-400 text-xs">
                      Bu hakemin seçili sezonda tamamlanmış maçı bulunmuyor.
                    </div>
                  )}
                </div>

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
