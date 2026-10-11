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
  Eye
} from 'lucide-react';
import { getTeam } from '../data/teams';

export default function MatchDetailModal({ match, onClose }) {
  const isCompleted = Boolean(
    match.status === 'COMPLETED' || 
    (match.home_score !== null && match.home_score !== undefined && match.home_score !== '')
  );
  const [activeTab, setActiveTab] = useState(isCompleted ? 'stats' : 'prediction');
  const [playerTabSide, setPlayerTabSide] = useState('home'); // 'home' or 'away'
  const [details, setDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [prediction, setPrediction] = useState(null);
  const [loadingPrediction, setLoadingPrediction] = useState(false);

  // If match is completed, NEVER show or allow prediction tab
  useEffect(() => {
    if (isCompleted && activeTab === 'prediction') {
      setActiveTab('stats');
    }
  }, [isCompleted, activeTab]);

  const homeTeam = getTeam(match.home_id, match.home_name);
  const awayTeam = getTeam(match.away_id, match.away_name);

  useEffect(() => {
    if (!match.match_id) return;
    setLoading(true);
    fetch(`/api/match/${match.match_id}/details`)
      .then(res => res.json())
      .then(data => {
        setDetails(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Error fetching match details:', err);
        setLoading(false);
      });
  }, [match.match_id]);

  useEffect(() => {
    // NEVER fetch prediction for completed matches
    if (isCompleted) return;
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
  }, [match.home_id, match.away_id, isCompleted]);

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
        
        {/* Header & Scoreboard */}
        <div className="p-5 sm:p-6 border-b border-slate-200 bg-gradient-to-b from-slate-50 to-white relative shrink-0">
          <button
            onClick={onClose}
            className="absolute top-5 right-5 p-2 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-500 hover:text-slate-900 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>

          <div className="flex items-center justify-between px-2 sm:px-6">
            
            {/* Home Team */}
            <div className="flex items-center gap-3 flex-1 min-w-0">
              <img 
                src={homeTeam.badge} 
                alt={homeTeam.name} 
                className="w-12 h-12 object-contain shrink-0"
                onError={(e) => { e.target.src = '/badges/1.svg'; }}
              />
              <div className="min-w-0">
                <h3 className="font-black text-base sm:text-lg text-slate-900 leading-tight truncate">
                  {homeTeam.name}
                </h3>
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                  Ev Sahibi
                </span>
              </div>
            </div>

            {/* Score */}
            <div className="text-center px-4 shrink-0">
              <div className="font-mono text-2xl sm:text-3xl font-black text-slate-900 px-4 py-1.5 rounded-2xl bg-slate-100 border border-slate-200">
                {match.home_score !== null && match.home_score !== undefined
                  ? `${match.home_score} - ${match.away_score}`
                  : 'VS'}
              </div>
              {meta.halfTimeScore && (
                <span className="text-[11px] font-mono text-slate-500 block mt-1">
                  İY: {meta.halfTimeScore.homeScore} - {meta.halfTimeScore.awayScore}
                </span>
              )}
            </div>

            {/* Away Team */}
            <div className="flex items-center gap-3 flex-1 justify-end text-right min-w-0">
              <div className="min-w-0">
                <h3 className="font-black text-base sm:text-lg text-slate-900 leading-tight truncate">
                  {awayTeam.name}
                </h3>
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                  Deplasman
                </span>
              </div>
              <img 
                src={awayTeam.badge} 
                alt={awayTeam.name} 
                className="w-12 h-12 object-contain shrink-0"
                onError={(e) => { e.target.src = '/badges/1.svg'; }}
              />
            </div>

          </div>

          <p className="text-center text-xs text-slate-500 mt-3 font-medium flex items-center justify-center gap-2">
            <span>{match.kickoff_label || meta.kickoff_label}</span>
            <span>•</span>
            <span>{match.ground_name || meta.ground || 'Premier League Stadı'}</span>
            {meta.attendance && (
              <>
                <span>•</span>
                <span>{meta.attendance.toLocaleString()} Seyirci</span>
              </>
            )}
          </p>

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

            {!isCompleted && (
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
                    Opta Canlı Maç Verisi
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

                            return (
                              <div key={itemIdx} className="space-y-1 text-xs">
                                <div className="flex items-center justify-between text-[11px] font-semibold text-slate-700">
                                  <span className="font-mono font-bold text-slate-900 min-w-[36px]">
                                    {hVal}{suffix}
                                  </span>
                                  <span className="text-slate-600 font-medium text-center truncate px-2">
                                    {item.label}
                                  </span>
                                  <span className="font-mono font-bold text-slate-900 min-w-[36px] text-right">
                                    {aVal}{suffix}
                                  </span>
                                </div>

                                {/* Comparison Dual Bar */}
                                <div className="h-1.5 rounded-full overflow-hidden flex bg-slate-200 gap-0.5">
                                  <div 
                                    style={{ width: `${homePct}%` }}
                                    className="h-full bg-[#38003c] transition-all duration-500 rounded-l-full"
                                  />
                                  <div 
                                    style={{ width: `${awayPct}%` }}
                                    className="h-full bg-emerald-600 transition-all duration-500 rounded-r-full"
                                  />
                                </div>
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
                            <td className="py-2.5 px-3 font-bold text-slate-900 flex items-center gap-1.5">
                              <span>{p.name}</span>
                              {p.captain && (
                                <span className="text-[9px] font-black px-1 rounded bg-amber-200 text-amber-900">
                                  C
                                </span>
                              )}
                              {!p.is_starter && (
                                <span className="text-[9px] font-bold px-1 rounded bg-sky-100 text-sky-800">
                                  Yedek
                                </span>
                              )}
                            </td>
                            <td className="py-2.5 px-2 text-center font-mono font-bold text-slate-600">
                              <span className="px-1.5 py-0.5 rounded bg-slate-100 text-[10px]">
                                {p.position || 'O'}
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

          ) : (activeTab === 'prediction' && !isCompleted) ? (

            /* PREDICTION TAB: Live Match Predictions & 5 Micro-Metric Models */
            <div className="space-y-6">

              {loadingPrediction || !prediction ? (
                <div className="py-20 text-center">
                  <div className="w-8 h-8 border-3 border-[#38003c] border-t-transparent rounded-full animate-spin mx-auto mb-3" />
                  <p className="text-xs font-bold text-slate-700">Model tahminleri hesaplanıyor...</p>
                </div>
              ) : (
                <>
                  {/* Outcome Probabilities Card */}
                  <div className="bg-slate-50 border border-slate-200 rounded-2xl p-5 space-y-4 shadow-xs">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Sparkles className="w-4 h-4 text-[#38003c]" />
                        <span className="text-xs font-black uppercase tracking-wider text-slate-800">
                          Karşılaşma Öngörüsü & 1X2 Olasılık Dağılımı
                        </span>
                      </div>
                      <span className="text-xs font-bold px-3 py-1 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200 font-mono">
                        {prediction.favorite_label}
                      </span>
                    </div>

                    {/* 1X2 Probabilities Bar */}
                    <div className="space-y-2">
                      <div className="flex justify-between text-xs font-bold">
                        <span className="text-slate-900">{homeTeam.short}: %{prediction.outcome.home_win_pct}</span>
                        <span className="text-slate-500">Beraberlik: %{prediction.outcome.draw_pct}</span>
                        <span className="text-slate-900">{awayTeam.short}: %{prediction.outcome.away_win_pct}</span>
                      </div>
                      <div className="h-3 rounded-full bg-slate-200 overflow-hidden flex">
                        <div 
                          style={{ width: `${prediction.outcome.home_win_pct}%` }} 
                          className="h-full bg-[#38003c] transition-all" 
                          title={`Ev Sahibi: %${prediction.outcome.home_win_pct}`}
                        />
                        <div 
                          style={{ width: `${prediction.outcome.draw_pct}%` }} 
                          className="h-full bg-slate-400 transition-all" 
                          title={`Beraberlik: %${prediction.outcome.draw_pct}`}
                        />
                        <div 
                          style={{ width: `${prediction.outcome.away_win_pct}%` }} 
                          className="h-full bg-emerald-500 transition-all" 
                          title={`Deplasman: %${prediction.outcome.away_win_pct}`}
                        />
                      </div>
                    </div>

                    <div className="pt-2 border-t border-slate-200/80 flex flex-wrap items-center justify-between text-xs gap-2">
                      <span className="text-slate-600 font-medium">2.5 Gol Üst Olasılığı: <strong className="text-rose-700 font-mono font-bold">%{prediction.outcome.over_2_5_goals_pct}</strong></span>
                      <span className="text-slate-500 font-medium">Model: <strong className="text-slate-800 font-mono">Multi-LGBM + XGBoost</strong></span>
                    </div>
                  </div>

                  {/* 5 Micro-Metric Models Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    
                    {/* Card 1: Corners */}
                    <div className="bg-white border border-slate-200 rounded-2xl p-4 space-y-3 shadow-xs hover:border-emerald-300 transition-all">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 text-emerald-700">
                          <Flag className="w-4 h-4" />
                          <span className="text-xs font-bold uppercase tracking-wider">Toplam Korner</span>
                        </div>
                        <span className="text-[10px] font-mono font-bold bg-emerald-50 text-emerald-800 px-2 py-0.5 rounded border border-emerald-200">
                          XGBoost
                        </span>
                      </div>
                      <div className="space-y-0.5">
                        <div className="flex items-baseline gap-1.5">
                          <span className="text-3xl font-black font-mono text-slate-900">{prediction.corners.expected_total}</span>
                          <span className="text-xs text-slate-500 font-medium">beklenen korner</span>
                        </div>
                        <p className="text-xs text-slate-600 font-medium">
                          {homeTeam.short}: <strong className="text-slate-900">{prediction.corners.expected_home}</strong> • {awayTeam.short}: <strong className="text-slate-900">{prediction.corners.expected_away}</strong>
                        </p>
                      </div>
                      <div className="pt-2 border-t border-slate-100 space-y-1 text-xs">
                        <div className="flex justify-between text-slate-600">
                          <span>9.5 Üst Olasılığı:</span>
                          <strong className="text-emerald-700 font-mono font-bold">%{prediction.corners.prob_over_9_5_pct}</strong>
                        </div>
                        <div className="flex justify-between text-slate-600">
                          <span>10.5 Üst:</span>
                          <strong className="text-slate-800 font-mono font-bold">%{prediction.corners.prob_over_10_5_pct}</strong>
                        </div>
                      </div>
                    </div>

                    {/* Card 2: Throws */}
                    <div className="bg-white border border-slate-200 rounded-2xl p-4 space-y-3 shadow-xs hover:border-sky-300 transition-all">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 text-sky-700">
                          <Activity className="w-4 h-4" />
                          <span className="text-xs font-bold uppercase tracking-wider">Taç Atışları</span>
                        </div>
                        <span className="text-[10px] font-mono font-bold bg-sky-50 text-sky-800 px-2 py-0.5 rounded border border-sky-200">
                          LightGBM
                        </span>
                      </div>
                      <div className="space-y-0.5">
                        <div className="flex items-baseline gap-1.5">
                          <span className="text-3xl font-black font-mono text-slate-900">{prediction.throws.expected_total}</span>
                          <span className="text-xs text-slate-500 font-medium">beklenen taç</span>
                        </div>
                        <p className="text-xs text-slate-600 font-medium">
                          {homeTeam.short}: <strong className="text-slate-900">{prediction.throws.expected_home}</strong> • {awayTeam.short}: <strong className="text-slate-900">{prediction.throws.expected_away}</strong>
                        </p>
                      </div>
                      <div className="pt-2 border-t border-slate-100 space-y-1 text-xs">
                        <div className="flex justify-between text-slate-600">
                          <span>33.5 Üst Olasılığı:</span>
                          <strong className="text-sky-700 font-mono font-bold">%{prediction.throws.prob_over_33_5_pct}</strong>
                        </div>
                        <div className="flex justify-between text-slate-600">
                          <span>36.5 Üst:</span>
                          <strong className="text-slate-800 font-mono font-bold">%{prediction.throws.prob_over_36_5_pct}</strong>
                        </div>
                      </div>
                    </div>

                    {/* Card 3: Saves */}
                    <div className="bg-white border border-slate-200 rounded-2xl p-4 space-y-3 shadow-xs hover:border-purple-300 transition-all">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 text-purple-700">
                          <Shield className="w-4 h-4" />
                          <span className="text-xs font-bold uppercase tracking-wider">Kaleci Kurtarışları</span>
                        </div>
                        <span className="text-[10px] font-mono font-bold bg-purple-50 text-purple-800 px-2 py-0.5 rounded border border-purple-200">
                          XGBoost
                        </span>
                      </div>
                      <div className="space-y-0.5">
                        <div className="flex items-baseline gap-1.5">
                          <span className="text-3xl font-black font-mono text-slate-900">{prediction.saves.expected_total}</span>
                          <span className="text-xs text-slate-500 font-medium">toplam kurtarış</span>
                        </div>
                        <p className="text-xs text-slate-600 font-medium">
                          Ev GK: <strong className="text-slate-900">{prediction.saves.expected_home}</strong> • Dep GK: <strong className="text-slate-900">{prediction.saves.expected_away}</strong>
                        </p>
                      </div>
                      <div className="pt-2 border-t border-slate-100 text-xs text-slate-600 flex justify-between">
                        <span>Kurtarış Baskısı:</span>
                        <strong className="text-purple-700 font-bold">
                          {prediction.saves.expected_away > prediction.saves.expected_home ? `${awayTeam.short} GK Yoğun` : `${homeTeam.short} GK Yoğun`}
                        </strong>
                      </div>
                    </div>

                    {/* Card 4: Offsides */}
                    <div className="bg-white border border-slate-200 rounded-2xl p-4 space-y-3 shadow-xs hover:border-amber-300 transition-all">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 text-amber-700">
                          <Eye className="w-4 h-4" />
                          <span className="text-xs font-bold uppercase tracking-wider">Yakalanılan Ofsayt</span>
                        </div>
                        <span className="text-[10px] font-mono font-bold bg-amber-50 text-amber-800 px-2 py-0.5 rounded border border-amber-200">
                          XGBoost + Poisson
                        </span>
                      </div>
                      <div className="space-y-0.5">
                        <div className="flex items-baseline gap-1.5">
                          <span className="text-3xl font-black font-mono text-slate-900">{prediction.offsides?.expected_total || '3.3'}</span>
                          <span className="text-xs text-slate-500 font-medium">beklenen ofsayt</span>
                        </div>
                        <p className="text-xs text-slate-600 font-medium">
                          {homeTeam.short}: <strong className="text-slate-900">{prediction.offsides?.expected_home || '1.7'}</strong> • {awayTeam.short}: <strong className="text-slate-900">{prediction.offsides?.expected_away || '1.6'}</strong>
                        </p>
                      </div>
                      <div className="pt-2 border-t border-slate-100 space-y-1 text-xs">
                        <div className="flex justify-between text-slate-600">
                          <span>3.5 Üst Olasılığı:</span>
                          <strong className="text-amber-700 font-mono font-bold">%{prediction.offsides?.prob_over_3_5_pct || '45.0'}</strong>
                        </div>
                        <div className="flex justify-between text-slate-600">
                          <span>Hat Analizi:</span>
                          <strong className="text-amber-800 font-bold">
                            {(prediction.offsides?.expected_total || 3.3) >= 3.6 ? 'Yüksek Çizgi / Tuzak' : 'Derin Blok'}
                          </strong>
                        </div>
                      </div>
                    </div>

                    {/* Card 5: Shots */}
                    <div className="bg-white border border-slate-200 rounded-2xl p-4 space-y-3 shadow-xs hover:border-rose-300 transition-all">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 text-rose-700">
                          <Target className="w-4 h-4" />
                          <span className="text-xs font-bold uppercase tracking-wider">Şut Hacmi & Tempo</span>
                        </div>
                        <span className="text-[10px] font-mono font-bold bg-rose-50 text-rose-800 px-2 py-0.5 rounded border border-rose-200">
                          Poisson / Opta
                        </span>
                      </div>
                      <div className="space-y-0.5">
                        <div className="flex items-baseline gap-1.5">
                          <span className="text-3xl font-black font-mono text-slate-900">{prediction.shots.expected_total}</span>
                          <span className="text-xs text-slate-500 font-medium">beklenen şut</span>
                        </div>
                        <p className="text-xs text-slate-600 font-medium">
                          Ortalama 9.1 isabetli şut beklentisi
                        </p>
                      </div>
                      <div className="pt-2 border-t border-slate-100 text-xs text-slate-600 flex justify-between">
                        <span>Tempo Öngörüsü:</span>
                        <strong className="text-rose-700 font-bold">
                          {prediction.outcome.over_2_5_goals_pct > 55 ? 'Açık & Tempolu' : 'Dengeli & Taktiksel'}
                        </strong>
                      </div>
                    </div>

                  </div>
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
                        Başlangıç 11'i ({homeLineup?.starters?.length || 0})
                      </span>
                      {homeLineup?.starters?.map((p, idx) => (
                        <div 
                          key={p.id || idx}
                          className="flex items-center justify-between p-2 rounded-xl bg-white border border-slate-200/80 text-xs"
                        >
                          <div className="flex items-center gap-2.5">
                            <span className="w-5 h-5 rounded-full bg-slate-100 border border-slate-300 flex items-center justify-center font-mono font-bold text-[10px] text-slate-800">
                              {p.shirt || idx + 1}
                            </span>
                            <span className="font-bold text-slate-900">{p.name}</span>
                            {p.captain && (
                              <span className="text-[9px] font-black px-1 rounded bg-amber-200 text-amber-900">
                                C
                              </span>
                            )}
                          </div>
                          <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">
                            {p.position || 'O'}
                          </span>
                        </div>
                      ))}
                    </div>

                    {homeLineup?.substitutes?.length > 0 && (
                      <div className="pt-2 border-t border-slate-200 space-y-1">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1">
                          Yedekler
                        </span>
                        <div className="flex flex-wrap gap-1.5">
                          {homeLineup.substitutes.map((sub, idx) => (
                            <span 
                              key={sub.id || idx}
                              className="text-[11px] px-2 py-1 rounded-lg bg-white border border-slate-200 text-slate-700 font-medium"
                            >
                              #{sub.shirt} {sub.name}
                            </span>
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
                        Başlangıç 11'i ({awayLineup?.starters?.length || 0})
                      </span>
                      {awayLineup?.starters?.map((p, idx) => (
                        <div 
                          key={p.id || idx}
                          className="flex items-center justify-between p-2 rounded-xl bg-white border border-slate-200/80 text-xs"
                        >
                          <div className="flex items-center gap-2.5">
                            <span className="w-5 h-5 rounded-full bg-slate-100 border border-slate-300 flex items-center justify-center font-mono font-bold text-[10px] text-slate-800">
                              {p.shirt || idx + 1}
                            </span>
                            <span className="font-bold text-slate-900">{p.name}</span>
                            {p.captain && (
                              <span className="text-[9px] font-black px-1 rounded bg-amber-200 text-amber-900">
                                C
                              </span>
                            )}
                          </div>
                          <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">
                            {p.position || 'O'}
                          </span>
                        </div>
                      ))}
                    </div>

                    {awayLineup?.substitutes?.length > 0 && (
                      <div className="pt-2 border-t border-slate-200 space-y-1">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1">
                          Yedekler
                        </span>
                        <div className="flex flex-wrap gap-1.5">
                          {awayLineup.substitutes.map((sub, idx) => (
                            <span 
                              key={sub.id || idx}
                              className="text-[11px] px-2 py-1 rounded-lg bg-white border border-slate-200 text-slate-700 font-medium"
                            >
                              #{sub.shirt} {sub.name}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

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
