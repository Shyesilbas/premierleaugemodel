import React, { useState, useEffect, useMemo } from 'react';
import { 
  Search, 
  Scale, 
  AlertTriangle, 
  ChevronRight, 
  X, 
  Calendar, 
  Shield, 
  Activity, 
  Flame, 
  CheckCircle2, 
  Layers,
  Award,
  TrendingUp,
  MapPin
} from 'lucide-react';
import { getTeam } from '../data/teams';

export default function RefereesTab({ selectedSeason }) {
  const [referees, setReferees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [activeSeason, setActiveSeason] = useState(selectedSeason || '2026_27');
  const [selectedReferee, setSelectedReferee] = useState(null);
  const [refereeDetail, setRefereeDetail] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

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
    return referees.filter(r => r.referee_name.toLowerCase().includes(q));
  }, [referees, search]);

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
      <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="p-1.5 rounded-lg bg-purple-50 text-[#38003c] border border-purple-100">
                <Scale className="w-5 h-5 text-[#38003c]" />
              </span>
              <h2 className="text-xl font-black text-slate-900 tracking-tight">
                Hakem Profilleri & Disiplin Analizi
              </h2>
            </div>
            <p className="text-xs text-slate-500">
              Premier League PGMOL hakemlerinin sezonluk kart, faul ve sertlik eğilimleri, maç geçmişleri ve model tahmin verileri.
            </p>
          </div>

          {/* Season Selector */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-500">Sezon:</span>
            <select
              value={activeSeason}
              onChange={(e) => setActiveSeason(e.target.value)}
              className="bg-slate-50 border border-slate-200 text-xs font-bold text-slate-800 rounded-xl px-3 py-2 outline-none focus:ring-2 focus:ring-[#38003c]/20"
            >
              <option value="2026_27">2026-27 (Güncel Sezon)</option>
              <option value="2025_26">2025-26 Sezonu</option>
              <option value="2024_25">2024-25 Sezonu</option>
              <option value="2023_24">2023-24 Sezonu</option>
              <option value="all">Tüm Sezonlar (Kariyer)</option>
            </select>
          </div>
        </div>

        {/* Global Summary Metrics */}
        {summaryStats && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-5 pt-5 border-t border-slate-100">
            <div className="bg-slate-50/70 border border-slate-200/60 p-3 rounded-xl">
              <span className="text-[10px] font-bold text-slate-500 block uppercase">Aktif Hakemler</span>
              <span className="text-xl font-black text-slate-900">{summaryStats.count} Hakem</span>
            </div>
            <div className="bg-amber-50/60 border border-amber-200/60 p-3 rounded-xl">
              <span className="text-[10px] font-bold text-amber-700 block uppercase">Lig Kart Ortalaması</span>
              <span className="text-xl font-black text-amber-900">{summaryStats.avgCards} <span className="text-xs font-normal">kart/maç</span></span>
            </div>
            <div className="bg-sky-50/60 border border-sky-200/60 p-3 rounded-xl">
              <span className="text-[10px] font-bold text-sky-700 block uppercase">Lig Faul Ortalaması</span>
              <span className="text-xl font-black text-sky-900">{summaryStats.avgFouls} <span className="text-xs font-normal">faul/maç</span></span>
            </div>
            <div className="bg-purple-50/60 border border-purple-200/60 p-3 rounded-xl">
              <span className="text-[10px] font-bold text-[#38003c] block uppercase">En Sert Hakem</span>
              <span className="text-sm font-black text-[#38003c] truncate block">
                {summaryStats.topStrict?.referee_name || '-'} ({summaryStats.topStrict?.avg_cards} kart)
              </span>
            </div>
          </div>
        )}

        {/* Search Bar */}
        <div className="mt-4 relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Hakem adına göre ara (örn. Michael Oliver, Anthony Taylor, Chris Kavanagh)..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl outline-none focus:bg-white focus:border-[#38003c] transition-all"
          />
        </div>
      </div>

      {/* Referees Grid */}
      {loading ? (
        <div className="py-20 text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-slate-300 border-t-[#38003c] mb-3" />
          <p className="text-xs font-medium text-slate-500">Hakem verileri ve kart istatistikleri yükleniyor...</p>
        </div>
      ) : filteredReferees.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-slate-400">
          <Scale className="w-10 h-10 mx-auto mb-2 opacity-30" />
          <p className="text-sm font-medium">Aramanıza uygun hakem bulunamadı.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredReferees.map((ref) => {
            const initials = ref.referee_name
              .split(' ')
              .map(n => n[0])
              .join('')
              .slice(0, 2);

            return (
              <div 
                key={ref.id || ref.referee_name}
                className="bg-white rounded-2xl border border-slate-200/90 hover:border-purple-300 hover:shadow-md transition-all duration-200 overflow-hidden flex flex-col justify-between group"
              >
                {/* Card Top */}
                <div className="p-4 space-y-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-[#38003c] to-[#250128] text-white flex items-center justify-center font-bold text-sm shadow-sm shrink-0">
                        {initials}
                      </div>
                      <div>
                        <h3 className="font-extrabold text-slate-900 group-hover:text-[#38003c] transition-colors leading-tight">
                          {ref.referee_name}
                        </h3>
                        <span className="text-[11px] text-slate-400">
                          {ref.is_career_fallback ? 'Kariyer Kaydı (Bu Sezon Atanmadı)' : `${ref.matches_count} Maç Yönetti`}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Strictness badge */}
                  <div>
                    {renderStrictnessBadge(ref.strictness_label)}
                  </div>

                  {/* 4-Box Metric Display */}
                  <div className="grid grid-cols-4 gap-1.5 text-center text-[10px] font-mono pt-1">
                    <div className="bg-slate-50 border border-slate-100 py-1.5 px-1 rounded-lg">
                      <span className="text-[8px] text-slate-400 font-sans block">MAÇ</span>
                      <strong className="text-slate-800 text-xs font-bold">{ref.matches_count}</strong>
                    </div>
                    <div className="bg-amber-50/70 border border-amber-100 py-1.5 px-1 rounded-lg">
                      <span className="text-[8px] text-amber-600 font-sans font-bold block">ORT. KART</span>
                      <strong className="text-amber-900 text-xs font-bold">{ref.avg_cards}</strong>
                    </div>
                    <div className="bg-rose-50/70 border border-rose-100 py-1.5 px-1 rounded-lg">
                      <span className="text-[8px] text-rose-600 font-sans font-bold block">KIRMIZI</span>
                      <strong className="text-rose-900 text-xs font-bold">{ref.total_red_cards || 0} 🟥</strong>
                    </div>
                    <div className="bg-sky-50/70 border border-sky-100 py-1.5 px-1 rounded-lg">
                      <span className="text-[8px] text-sky-600 font-sans font-bold block">ORT. FAUL</span>
                      <strong className="text-sky-900 text-xs font-bold">{ref.avg_fouls}</strong>
                    </div>
                  </div>

                  {/* 3.5 Üst Kart Olasılık Çubuğu */}
                  <div className="pt-1">
                    <div className="flex items-center justify-between text-[10px] mb-1">
                      <span className="text-slate-500 font-medium">+3.5 Kart Görme Oranı:</span>
                      <span className="font-bold text-slate-800">%{ref.over_3_5_pct || 0}</span>
                    </div>
                    <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
                      <div 
                        className={`h-full rounded-full ${
                          (ref.over_3_5_pct || 0) >= 60 ? 'bg-rose-500' :
                          (ref.over_3_5_pct || 0) >= 40 ? 'bg-amber-500' : 'bg-emerald-500'
                        }`}
                        style={{ width: `${Math.min(100, ref.over_3_5_pct || 0)}%` }}
                      />
                    </div>
                  </div>
                </div>

                {/* Card Action Footer */}
                <div className="px-4 py-2.5 bg-slate-50 border-t border-slate-100 flex items-center justify-between">
                  <span className="text-[11px] text-slate-500">
                    Toplam {ref.total_yellow_cards || 0} 🟨 Sarı Kart
                  </span>
                  <button
                    onClick={() => handleOpenDetail(ref.referee_name)}
                    className="inline-flex items-center gap-1 text-[11px] font-bold text-[#38003c] hover:text-purple-700 group-hover:underline"
                  >
                    Maçları Gör <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Referee Detail Modal */}
      {selectedReferee && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-3xl max-w-3xl w-full max-h-[90vh] overflow-y-auto border border-slate-200 shadow-2xl space-y-6 p-6">
            
            {/* Modal Header */}
            <div className="flex items-start justify-between border-b border-slate-100 pb-4">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-2xl bg-[#38003c] text-white flex items-center justify-center font-black text-base shadow-sm">
                  <Scale className="w-6 h-6 text-[#00ff87]" />
                </div>
                <div>
                  <h3 className="text-xl font-black text-slate-900">{selectedReferee}</h3>
                  <span className="text-xs text-slate-500">Premier League PGMOL Baş Hakemi • {activeSeason} Sezonu Analizi</span>
                </div>
              </div>

              <button
                onClick={() => setSelectedReferee(null)}
                className="p-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-600 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {loadingDetail ? (
              <div className="py-16 text-center">
                <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-slate-300 border-t-[#38003c] mb-3" />
                <p className="text-xs text-slate-500">Hakemin yönettiği maçlar ve detaylar getiriliyor...</p>
              </div>
            ) : refereeDetail ? (
              <div className="space-y-6">

                {/* Season & Career Stats Comparison Cards */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="bg-purple-50/60 border border-purple-200/70 p-3 rounded-2xl text-center">
                    <span className="text-[10px] font-bold text-[#38003c] block">YÖNETTİĞİ MAÇ</span>
                    <strong className="text-2xl font-black text-[#38003c]">{refereeDetail.matches_count}</strong>
                  </div>
                  <div className="bg-amber-50/60 border border-amber-200/70 p-3 rounded-2xl text-center">
                    <span className="text-[10px] font-bold text-amber-700 block">ORTALAMA KART</span>
                    <strong className="text-2xl font-black text-amber-900">{refereeDetail.season_stats?.avg_cards || '-'}</strong>
                  </div>
                  <div className="bg-rose-50/60 border border-rose-200/70 p-3 rounded-2xl text-center">
                    <span className="text-[10px] font-bold text-rose-700 block">TOPLAM KIRMIZI</span>
                    <strong className="text-2xl font-black text-rose-900">{refereeDetail.season_stats?.total_red_cards || 0}</strong>
                  </div>
                  <div className="bg-sky-50/60 border border-sky-200/70 p-3 rounded-2xl text-center">
                    <span className="text-[10px] font-bold text-sky-700 block">ORTALAMA FAUL</span>
                    <strong className="text-2xl font-black text-sky-900">{refereeDetail.season_stats?.avg_fouls || '-'}</strong>
                  </div>
                </div>

                {/* Team Disciplinary Breakdown */}
                {refereeDetail.team_breakdown && refereeDetail.team_breakdown.length > 0 && (
                  <div className="space-y-2">
                    <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                      <Flame className="w-3.5 h-3.5 text-rose-500" />
                      En Çok Kart Gösterdiği Takımlar
                    </h4>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                      {refereeDetail.team_breakdown.map((t) => (
                        <div key={t.team_name} className="bg-slate-50 border border-slate-200/70 p-2.5 rounded-xl flex items-center justify-between">
                          <span className="text-xs font-bold text-slate-800 truncate">{t.team_name}</span>
                          <div className="text-right shrink-0 font-mono text-[11px] font-bold">
                            <span className="text-amber-700">{t.yellows}🟨</span>
                            {t.reds > 0 && <span className="text-rose-700 ml-1">{t.reds}🟥</span>}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Match History List */}
                <div className="space-y-3">
                  <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                    <Calendar className="w-3.5 h-3.5 text-purple-600" />
                    Bu Sezon Yönettiği Maçlar ({refereeDetail.matches?.length || 0})
                  </h4>

                  {refereeDetail.matches && refereeDetail.matches.length > 0 ? (
                    <div className="space-y-2">
                      {refereeDetail.matches.map((m) => {
                        const homeTeam = getTeam(m.home_name);
                        const awayTeam = getTeam(m.away_name);

                        return (
                          <div 
                            key={m.match_id}
                            className="bg-slate-50/70 border border-slate-200/80 rounded-2xl p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-white hover:border-purple-200 transition-colors"
                          >
                            {/* Match Teams & Score */}
                            <div className="flex items-center gap-3">
                              <span className="text-[10px] font-bold font-mono text-purple-900 bg-purple-50 border border-purple-200 px-2 py-0.5 rounded-md shrink-0">
                                GW {m.gameweek}
                              </span>

                              <div className="flex items-center gap-2 text-xs font-bold text-slate-900">
                                <span className="flex items-center gap-1.5">
                                  {homeTeam?.badge && <img src={homeTeam.badge} alt="" className="w-4 h-4 object-contain" />}
                                  <span>{m.home_name}</span>
                                </span>
                                <span className="font-mono bg-white border border-slate-200 px-2 py-0.5 rounded text-slate-900 font-extrabold text-xs shadow-2xs">
                                  {m.home_score} - {m.away_score}
                                </span>
                                <span className="flex items-center gap-1.5">
                                  {awayTeam?.badge && <img src={awayTeam.badge} alt="" className="w-4 h-4 object-contain" />}
                                  <span>{m.away_name}</span>
                                </span>
                              </div>
                            </div>

                            {/* Cards and Fouls Shown in Match */}
                            <div className="flex items-center gap-3 shrink-0 font-mono text-xs">
                              <div className="flex items-center gap-1.5 bg-amber-50 border border-amber-200/80 px-2 py-1 rounded-lg text-amber-900 font-bold">
                                <span>{m.total_yellow_cards || 0} 🟨</span>
                                {m.total_red_cards > 0 && <span className="text-rose-700">{m.total_red_cards} 🟥</span>}
                              </div>
                              <div className="bg-slate-100 text-slate-700 px-2 py-1 rounded-lg text-[11px] font-bold">
                                {m.total_fouls ? `${m.total_fouls} Faul` : '-'}
                              </div>
                            </div>
                          </div>
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

    </div>
  );
}
