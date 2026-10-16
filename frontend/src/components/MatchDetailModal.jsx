import MatchModalStatsTab from './match-detail/MatchModalStatsTab';
import MatchOddsTab from './match-detail/MatchOddsTab';
import MatchModalLineupsTab from './match-detail/MatchModalLineupsTab';
import MatchTimelineTab from './match-detail/MatchTimelineTab';
import MatchPredictionTab from './match-detail/MatchPredictionTab';
import { handleTeamBadgeError } from '../utils/imageFallbacks';
import React, { useEffect, useState } from 'react';
import { 
  X, 
  Clock, 
  Users, 
  BarChart3, 
  Activity, 
  Shield, 
  Target,
  Flag,
  AlertCircle,
  Sparkles,
  RefreshCw,
  Zap,
  TrendingUp,
  RotateCw
} from 'lucide-react';
import { getTeam } from '../data/teams';
import { getCachedTeamData, setCachedTeamData } from '../utils/teamProfileCache';
import { getMatchDetails, getMatchOdds, getMatchPrediction } from '../services/matchService';

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
  const [oddsData, setOddsData] = useState([]);
  const [loadingOdds, setLoadingOdds] = useState(false);
  const [selectedBookmaker, setSelectedBookmaker] = useState('Bet365');
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
    getMatchDetails(match.match_id)
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
    getMatchPrediction(match.home_id, match.away_id, match?.match_id)
      .then(data => {
        setPrediction(data);
        setLoadingPrediction(false);
      })
      .catch(err => {
        console.error('Error fetching prediction:', err);
        setLoadingPrediction(false);
      });
  }, [match.home_id, match.away_id, isCompleted, isPredictable]);

  useEffect(() => {
    if (!match.match_id) return;
    setLoadingOdds(true);
    getMatchOdds(match.match_id)
      .then(data => {
        const list = data.odds || [];
        setOddsData(list);
        if (list.length > 0) {
          const hasBet365 = list.some(b => b.bookmaker === 'Bet365');
          setSelectedBookmaker(hasBet365 ? 'Bet365' : list[0].bookmaker);
        }
        setLoadingOdds(false);
      })
      .catch(err => {
        console.error('Error fetching odds:', err);
        setLoadingOdds(false);
      });
  }, [match.match_id]);

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
                onError={handleTeamBadgeError}
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
                onError={handleTeamBadgeError}
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

            {/* Bahis / Piyasa Oranları Tab */}
            {oddsData.length > 0 && (
              <button
                onClick={() => setActiveTab('odds')}
                className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 ${
                  activeTab === 'odds'
                    ? 'bg-[#38003c] text-white shadow-sm'
                    : 'bg-slate-100 text-slate-600 hover:text-slate-900'
                }`}
              >
                <TrendingUp className="w-3.5 h-3.5 text-emerald-500" />
                <span>Piyasa Oranları ({oddsData.length})</span>
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
            <MatchModalStatsTab
              teamStats={teamStats}
              homeTeam={homeTeam}
              awayTeam={awayTeam}
              calcBarWidths={calcBarWidths}
              playerStats={playerStats}
              playerTabSide={playerTabSide}
              setPlayerTabSide={setPlayerTabSide}
              formatPosition={formatPosition}
              getPositionBadgeClass={getPositionBadgeClass}
            />
          ) : (activeTab === 'prediction' && !isCompleted && isPredictable) ? (
            <MatchPredictionTab
              prediction={prediction}
              loadingPrediction={loadingPrediction}
              predSubTab={predSubTab}
              setPredSubTab={setPredSubTab}
              homeTeam={homeTeam}
              awayTeam={awayTeam}
              variant="modal"
            />
          ) : activeTab === 'lineups' ? (
            <MatchModalLineupsTab
              homeLineup={homeLineup}
              awayLineup={awayLineup}
              homeTeam={homeTeam}
              awayTeam={awayTeam}
              formatPosition={formatPosition}
              getPositionBadgeClass={getPositionBadgeClass}
            />
          ) : activeTab === 'timeline' ? (
            <MatchTimelineTab timeline={timeline} homeTeam={homeTeam} awayTeam={awayTeam} homeTeamId={match.home_id} />
           ) : activeTab === 'odds' ? (
            <MatchOddsTab
              loadingOdds={loadingOdds}
              oddsData={oddsData}
              selectedBookmaker={selectedBookmaker}
              setSelectedBookmaker={setSelectedBookmaker}
              homeTeam={homeTeam}
              awayTeam={awayTeam}
            />
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
