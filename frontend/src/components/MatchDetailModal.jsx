import React, { useEffect, useState } from 'react';
import { 
  X, 
  Clock, 
  Users, 
  BarChart3, 
  Activity, 
  Shield, 
  Calendar, 
  MapPin, 
  ChevronRight, 
  Award,
  Target,
  Flag,
  AlertCircle,
  Sparkles,
  RefreshCw,
  Zap,
  Eye,
  CreditCard,
  Scale,
  Flame,
  TrendingUp,
  RotateCw
} from 'lucide-react';
import PlayerAvatar from './PlayerAvatar';
import { getTeam } from '../data/teams';
import { getCachedTeamData, setCachedTeamData } from '../utils/teamProfileCache';

export default function MatchDetailModal({ match, onClose, currentGameweek }) {
  const isCompleted = Boolean(
    match.status === 'COMPLETED' || 
    (match.home_score !== null && match.home_score !== undefined && match.home_score !== '')
  );
  const isPredictable = !isCompleted && (
    currentGameweek ? Number(match.gameweek) === Number(currentGameweek) : true
  );
  const [activeTab, setActiveTab] = useState(
    isCompleted ? 'stats' : isPredictable ? 'prediction' : 'lineups'
  );
  const [playerTabSide, setPlayerTabSide] = useState('home'); // 'home' or 'away'
  const [details, setDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [prediction, setPrediction] = useState(null);
  const [loadingPrediction, setLoadingPrediction] = useState(false);
  const [predSubTab, setPredSubTab] = useState('outcome'); // 'outcome', 'goals', 'stats'
  const [refreshKey, setRefreshKey] = useState(0);

  // If match is completed or not in current gameweek, NEVER show or allow prediction tab
  useEffect(() => {
    if ((isCompleted || !isPredictable) && activeTab === 'prediction') {
      setActiveTab(isCompleted ? 'stats' : 'lineups');
    }
  }, [isCompleted, isPredictable, activeTab]);

  const homeTeam = getTeam(match.home_id, match.home_name);
  const awayTeam = getTeam(match.away_id, match.away_name);

  useEffect(() => {
    if (!match.match_id) return;

    if (isCompleted && refreshKey === 0) {
      const cached = getCachedTeamData('match_detail', match.match_id, 'all');
      if (cached?.data) {
        setDetails(cached.data);
        setLoading(false);
        return;
      }
    }

    setLoading(true);
    fetch(`/api/match/${match.match_id}/details`)
      .then(res => res.json())
      .then(data => {
        setDetails(data);
        if (isCompleted || data?.team_stats?.length > 0 || (data?.events && data.events.length > 0)) {
          setCachedTeamData('match_detail', match.match_id, 'all', data, null, 'Tamamlanan maç detayı');
        }
        setLoading(false);
      })
      .catch(err => {
        console.error('Error fetching match details:', err);
        setLoading(false);
      });
  }, [match.match_id, isCompleted, refreshKey]);

  useEffect(() => {
    // Only fetch prediction for unplayed matches in the current active gameweek
    if (isCompleted || !isPredictable) return;
    if (!match.home_id || !match.away_id) return;
    setLoadingPrediction(true);
    fetch(`/api/predict?home_id=${match.home_id}&away_id=${match.away_id}`)
      .then(res => res.json())
      .then(data => {
        setPrediction(data);
        setLoadingPrediction(false);
      })
      .catch(err => {
        console.error('Error fetching prediction:', err);
        setLoadingPrediction(false);
      });
  }, [match.home_id, match.away_id, isCompleted, isPredictable]);

  const renderEventIcon = (type) => {
    switch (type) {
      case 'goal':
        return <Target className="w-3.5 h-3.5 text-emerald-600" />;
      case 'corner':
        return <Flag className="w-3.5 h-3.5 text-sky-600" />;
      case 'attempt saved':
        return <Shield className="w-3.5 h-3.5 text-purple-600" />;
      case 'miss':
        return <Activity className="w-3.5 h-3.5 text-slate-400" />;
      case 'attempt blocked':
        return <Shield className="w-3.5 h-3.5 text-slate-500" />;
      case 'yellow card':
        return <span className="w-2.5 h-3.5 bg-amber-400 rounded-xs inline-block shadow-xs" title="Sarı Kart" />;
      case 'red card':
        return <span className="w-2.5 h-3.5 bg-rose-600 rounded-xs inline-block shadow-xs" title="Kırmızı Kart" />;
      case 'substitution':
        return <RefreshCw className="w-3.5 h-3.5 text-blue-600" />;
      default:
        return <Zap className="w-3.5 h-3.5 text-amber-500" />;
    }
  };

  const lineups = details?.lineups || [];
  const homeLineup = lineups.find(l => l.team_id === match.home_id) || lineups[0];
  const awayLineup = lineups.find(l => l.team_id === match.away_id) || lineups[1];
  const teamStats = details?.team_stats || [];
  const playerStats = details?.player_stats || { home: [], away: [] };
  const events = details?.events || [];
  const meta = details?.metadata || {};
  const timeline = details?.timeline || [];

  const formatPosition = (pos) => {
    if (!pos) return 'Mevki Belirtilmedi';
    const p = String(pos).toUpperCase();
    if (['G', 'GK', 'GOALKEEPER'].includes(p)) return 'Kaleci';
    if (['D', 'DEF', 'DEFENDER', 'CB', 'LB', 'RB', 'LWB', 'RWB'].includes(p)) return 'Savunma';
    if (['M', 'MID', 'MIDFIELDER', 'CM', 'DM', 'AM', 'LM', 'RM'].includes(p)) return 'Orta Saha';
    if (['F', 'FWD', 'FORWARD', 'ST', 'CF', 'RW', 'LW', 'ATT'].includes(p)) return 'Forvet';
    return pos;
  };

  const getPositionBadgeClass = (pos) => {
    if (!pos) return 'bg-slate-100 text-slate-700 border-slate-200';
    const p = String(pos).toUpperCase();
    if (['G', 'GK', 'GOALKEEPER'].includes(p)) return 'bg-amber-100 text-amber-900 border-amber-200';
    if (['D', 'DEF', 'DEFENDER', 'CB', 'LB', 'RB', 'LWB', 'RWB'].includes(p)) return 'bg-sky-100 text-sky-900 border-sky-200';
    if (['M', 'MID', 'MIDFIELDER', 'CM', 'DM', 'AM', 'LM', 'RM'].includes(p)) return 'bg-purple-100 text-[#38003c] border-purple-200';
    if (['F', 'FWD', 'FORWARD', 'ST', 'CF', 'RW', 'LW', 'ATT'].includes(p)) return 'bg-rose-100 text-rose-900 border-rose-200';
    return 'bg-slate-100 text-slate-700 border-slate-200';
  };

  // Helper to calculate comparison bar percentage
  const calcBarWidths = (item) => {
    let h = item.rawHome !== undefined ? Number(item.rawHome) : Number(item.home);
    let a = item.rawAway !== undefined ? Number(item.rawAway) : Number(item.away);

    if (isNaN(h)) h = 0;
    if (isNaN(a)) a = 0;

    const total = h + a;
    if (total === 0) return { homePct: 50, awayPct: 50 };

    const homePct = Math.min(100, Math.max(5, (h / total) * 100));
    const awayPct = 100 - homePct;
    return { homePct, awayPct };
  };

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 md:p-6 bg-slate-900/60 backdrop-blur-sm animate-fadeIn"
      onClick={onClose}
    >
      <div 
        className="bg-white border border-slate-200 rounded-3xl max-w-4xl w-full max-h-[92vh] flex flex-col shadow-2xl overflow-hidden relative"
        onClick={e => e.stopPropagation()}
      >
        
        {/* Header & Scoreboard (Compact & Sleek) */}
        <div className="py-3 px-4 sm:px-6 border-b border-slate-200 bg-slate-50/70 relative shrink-0">
          <div className="absolute top-3 right-3 flex items-center gap-1 z-10">
            <button
              onClick={() => setRefreshKey(k => k + 1)}
              title="Maç verisini sunucudan tazele"
              className="p-1.5 rounded-lg bg-white border border-slate-200 hover:bg-slate-100 text-slate-500 hover:text-slate-900 transition-colors shadow-2xs"
            >
              <RotateCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-emerald-600' : ''}`} />
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg bg-white border border-slate-200 hover:bg-slate-100 text-slate-500 hover:text-slate-900 transition-colors shadow-2xs"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="flex items-center justify-between pr-16 sm:pr-20">
            {/* Home Team */}
            <div className="flex items-center gap-2.5 flex-1 min-w-0">
              <img 
                src={homeTeam.badge} 
                alt={homeTeam.name} 
                className="w-8 h-8 sm:w-9 sm:h-9 object-contain shrink-0"
                onError={(e) => { e.target.src = '/badges/1.svg'; }}
              />
              <div className="min-w-0">
                <h3 className="font-bold text-sm sm:text-base text-slate-900 leading-tight truncate">
                  {homeTeam.name}
                </h3>
                <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                  Ev Sahibi
                </span>
              </div>
            </div>

            {/* Score Center */}
            <div className="text-center px-3 shrink-0">
              <div className="font-mono text-xl sm:text-2xl font-black text-slate-900 px-3 py-1 rounded-xl bg-white border border-slate-200 shadow-2xs inline-block">
                {match.home_score !== null && match.home_score !== undefined
                  ? `${match.home_score} - ${match.away_score}`
                  : 'VS'}
              </div>
              {meta.halfTimeScore && (
                <span className="text-[10px] font-mono text-slate-500 block mt-0.5">
                  İY: {meta.halfTimeScore.homeScore} - {meta.halfTimeScore.awayScore}
                </span>
              )}
              {isCompleted && ((match.home_xg ?? meta.home_xg) != null || (match.away_xg ?? meta.away_xg) != null) && (
                <div className="mt-0.5 flex items-center justify-center">
                  <span className="text-[9px] font-mono font-bold text-slate-600 bg-white border border-slate-200 px-2 py-0.5 rounded shadow-2xs inline-flex items-center gap-1">
                    <span className="text-slate-400">xG:</span>
                    {(match.home_xg ?? meta.home_xg) != null ? Number(match.home_xg ?? meta.home_xg).toFixed(2) : '-'} - {(match.away_xg ?? meta.away_xg) != null ? Number(match.away_xg ?? meta.away_xg).toFixed(2) : '-'}
                  </span>
                </div>
              )}
            </div>

            {/* Away Team */}
            <div className="flex items-center gap-2.5 flex-1 justify-end text-right min-w-0">
              <div className="min-w-0">
                <h3 className="font-bold text-sm sm:text-base text-slate-900 leading-tight truncate">
                  {awayTeam.name}
                </h3>
                <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                  Deplasman
                </span>
              </div>
              <img 
                src={awayTeam.badge} 
                alt={awayTeam.name} 
                className="w-8 h-8 sm:w-9 sm:h-9 object-contain shrink-0"
                onError={(e) => { e.target.src = '/badges/1.svg'; }}
              />
            </div>
          </div>

          <div className="text-center text-[11px] text-slate-500 mt-2 font-medium flex items-center justify-center gap-2">
            <span>{match.kickoff_label || meta.kickoff_label}</span>
            <span>•</span>
            <span className="truncate max-w-[200px]">{match.ground_name || meta.ground || 'Premier League Stadı'}</span>
            {meta.attendance && (
              <>
                <span>•</span>
                <span>{meta.attendance.toLocaleString()} Seyirci</span>
              </>
            )}
          </div>

          {/* Sub-tab Navigation */}
          <div className="flex flex-wrap items-center justify-center gap-2 mt-4 pt-3 border-t border-slate-100">
            {isCompleted && (
              <button
                onClick={() => setActiveTab('stats')}
                className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 ${
                  activeTab === 'stats'
                    ? 'bg-[#38003c] text-white shadow-sm'
                    : 'bg-slate-100 text-slate-600 hover:text-slate-900'
                }`}
              >
                <BarChart3 className="w-3.5 h-3.5" />
                <span>İstatistikler (Takım & Oyuncu)</span>
              </button>
            )}

            {!isCompleted && isPredictable && (
              <button
                onClick={() => setActiveTab('prediction')}
                className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 ${
                  activeTab === 'prediction'
                    ? 'bg-[#38003c] text-white shadow-sm'
                    : 'bg-slate-100 text-slate-600 hover:text-slate-900'
                }`}
              >
                <Sparkles className="w-3.5 h-3.5 text-[#00ff87]" />
                <span>Model Tahminleri</span>
              </button>
            )}

            {!isCompleted && !isPredictable && (
              <span className="px-3 py-1 rounded-xl text-[11px] font-bold bg-amber-50 border border-amber-200 text-amber-800 flex items-center gap-1.5" title="Model tahminleri takım formu ve sakatlık güncelliği için yalnızca mevcut haftanın maçlarında aktiftir">
                <AlertCircle className="w-3.5 h-3.5 text-amber-600" />
                <span>Tahminler {match.gameweek}. Haftada Açılacak</span>
              </span>
            )}

            <button
              onClick={() => setActiveTab('lineups')}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 ${
                activeTab === 'lineups'
                  ? 'bg-[#38003c] text-white shadow-sm'
                  : 'bg-slate-100 text-slate-600 hover:text-slate-900'
              }`}
            >
              <Users className="w-3.5 h-3.5" />
              <span>{isCompleted ? 'İlk 11 & Kadrolar' : 'Kadro Bilgisi'}</span>
            </button>

            {isCompleted && timeline.length > 0 && (
              <button
                onClick={() => setActiveTab('timeline')}
                className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 ${
                  activeTab === 'timeline'
                    ? 'bg-[#38003c] text-white shadow-sm'
                    : 'bg-slate-100 text-slate-600 hover:text-slate-900'
                }`}
              >
                <Zap className="w-3.5 h-3.5 text-amber-500" />
                <span>Maç Zaman Akışı ({timeline.length})</span>
              </button>
            )}

            {isCompleted && events.length > 0 && (
              <button
                onClick={() => setActiveTab('events')}
                className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 ${
                  activeTab === 'events'
                    ? 'bg-[#38003c] text-white shadow-sm'
                    : 'bg-slate-100 text-slate-600 hover:text-slate-900'
                }`}
              >
                <Clock className="w-3.5 h-3.5" />
                <span>Opta Olay Akışı ({events.length})</span>
              </button>
            )}
          </div>

        </div>

        {/* Modal Body */}
        <div className="p-4 sm:p-6 overflow-y-auto flex-1 space-y-6">
          
          {loading ? (
            <div className="py-20 text-center">
              <div className="w-8 h-8 border-3 border-[#38003c] border-t-transparent rounded-full animate-spin mx-auto mb-3" />
              <p className="text-xs font-bold text-slate-700">İstatistikler ve maç verileri yükleniyor...</p>
            </div>
          ) : activeTab === 'stats' ? (

            /* STATS TAB: Team & Player Match Performance */
            <div className="space-y-8">
              
              {/* 1. SECTION: Detailed Team Match Statistics (Sofascore Style) */}
              <div className="space-y-4">
                <div className="flex items-center justify-between pb-2 border-b border-slate-200">
                  <div className="flex items-center gap-2">
                    <BarChart3 className="w-4 h-4 text-[#38003c]" />
                    <h4 className="text-xs font-black uppercase tracking-wider text-slate-900">
                      Takım Karşılaştırmalı İstatistikleri & Mikro-Metrikler
                    </h4>
                  </div>
                  <span className="text-[11px] font-mono font-bold text-slate-500">
                    Premier League Maç Verisi
                  </span>
                </div>

                {teamStats.length === 0 ? (
                  <div className="py-8 text-center text-xs text-slate-500">
                    Bu karşılaşma henüz oynanmadığı için takım istatistikleri bulunmamaktadır.
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {teamStats.map((cat, catIdx) => (
                      <div 
                        key={catIdx} 
                        className="bg-slate-50 border border-slate-200 rounded-2xl p-4 space-y-3"
                      >
                        <h5 className="text-[11px] font-black uppercase tracking-wider text-slate-800 pb-1.5 border-b border-slate-200 flex items-center justify-between">
                          <span>{cat.category}</span>
                          <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-slate-200 text-slate-700">
                            {cat.items.length} Metrik
                          </span>
                        </h5>

                        <div className="space-y-2.5">
                          {cat.items.map((item, itemIdx) => {
                            const { homePct, awayPct } = calcBarWidths(item);
                            const hVal = item.home !== undefined ? item.home : '-';
                            const aVal = item.away !== undefined ? item.away : '-';
                            const suffix = item.suffix || '';
                            const isNotFound = (hVal === 'Not Found' && aVal === 'Not Found') || Boolean(item.notFound);
                            const isXg = Boolean(item.isXg || item.label?.includes('xG'));

                            return (
                              <div key={itemIdx} className={`space-y-1 text-xs ${isXg ? 'bg-rose-50/40 p-2 rounded-xl border border-rose-100/60' : ''}`}>
                                <div className="flex items-center justify-between text-[11px] font-semibold text-slate-700">
                                  <span className={`font-mono min-w-[36px] ${isXg ? 'text-rose-700 font-black' : 'font-bold text-slate-900'}`}>
                                    {hVal === 'Not Found' ? (
                                      <span className="text-slate-400 font-normal italic text-[10px]">Not Found</span>
                                    ) : (
                                      `${hVal}${suffix}`
                                    )}
                                  </span>
                                  <span className={`font-medium text-center truncate px-2 ${isXg ? 'text-rose-900 font-bold' : 'text-slate-600'}`}>
                                    {item.label}
                                  </span>
                                  <span className={`font-mono min-w-[36px] text-right ${isXg ? 'text-rose-700 font-black' : 'font-bold text-slate-900'}`}>
                                    {aVal === 'Not Found' ? (
                                      <span className="text-slate-400 font-normal italic text-[10px]">Not Found</span>
                                    ) : (
                                      `${aVal}${suffix}`
                                    )}
                                  </span>
                                </div>

                                {/* Comparison Dual Bar */}
                                {isNotFound ? (
                                  <div className="h-1.5 rounded-full overflow-hidden bg-slate-100 border border-dashed border-slate-200" title="Veri Bulunamadı" />
                                ) : (
                                  <div className="h-1.5 rounded-full overflow-hidden flex bg-slate-200 gap-0.5">
                                    <div 
                                      style={{ width: `${homePct}%` }}
                                      className={`h-full transition-all duration-500 rounded-l-full ${isXg ? 'bg-rose-600' : 'bg-[#38003c]'}`}
                                    />
                                    <div 
                                      style={{ width: `${awayPct}%` }}
                                      className={`h-full transition-all duration-500 rounded-r-full ${isXg ? 'bg-pink-600' : 'bg-emerald-600'}`}
                                    />
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* 2. SECTION: Player Match Scorecard Table */}
              <div className="space-y-4 pt-4 border-t border-slate-200">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-200">
                  <div className="flex items-center gap-2">
                    <Users className="w-4 h-4 text-[#38003c]" />
                    <h4 className="text-xs font-black uppercase tracking-wider text-slate-900">
                      Oyuncu Maç Performans Karnesi (Dakika, Şut, Faul, Ofsayt)
                    </h4>
                  </div>

                  {/* Home vs Away Player Selector */}
                  <div className="flex items-center bg-slate-100 p-1 rounded-xl border border-slate-200 gap-1">
                    <button
                      onClick={() => setPlayerTabSide('home')}
                      className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                        playerTabSide === 'home'
                          ? 'bg-[#38003c] text-white shadow-sm'
                          : 'text-slate-600 hover:text-slate-900'
                      }`}
                    >
                      <img src={homeTeam.badge} alt="" className="w-3.5 h-3.5 object-contain" />
                      <span>{homeTeam.short || homeTeam.name}</span>
                    </button>
                    <button
                      onClick={() => setPlayerTabSide('away')}
                      className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                        playerTabSide === 'away'
                          ? 'bg-[#38003c] text-white shadow-sm'
                          : 'text-slate-600 hover:text-slate-900'
                      }`}
                    >
                      <img src={awayTeam.badge} alt="" className="w-3.5 h-3.5 object-contain" />
                      <span>{awayTeam.short || awayTeam.name}</span>
                    </button>
                  </div>
                </div>

                {/* Player Table */}
                {(!playerStats[playerTabSide] || playerStats[playerTabSide].length === 0) ? (
                  <div className="py-8 text-center text-xs text-slate-500">
                    Bu takım için oyuncu maç istatistiği bulunamadı.
                  </div>
                ) : (
                  <div className="overflow-x-auto rounded-2xl border border-slate-200 shadow-sm">
                    <table className="w-full text-left text-xs font-medium border-collapse min-w-[700px]">
                      <thead>
                        <tr className="bg-slate-100 text-slate-700 text-[11px] font-bold border-b border-slate-200">
                          <th className="py-2.5 px-3 text-center">#</th>
                          <th className="py-2.5 px-3">Oyuncu</th>
                          <th className="py-2.5 px-2 text-center">Mevki</th>
                          <th className="py-2.5 px-2 text-center">Süre</th>
                          <th className="py-2.5 px-2 text-center">Gol</th>
                          <th className="py-2.5 px-2 text-center">Asist</th>
                          <th className="py-2.5 px-2 text-center">Şut (İsb)</th>
                          <th className="py-2.5 px-2 text-center">Faul Yaptı</th>
                          <th className="py-2.5 px-2 text-center">Faul Aldı</th>
                          <th className="py-2.5 px-2 text-center">Ofsayt</th>
                          <th className="py-2.5 px-2 text-center">Kart</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 bg-white">
                        {playerStats[playerTabSide].map((p, idx) => (
                          <tr key={p.id || idx} className="hover:bg-slate-50/80 transition-colors">
                            <td className="py-2.5 px-3 text-center font-mono font-bold text-slate-500">
                              {p.shirt || '-'}
                            </td>
                            <td className="py-2.5 px-3 font-bold text-slate-900">
                              <div className="flex items-center gap-2.5">
                                <PlayerAvatar 
                                  photoUrl={p.photo_url} 
                                  name={p.name} 
                                  shirt={p.shirt} 
                                  fallback="initials" 
                                  size="w-7 h-7 text-[10px]" 
                                  className="shrink-0" 
                                />
                                <div className="min-w-0">
                                  <div className="flex items-center gap-1">
                                    <span className="truncate">{p.name}</span>
                                    {p.captain && (
                                      <span className="text-[9px] font-black px-1 rounded bg-amber-200 text-amber-900 shrink-0">
                                        C
                                      </span>
                                    )}
                                  </div>
                                  {!p.is_starter && (
                                    <span className="text-[9px] text-purple-700 font-mono block">
                                      Yedek (Sonradan Girdi)
                                    </span>
                                  )}
                                </div>
                              </div>
                            </td>
                            <td className="py-2.5 px-2 text-center">
                              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md border ${getPositionBadgeClass(p.position)}`}>
                                {formatPosition(p.position)}
                              </span>
                            </td>
                            <td className="py-2.5 px-2 text-center font-mono font-bold text-slate-800">
                              {p.minutes}'
                            </td>
                            <td className="py-2.5 px-2 text-center font-mono font-bold">
                              {p.goals > 0 ? (
                                <span className="text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                                  {p.goals}
                                </span>
                              ) : (
                                <span className="text-slate-300">0</span>
                              )}
                            </td>
                            <td className="py-2.5 px-2 text-center font-mono font-bold">
                              {p.assists > 0 ? (
                                <span className="text-purple-700 bg-purple-50 px-1.5 py-0.5 rounded border border-purple-200">
                                  {p.assists}
                                </span>
                              ) : (
                                <span className="text-slate-300">0</span>
                              )}
                            </td>
                            <td className="py-2.5 px-2 text-center font-mono font-bold text-slate-700">
                              {p.shots > 0 ? `${p.shots} (${p.shots_ontarget})` : <span className="text-slate-300">0</span>}
                            </td>
                            <td className="py-2.5 px-2 text-center font-mono font-bold">
                              {p.fouls_committed > 0 ? (
                                <span className="text-rose-700">{p.fouls_committed}</span>
                              ) : (
                                <span className="text-slate-300">0</span>
                              )}
                            </td>
                            <td className="py-2.5 px-2 text-center font-mono font-bold">
                              {p.fouls_won > 0 ? (
                                <span className="text-emerald-700">{p.fouls_won}</span>
                              ) : (
                                <span className="text-slate-300">0</span>
                              )}
                            </td>
                            <td className="py-2.5 px-2 text-center font-mono font-bold">
                              {p.offsides > 0 ? (
                                <span className="text-amber-700 font-black">{p.offsides}</span>
                              ) : (
                                <span className="text-slate-300">0</span>
                              )}
                            </td>
                            <td className="py-2.5 px-2 text-center">
                              {p.yellow_cards > 0 && (
                                <span className="inline-block w-2.5 h-3.5 bg-amber-400 rounded-[2px] shadow-xs mr-1 align-middle" title="Sarı Kart" />
                              )}
                              {p.red_cards > 0 && (
                                <span className="inline-block w-2.5 h-3.5 bg-rose-600 rounded-[2px] shadow-xs mr-1 align-middle" title="Kırmızı Kart" />
                              )}
                              {p.yellow_cards === 0 && p.red_cards === 0 && <span className="text-slate-300">—</span>}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

            </div>

          ) : (activeTab === 'prediction' && !isCompleted && isPredictable) ? (

            /* PREDICTION TAB: Tabbed, Clean & Basic */
            <div className="space-y-4 max-w-2xl mx-auto py-1">

              {loadingPrediction || !prediction ? (
                <div className="py-12 text-center">
                  <div className="w-6 h-6 border-2 border-slate-900 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                  <p className="text-xs font-semibold text-slate-700">Tahminler hesaplanıyor...</p>
                </div>
              ) : (
                <>
                  {/* Category Tabs */}
                  <div className="flex items-center justify-center gap-1.5 p-1 bg-slate-100 rounded-xl border border-slate-200">
                    <button
                      onClick={() => setPredSubTab('outcome')}
                      className={`flex-1 py-1.5 text-xs font-bold rounded-lg transition-all ${
                        predSubTab === 'outcome'
                          ? 'bg-white text-slate-900 shadow-xs'
                          : 'text-slate-600 hover:text-slate-900'
                      }`}
                    >
                      Maç Sonucu (1X2)
                    </button>
                    <button
                      onClick={() => setPredSubTab('goals')}
                      className={`flex-1 py-1.5 text-xs font-bold rounded-lg transition-all ${
                        predSubTab === 'goals'
                          ? 'bg-white text-slate-900 shadow-xs'
                          : 'text-slate-600 hover:text-slate-900'
                      }`}
                    >
                      Goller & Piyasalar
                    </button>
                    <button
                      onClick={() => setPredSubTab('stats')}
                      className={`flex-1 py-1.5 text-xs font-bold rounded-lg transition-all ${
                        predSubTab === 'stats'
                          ? 'bg-white text-slate-900 shadow-xs'
                          : 'text-slate-600 hover:text-slate-900'
                      }`}
                    >
                      Diğer İstatistikler
                    </button>
                  </div>

                  {/* TAB 1: MAÇ SONUCU (1X2) */}
                  {predSubTab === 'outcome' && (
                    <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 animate-fadeIn space-y-3">
                      <div className="flex items-center justify-between pb-2 border-b border-slate-200 text-xs">
                        <span className="font-bold text-slate-800">1X2 Olasılık Dağılımı</span>
                        <span className="font-semibold text-slate-600 bg-white px-2 py-0.5 rounded border border-slate-200">
                          Favori: {prediction.favorite_label}
                        </span>
                      </div>

                      <div className="grid grid-cols-3 gap-3 pt-1 text-center">
                        <div className="bg-white p-3 rounded-lg border border-slate-200">
                          <span className="text-xs font-semibold text-slate-600 truncate block">{homeTeam.name}</span>
                          <div className="text-2xl font-black font-mono text-slate-900 my-1">%{prediction.outcome.home_win_pct}</div>
                          <span className="text-[11px] text-slate-400">1 (Ev Sahibi)</span>
                        </div>

                        <div className="bg-white p-3 rounded-lg border border-slate-200">
                          <span className="text-xs font-semibold text-slate-600 block">Beraberlik</span>
                          <div className="text-2xl font-black font-mono text-slate-900 my-1">%{prediction.outcome.draw_pct}</div>
                          <span className="text-[11px] text-slate-400">X (Eşitlik)</span>
                        </div>

                        <div className="bg-white p-3 rounded-lg border border-slate-200">
                          <span className="text-xs font-semibold text-slate-600 truncate block">{awayTeam.name}</span>
                          <div className="text-2xl font-black font-mono text-slate-900 my-1">%{prediction.outcome.away_win_pct}</div>
                          <span className="text-[11px] text-slate-400">2 (Deplasman)</span>
                        </div>
                      </div>

                      <div className="h-1.5 rounded-full bg-slate-200 overflow-hidden flex mt-2">
                        <div style={{ width: `${prediction.outcome.home_win_pct}%` }} className="h-full bg-slate-900" />
                        <div style={{ width: `${prediction.outcome.draw_pct}%` }} className="h-full bg-slate-400" />
                        <div style={{ width: `${prediction.outcome.away_win_pct}%` }} className="h-full bg-emerald-600" />
                      </div>
                    </div>
                  )}

                  {/* TAB 2: GOLLER & PİYASALAR */}
                  {predSubTab === 'goals' && (
                    <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 animate-fadeIn space-y-3">
                      <div className="flex items-center justify-between pb-2 border-b border-slate-200 text-xs">
                        <span className="font-bold text-slate-800">Gol Beklentisi & İhtimaller</span>
                        <span className="font-mono text-slate-600">
                          Toplam Beklenen Gol: <strong className="text-slate-900 text-sm">{prediction.goals?.expected_total_goals || (Number(prediction.goals?.expected_home_goals || 1.4) + Number(prediction.goals?.expected_away_goals || 1.2)).toFixed(2)}</strong>
                        </span>
                      </div>

                      <div className="text-xs text-slate-600 flex justify-between px-1">
                        <span>{homeTeam.name}: <strong className="text-slate-900">{prediction.goals?.expected_home_goals || '1.4'}</strong> gol</span>
                        <span>{awayTeam.name}: <strong className="text-slate-900">{prediction.goals?.expected_away_goals || '1.2'}</strong> gol</span>
                      </div>

                      <div className="grid grid-cols-4 gap-2 pt-1 text-center">
                        <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                          <span className="text-[11px] text-slate-500 block">1.5 Üst</span>
                          <strong className="text-lg font-black font-mono text-slate-900">%{prediction.goals?.['over_1.5']?.pct || '75.0'}</strong>
                        </div>
                        <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                          <span className="text-[11px] text-slate-500 block">2.5 Üst</span>
                          <strong className="text-lg font-black font-mono text-slate-900">%{prediction.outcome?.over_2_5_goals_pct}</strong>
                        </div>
                        <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                          <span className="text-[11px] text-slate-500 block">3.5 Üst</span>
                          <strong className="text-lg font-black font-mono text-slate-900">%{prediction.goals?.['over_3.5']?.pct || '32.0'}</strong>
                        </div>
                        <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                          <span className="text-[11px] text-slate-500 block">KG Var</span>
                          <strong className="text-lg font-black font-mono text-slate-900">%{prediction.goals?.btts_pct || '55.0'}</strong>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* TAB 3: DİĞER İSTATİSTİKLER */}
                  {predSubTab === 'stats' && (
                    <div className="bg-white border border-slate-200 rounded-xl overflow-hidden divide-y divide-slate-100 text-xs animate-fadeIn">
                      
                      {/* Korner */}
                      <div className="p-3 flex items-center justify-between">
                        <div>
                          <span className="font-bold text-slate-900 block">Korner</span>
                          <span className="text-slate-500 text-[11px]">{homeTeam.short}: {prediction.corners.expected_home} • {awayTeam.short}: {prediction.corners.expected_away}</span>
                        </div>
                        <div className="text-right">
                          <span className="font-mono font-black text-slate-900 text-base">{prediction.corners.expected_total} korner</span>
                          <span className="text-slate-500 text-[11px] block">9.5 Üst: %{prediction.corners.prob_over_9_5_pct}</span>
                        </div>
                      </div>

                      {/* Kart & Hakem */}
                      <div className="p-3 flex items-center justify-between">
                        <div>
                          <span className="font-bold text-slate-900 block">Kart & Disiplin</span>
                          <span className="text-slate-500 text-[11px]">Hakem: {prediction.referee?.name || 'Belirtilmedi'} ({prediction.referee?.avg_cards || '4.0'} kart/m)</span>
                        </div>
                        <div className="text-right">
                          <span className="font-mono font-black text-slate-900 text-base">{prediction.cards?.expected_total || '4.2'} kart</span>
                          <span className="text-slate-500 text-[11px] block">3.5 Üst: %{prediction.cards?.prob_over_3_5_pct || '62.0'}</span>
                        </div>
                      </div>

                      {/* Şut & Kaleci */}
                      <div className="p-3 flex items-center justify-between">
                        <div>
                          <span className="font-bold text-slate-900 block">Şut & Kurtarış</span>
                          <span className="text-slate-500 text-[11px]">Kurtarış: {homeTeam.short} ({prediction.saves.expected_home}) • {awayTeam.short} ({prediction.saves.expected_away})</span>
                        </div>
                        <div className="text-right">
                          <span className="font-mono font-black text-slate-900 text-base">{prediction.shots?.expected_total || '26.0'} şut</span>
                          <span className="text-slate-500 text-[11px] block">{prediction.saves.expected_total} kaleci kurtarışı</span>
                        </div>
                      </div>

                      {/* Taç & Ofsayt */}
                      <div className="p-3 flex items-center justify-between">
                        <div>
                          <span className="font-bold text-slate-900 block">Taç & Ofsayt</span>
                          <span className="text-slate-500 text-[11px]">Taktik: {(prediction.offsides?.expected_total || 3.3) >= 3.6 ? 'Yüksek Savunma Hattı' : 'Derin Blok Savunma'}</span>
                        </div>
                        <div className="text-right">
                          <span className="font-mono font-black text-slate-900 text-base">{prediction.throws.expected_total} taç</span>
                          <span className="text-slate-500 text-[11px] block">{prediction.offsides?.expected_total || '3.3'} ofsayt</span>
                        </div>
                      </div>

                    </div>
                  )}
                </>
              )}

            </div>

          ) : activeTab === 'lineups' ? (
            
            /* LINEUPS TAB */
            <div className="space-y-6">
              {!homeLineup && !awayLineup ? (
                <div className="py-12 text-center text-xs text-slate-500 font-medium">
                  Bu maç için henüz resmi kadro verisi yayınlanmamış.
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  
                  {/* Home Team Lineup */}
                  <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 space-y-3">
                    <div className="flex items-center justify-between pb-2 border-b border-slate-200">
                      <div className="flex items-center gap-2">
                        <img src={homeTeam.badge} alt="" className="w-5 h-5 object-contain" />
                        <h4 className="font-bold text-xs text-slate-900">{homeTeam.name}</h4>
                      </div>
                      {homeLineup?.formation && (
                        <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-purple-100 text-[#38003c]">
                          Diziliş: {homeLineup.formation}
                        </span>
                      )}
                    </div>

                    <div className="space-y-1.5">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
                        Başlangıç 11'i ({homeLineup?.starters?.length || 0}) • Pozisyon Sıralı
                      </span>
                      {homeLineup?.starters?.map((p, idx) => (
                        <div 
                          key={p.id || idx}
                          className="flex items-center justify-between p-2 rounded-xl bg-white border border-slate-200/80 hover:border-purple-200 transition-colors text-xs"
                        >
                          <div className="flex items-center gap-2.5 min-w-0">
                            <PlayerAvatar 
                              photoUrl={p.photo_url} 
                              name={p.name} 
                              shirt={p.shirt || idx + 1} 
                              fallback="initials" 
                              size="w-7 h-7 text-[10px]" 
                              className="shrink-0" 
                            />
                            <span className="w-5 h-5 rounded-full bg-slate-100 border border-slate-300 flex items-center justify-center font-mono font-bold text-[10px] text-slate-800 shrink-0">
                              {p.shirt || idx + 1}
                            </span>
                            <span className="font-bold text-slate-900 truncate">{p.name}</span>
                            {p.captain && (
                              <span className="text-[9px] font-black px-1 rounded bg-amber-200 text-amber-900 shrink-0">
                                C
                              </span>
                            )}
                          </div>
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md border shrink-0 ${getPositionBadgeClass(p.position)}`}>
                            {formatPosition(p.position)}
                          </span>
                        </div>
                      ))}
                    </div>

                    {homeLineup?.substitutes?.length > 0 && (
                      <div className="pt-2 border-t border-slate-200 space-y-1.5">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
                          Yedekler ({homeLineup.substitutes.length})
                        </span>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                          {homeLineup.substitutes.map((sub, idx) => (
                            <div 
                              key={sub.id || idx}
                              className="flex items-center justify-between p-1.5 rounded-xl bg-white border border-slate-200 text-xs"
                            >
                              <div className="flex items-center gap-2 min-w-0">
                                <PlayerAvatar 
                                  photoUrl={sub.photo_url} 
                                  name={sub.name} 
                                  shirt={sub.shirt} 
                                  fallback="initials" 
                                  size="w-6 h-6 text-[9px]" 
                                  className="shrink-0" 
                                />
                                <span className="font-mono text-[10px] font-bold text-slate-500">#{sub.shirt}</span>
                                <span className="font-medium text-slate-800 truncate">{sub.name}</span>
                              </div>
                              <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border shrink-0 ${getPositionBadgeClass(sub.position)}`}>
                                {formatPosition(sub.position)}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Away Team Lineup */}
                  <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 space-y-3">
                    <div className="flex items-center justify-between pb-2 border-b border-slate-200">
                      <div className="flex items-center gap-2">
                        <img src={awayTeam.badge} alt="" className="w-5 h-5 object-contain" />
                        <h4 className="font-bold text-xs text-slate-900">{awayTeam.name}</h4>
                      </div>
                      {awayLineup?.formation && (
                        <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-purple-100 text-[#38003c]">
                          Diziliş: {awayLineup.formation}
                        </span>
                      )}
                    </div>

                    <div className="space-y-1.5">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
                        Başlangıç 11'i ({awayLineup?.starters?.length || 0}) • Pozisyon Sıralı
                      </span>
                      {awayLineup?.starters?.map((p, idx) => (
                        <div 
                          key={p.id || idx}
                          className="flex items-center justify-between p-2 rounded-xl bg-white border border-slate-200/80 hover:border-purple-200 transition-colors text-xs"
                        >
                          <div className="flex items-center gap-2.5 min-w-0">
                            <PlayerAvatar 
                              photoUrl={p.photo_url} 
                              name={p.name} 
                              shirt={p.shirt || idx + 1} 
                              fallback="initials" 
                              size="w-7 h-7 text-[10px]" 
                              className="shrink-0" 
                            />
                            <span className="w-5 h-5 rounded-full bg-slate-100 border border-slate-300 flex items-center justify-center font-mono font-bold text-[10px] text-slate-800 shrink-0">
                              {p.shirt || idx + 1}
                            </span>
                            <span className="font-bold text-slate-900 truncate">{p.name}</span>
                            {p.captain && (
                              <span className="text-[9px] font-black px-1 rounded bg-amber-200 text-amber-900 shrink-0">
                                C
                              </span>
                            )}
                          </div>
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md border shrink-0 ${getPositionBadgeClass(p.position)}`}>
                            {formatPosition(p.position)}
                          </span>
                        </div>
                      ))}
                    </div>

                    {awayLineup?.substitutes?.length > 0 && (
                      <div className="pt-2 border-t border-slate-200 space-y-1.5">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
                          Yedekler ({awayLineup.substitutes.length})
                        </span>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                          {awayLineup.substitutes.map((sub, idx) => (
                            <div 
                              key={sub.id || idx}
                              className="flex items-center justify-between p-1.5 rounded-xl bg-white border border-slate-200 text-xs"
                            >
                              <div className="flex items-center gap-2 min-w-0">
                                <PlayerAvatar 
                                  photoUrl={sub.photo_url} 
                                  name={sub.name} 
                                  shirt={sub.shirt} 
                                  fallback="initials" 
                                  size="w-6 h-6 text-[9px]" 
                                  className="shrink-0" 
                                />
                                <span className="font-mono text-[10px] font-bold text-slate-500">#{sub.shirt}</span>
                                <span className="font-medium text-slate-800 truncate">{sub.name}</span>
                              </div>
                              <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border shrink-0 ${getPositionBadgeClass(sub.position)}`}>
                                {formatPosition(sub.position)}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                </div>
              )}
            </div>

          ) : activeTab === 'timeline' ? (

            /* TIMELINE TAB: Key Match Moments */
            <div className="space-y-4 max-w-2xl mx-auto py-2">
              <div className="text-center pb-2 border-b border-slate-100">
                <h4 className="text-xs font-black uppercase tracking-wider text-slate-800">
                  Karşılaşma Zaman Akışı & Önemli Anlar
                </h4>
                <p className="text-[11px] text-slate-500">
                  Maç başlangıcı, goller, kartlar, oyuncu değişiklikleri ve devre sonları
                </p>
              </div>

              {timeline.length === 0 ? (
                <div className="py-12 text-center text-xs text-slate-500">
                  Bu karşılaşma için önemli anlar zaman akışı bulunamadı.
                </div>
              ) : (
                <div className="relative pl-6 sm:pl-8 space-y-4 before:content-[''] before:absolute before:left-3 sm:before:left-4 before:top-3 before:bottom-3 before:w-0.5 before:bg-slate-200">
                  {timeline.map((item, idx) => {
                    const isGoal = item.type === 'goal';
                    const isCard = item.type === 'yellow_card' || item.type === 'red_card';
                    const isSub = item.type === 'substitution';
                    const isPeriod = item.type === 'period_start' || item.type === 'period_end';

                    return (
                      <div key={idx} className="relative flex items-start gap-3 group">
                        
                        {/* Timeline Node Icon */}
                        <div className={`absolute -left-6 sm:-left-8 w-6 h-6 rounded-full flex items-center justify-center border-2 bg-white z-10 shadow-xs ${
                          isGoal ? 'border-emerald-500 text-emerald-600' :
                          item.type === 'red_card' ? 'border-rose-500 text-rose-600' :
                          item.type === 'yellow_card' ? 'border-amber-400 text-amber-500' :
                          isSub ? 'border-sky-500 text-sky-600' :
                          'border-purple-600 text-purple-700'
                        }`}>
                          {isGoal && <span className="text-xs">⚽</span>}
                          {item.type === 'yellow_card' && <span className="text-xs">🟨</span>}
                          {item.type === 'red_card' && <span className="text-xs">🟥</span>}
                          {isSub && <RefreshCw className="w-3 h-3 text-sky-600" />}
                          {isPeriod && <Clock className="w-3 h-3 text-purple-700" />}
                        </div>

                        {/* Content Card */}
                        <div className={`flex-1 p-3 rounded-2xl border transition-all text-xs ${
                          isGoal ? 'bg-emerald-50/70 border-emerald-200 shadow-xs' :
                          item.type === 'red_card' ? 'bg-rose-50/70 border-rose-200' :
                          item.type === 'yellow_card' ? 'bg-amber-50/60 border-amber-200' :
                          isSub ? 'bg-sky-50/50 border-sky-200' :
                          'bg-slate-50 border-slate-200'
                        }`}>
                          <div className="flex items-center justify-between gap-2 mb-1">
                            <span className="font-mono font-black text-slate-800 bg-white/80 border border-slate-200 px-2 py-0.5 rounded-md text-[11px]">
                              {item.minute}
                            </span>
                            {item.score && (
                              <span className="font-mono font-extrabold text-[#38003c] bg-white border border-slate-200 px-2 py-0.5 rounded-md text-xs shadow-2xs">
                                {item.score}
                              </span>
                            )}
                          </div>

                          {/* Goal Details */}
                          {isGoal && (
                            <div className="flex items-center gap-2.5 mt-2">
                              <PlayerAvatar 
                                photoUrl={item.photo_url} 
                                name={item.player_name} 
                                fallback="initials" 
                                size="w-9 h-9 text-xs" 
                                className="shrink-0" 
                              />
                              <div className="min-w-0">
                                <div className="flex items-center gap-1.5 font-bold text-slate-900 text-sm">
                                  <span>⚽ {item.player_name}</span>
                                  <span className="text-[10px] font-bold text-emerald-800 bg-emerald-100 px-1.5 py-0.2 rounded font-sans">
                                    {item.goal_type || 'Gol'}
                                  </span>
                                </div>
                                <div className="text-[11px] text-slate-500">
                                  <span>{item.team_name}</span>
                                  {item.assist_name && (
                                    <span className="text-slate-600 font-medium"> • Asist: <strong>{item.assist_name}</strong></span>
                                  )}
                                </div>
                              </div>
                            </div>
                          )}

                          {/* Card Details */}
                          {isCard && (
                            <div className="flex items-center gap-2.5 mt-1.5">
                              <PlayerAvatar 
                                photoUrl={item.photo_url} 
                                name={item.player_name} 
                                fallback="initials" 
                                size="w-8 h-8 text-xs" 
                                className="shrink-0" 
                              />
                              <div>
                                <span className="font-bold text-slate-900 block text-xs">
                                  {item.type === 'yellow_card' ? '🟨 Sarı Kart:' : '🟥 Kırmızı Kart:'} {item.player_name}
                                </span>
                                <span className="text-[11px] text-slate-500">{item.team_name}</span>
                              </div>
                            </div>
                          )}

                          {/* Substitution Details */}
                          {isSub && (
                            <div className="space-y-1 mt-1">
                              <span className="text-[10px] font-bold uppercase tracking-wider text-sky-800 block">
                                {item.team_name} Oyuncu Değişikliği
                              </span>
                              <div className="grid grid-cols-2 gap-2 pt-0.5">
                                <div className="flex items-center gap-2 bg-white/80 border border-emerald-100 p-1.5 rounded-xl">
                                  <PlayerAvatar 
                                    photoUrl={item.player_in_photo} 
                                    name={item.player_in_name} 
                                    fallback="initials" 
                                    size="w-7 h-7 text-[10px]" 
                                    className="shrink-0" 
                                  />
                                  <div className="min-w-0">
                                    <span className="text-[10px] font-bold text-emerald-700 block">GİREN</span>
                                    <strong className="text-slate-900 truncate block text-[11px]">{item.player_in_name}</strong>
                                  </div>
                                </div>
                                <div className="flex items-center gap-2 bg-white/80 border border-rose-100 p-1.5 rounded-xl">
                                  <PlayerAvatar 
                                    photoUrl={item.player_out_photo} 
                                    name={item.player_out_name} 
                                    fallback="initials" 
                                    size="w-7 h-7 text-[10px]" 
                                    className="shrink-0" 
                                  />
                                  <div className="min-w-0">
                                    <span className="text-[10px] font-bold text-rose-700 block">ÇIKAN</span>
                                    <strong className="text-slate-900 truncate block text-[11px]">{item.player_out_name}</strong>
                                  </div>
                                </div>
                              </div>
                            </div>
                          )}

                          {/* Period Start / End */}
                          {isPeriod && (
                            <div className="flex items-center justify-between text-xs py-0.5">
                              <span className="font-bold text-slate-800">{item.label}</span>
                              <span className="text-[11px] text-slate-500">{item.description}</span>
                            </div>
                          )}

                        </div>

                      </div>
                    );
                  })}
                </div>
              )}
            </div>

          ) : (

            /* EVENTS TAB */
            <div className="space-y-2.5">
              {events.length === 0 ? (
                <div className="py-12 text-center text-xs text-slate-500">
                  Bu karşılaşma için canlı olay kaydı bulunamadı.
                </div>
              ) : (
                events.map((ev, idx) => {
                  const min = ev.time?.label || ev.minute || '-';
                  const type = ev.type || ev.event_type || 'olay';
                  return (
                    <div
                      key={ev.id || idx}
                      className="flex items-start gap-3 p-3 rounded-xl bg-slate-50 hover:bg-slate-100/80 border border-slate-200 transition-colors text-xs"
                    >
                      <span className="font-mono font-black text-[#38003c] min-w-[32px] pt-0.5">
                        {min}'
                      </span>
                      <div className="w-6 h-6 rounded-lg bg-white border border-slate-200 flex items-center justify-center shrink-0">
                        {renderEventIcon(type)}
                      </div>
                      <div className="flex-1">
                        <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-purple-700 block mb-0.5">
                          {type}
                        </span>
                        <p className="text-slate-800 font-medium leading-relaxed">
                          {ev.text}
                        </p>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

          )}

        </div>

      </div>
    </div>
  );
}
