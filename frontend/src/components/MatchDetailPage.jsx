import React, { useEffect, useState } from 'react';
import { 
  ArrowLeft,
  RotateCw, 
  Clock, 
  Users, 
  BarChart3, 
  Activity, 
  Shield, 
  Calendar, 
  MapPin, 
  Target,
  Flag,
  AlertCircle,
  Sparkles,
  Flame,
  CheckCircle2,
  Scale,
  CreditCard,
  Zap,
  ArrowRightLeft,
  Timer,
  X,
  TrendingUp,
  ExternalLink
} from 'lucide-react';
import { getTeam } from '../data/teams';
import { getCachedTeamData, setCachedTeamData } from '../utils/teamProfileCache';
import PlayerAvatar from './PlayerAvatar';
import PitchLineup from './PitchLineup';

function BallIcon({ className = "w-4 h-4" }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <path d="m12 2 2.5 4.5-2.5 4.5-2.5-4.5z" />
      <path d="M12 11 8.5 15.5l1.5 5.5h4l1.5-5.5z" />
      <path d="M2.5 10 7 11.5l1.5 4-5 1.5z" />
      <path d="M21.5 10 17 11.5l-1.5 4 5 1.5z" />
      <path d="M4.5 4 8 7l-1 4.5L2.5 10z" />
      <path d="M19.5 4 16 7l1 4.5L21.5 10z" />
    </svg>
  );
}

function PenaltyBallIcon({ className = "w-4 h-4" }) {
  return (
    <div className="relative inline-flex items-center justify-center">
      <BallIcon className={className} />
      <span className="absolute -bottom-1 -right-1 w-3 h-3 bg-emerald-600 text-white text-[8px] font-black font-mono rounded-full flex items-center justify-center shadow-xs">
        P
      </span>
    </div>
  );
}

function MissedPenaltyIcon({ className = "w-4 h-4" }) {
  return (
    <div className="relative inline-flex items-center justify-center text-rose-600">
      <BallIcon className={className} />
      <span className="absolute -bottom-1 -right-1 w-3 h-3 bg-rose-600 text-white text-[8px] font-black font-mono rounded-full flex items-center justify-center shadow-xs">
        ✕
      </span>
    </div>
  );
}

function YellowCardIcon({ className = "w-2.5 h-3.5" }) {
  return <span className={`${className} bg-amber-400 rounded-[2px] shadow-2xs inline-block`} title="Sarı Kart" />;
}

function RedCardIcon({ className = "w-2.5 h-3.5" }) {
  return <span className={`${className} bg-rose-600 rounded-[2px] shadow-2xs inline-block`} title="Kırmızı Kart" />;
}

export default function MatchDetailPage({ match, onBack, currentGameweek, selectedSeason }) {
  const isCompleted = Boolean(
    match?.status === 'COMPLETED' || 
    (match?.home_score !== null && match?.home_score !== undefined && match?.home_score !== '')
  );
  const isPredictable = !isCompleted && (
    currentGameweek ? Number(match?.gameweek) === Number(currentGameweek) : true
  );

  // Main tab: default to 'timeline' for completed matches as requested
  const [activeTab, setActiveTab] = useState(
    isCompleted ? 'timeline' : isPredictable ? 'prediction' : 'lineups'
  );
  const [details, setDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [prediction, setPrediction] = useState(null);
  const [loadingPrediction, setLoadingPrediction] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [teamManagers, setTeamManagers] = useState({});
  const [recentForm, setRecentForm] = useState({});

  // Modal for player match scorecard
  const [selectedPlayerModal, setSelectedPlayerModal] = useState(null);
  const [lineupViewMode, setLineupViewMode] = useState('pitch'); // 'pitch' | 'list'
  const [predSubTab, setPredSubTab] = useState('outcome'); // 'outcome', 'goals', 'stats'
  const [oddsData, setOddsData] = useState([]);
  const [loadingOdds, setLoadingOdds] = useState(false);
  const [selectedBookmaker, setSelectedBookmaker] = useState('Bet365');

  // If match is completed or not in current gameweek, never stay on prediction tab
  useEffect(() => {
    if ((isCompleted || !isPredictable) && activeTab === 'prediction') {
      setActiveTab(isCompleted ? 'timeline' : 'lineups');
    }
  }, [isCompleted, isPredictable, activeTab]);

  const homeTeam = getTeam(match?.home_id, match?.home_name);
  const awayTeam = getTeam(match?.away_id, match?.away_name);
  const homeManager = match?.home_manager || teamManagers[String(match?.home_id)];
  const awayManager = match?.away_manager || teamManagers[String(match?.away_id)];

  useEffect(() => {
    let cancelled = false;
    const season = selectedSeason || match?.season || '2026_27';
    fetch(`/api/teams/staff?season=${encodeURIComponent(season)}`)
      .then(res => res.ok ? res.json() : { managers: {} })
      .then(data => {
        if (!cancelled) setTeamManagers(data.managers || {});
      })
      .catch(err => {
        console.error('Error fetching match team managers:', err);
        if (!cancelled) setTeamManagers({});
      });
    return () => { cancelled = true; };
  }, [selectedSeason, match?.season]);

  useEffect(() => {
    let cancelled = false;
    setRecentForm({});
    if (!match?.match_id) return undefined;
    fetch(`/api/match/${match.match_id}/recent-form`)
      .then(res => res.ok ? res.json() : { form: {} })
      .then(data => {
        if (!cancelled) setRecentForm(data.form || {});
      })
      .catch(err => {
        console.error('Error fetching pre-match form:', err);
        if (!cancelled) setRecentForm({});
      });
    return () => { cancelled = true; };
  }, [match?.match_id]);

  const renderRecentForm = (teamId) => (recentForm[String(teamId)] || []).map((result, index) => {
    const colors = result === 'W'
      ? 'bg-emerald-500 text-white'
      : result === 'D'
      ? 'bg-slate-400 text-white'
      : 'bg-rose-500 text-white';
    const label = result === 'W' ? 'G' : result === 'D' ? 'B' : 'M';
    return (
      <span
        key={`${teamId}-${index}`}
        className={`w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-black ${colors}`}
        title={result === 'W' ? 'Galibiyet' : result === 'D' ? 'Beraberlik' : 'Mağlubiyet'}
      >
        {label}
      </span>
    );
  });

  // Fetch match details
  useEffect(() => {
    if (!match?.match_id) return;

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
  }, [match?.match_id, isCompleted, refreshKey]);

  // Fetch model predictions for upcoming current gameweek matches
  useEffect(() => {
    if (isCompleted || !isPredictable) return;
    if (!match?.home_id || !match?.away_id) return;
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
  }, [match?.home_id, match?.away_id, isCompleted, isPredictable]);

  // Fetch betting market odds
  useEffect(() => {
    if (!match?.match_id) return;
    setLoadingOdds(true);
    fetch(`/api/match/${match.match_id}/odds`)
      .then(res => res.json())
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
  }, [match?.match_id]);

  const lineups = details?.lineups || [];
  const homeLineup = lineups.find(l => l.team_id === match?.home_id) || lineups[0];
  const awayLineup = lineups.find(l => l.team_id === match?.away_id) || lineups[1];
  const teamStats = details?.team_stats || [];
  const playerStats = details?.player_stats || { home: [], away: [] };
  const events = details?.events || [];
  const meta = details?.metadata || {};
  const timeline = details?.timeline || [];
  const goalEvents = timeline.filter(item => item.type === 'goal');
  const homeGoals = goalEvents.filter(item => Number(item.team_id) === Number(match?.home_id));
  const awayGoals = goalEvents.filter(item => Number(item.team_id) === Number(match?.away_id));

  // Red card calculation for home and away teams
  const getTeamRedCardCount = (side) => {
    // 1. From teamStats if available
    if (teamStats && teamStats.length > 0) {
      for (const cat of teamStats) {
        const redItem = cat.items?.find(it => it.label === 'Kırmızı Kart');
        if (redItem) {
          const val = Number(side === 'home' ? redItem.home : redItem.away);
          if (!isNaN(val) && val > 0) return val;
        }
      }
    }
    // 2. From timeline
    const targetId = side === 'home' ? match?.home_id : match?.away_id;
    const targetName = side === 'home' ? homeTeam.name : awayTeam.name;
    const fromTimeline = (timeline || []).filter(
      item => item.type === 'red_card' && (
        (targetId && Number(item.team_id) === Number(targetId)) ||
        (targetName && item.team_name && item.team_name.toLowerCase().includes(targetName.toLowerCase()))
      )
    ).length;
    if (fromTimeline > 0) return fromTimeline;

    // 3. From player stats
    const players = playerStats?.[side] || [];
    const fromPlayers = players.reduce((sum, p) => sum + (Number(p.red_cards) || 0), 0);
    return fromPlayers;
  };

  const homeRedCards = getTeamRedCardCount('home');
  const awayRedCards = getTeamRedCardCount('away');

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

  // Group players by position line for enhanced display
  const groupPlayersByPosition = (players = []) => {
    const groups = {
      GK: [],
      DEF: [],
      MID: [],
      FWD: []
    };

    players.forEach(p => {
      const pos = String(p.position || '').toUpperCase();
      if (['G', 'GK', 'GOALKEEPER'].includes(pos)) {
        groups.GK.push(p);
      } else if (['D', 'DEF', 'DEFENDER', 'CB', 'LB', 'RB', 'LWB', 'RWB'].includes(pos)) {
        groups.DEF.push(p);
      } else if (['M', 'MID', 'MIDFIELDER', 'CM', 'DM', 'AM', 'LM', 'RM'].includes(pos)) {
        groups.MID.push(p);
      } else {
        groups.FWD.push(p);
      }
    });

    return [
      { key: 'GK', label: 'Kaleci', list: groups.GK },
      { key: 'DEF', label: 'Savunma Hattı', list: groups.DEF },
      { key: 'MID', label: 'Orta Saha', list: groups.MID },
      { key: 'FWD', label: 'Hücum Hattı', list: groups.FWD },
    ].filter(g => g.list.length > 0);
  };

  const handlePlayerClick = (player, side) => {
    const list = playerStats?.[side] || [];
    const statsObj = list.find(p => String(p.id) === String(player.id)) || {
      ...player,
      minutes: player.is_starter ? 90 : 0,
      goals: 0,
      assists: 0,
      shots: 0,
      shots_ontarget: 0,
      fouls_committed: 0,
      fouls_won: 0,
      offsides: 0,
      yellow_cards: 0,
      red_cards: 0,
    };
    setSelectedPlayerModal({
      player,
      stats: statsObj,
      team: side === 'home' ? homeTeam : awayTeam,
      side
    });
  };

  if (!match) return null;

  return (
    <div className="w-full space-y-6 pb-16 animate-fadeIn">
      
      {/* Top Navigation & Context Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-white p-3.5 sm:p-4 rounded-2xl border border-slate-200 shadow-xs">
        
        {/* Back Button & Breadcrumbs */}
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-100 hover:bg-[#38003c] text-slate-700 hover:text-white font-bold text-xs shadow-xs transition-all duration-200 cursor-pointer group"
          >
            <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
            <span>Fikstüre Dön</span>
          </button>

          <div className="hidden sm:flex items-center gap-2 text-xs text-slate-500 font-medium">
            <span className="font-bold text-slate-700">Premier League</span>
            <span>/</span>
            <span>{match.gameweek ? `${match.gameweek}. Hafta` : 'Maç Detayı'}</span>
            <span>/</span>
            <span className="font-bold text-slate-900">{homeTeam.short} vs {awayTeam.short}</span>
          </div>
        </div>

        {/* Right Action: Refresh & Status Pill */}
        <div className="flex items-center gap-2">
          {isCompleted ? (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold font-mono bg-emerald-50 text-emerald-700 border border-emerald-200">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
              <span>Tamamlandı</span>
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold font-mono bg-purple-50 text-purple-700 border border-purple-200">
              <Clock className="w-3.5 h-3.5 text-purple-600" />
              <span>{match.time_label || match.kickoff_label || 'Başlama Saati'}</span>
            </span>
          )}

          <button
            onClick={() => setRefreshKey(k => k + 1)}
            title="Maç verilerini sunucudan yenile"
            className="p-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-600 hover:text-slate-900 transition-colors"
          >
            <RotateCw className={`w-4 h-4 ${loading ? 'animate-spin text-emerald-600' : ''}`} />
          </button>
        </div>

      </div>

      {/* Hero Scoreboard Banner: Compact & Balanced */}
      <div className="bg-white border border-slate-200 shadow-2xs rounded-2xl p-4 sm:p-6 text-slate-900 relative">
        <div className="relative z-10 flex flex-col md:flex-row items-center justify-between gap-4 sm:gap-6">
          
          {/* Home Team */}
          <div className="flex items-center gap-3 sm:gap-4 flex-1 w-full md:w-auto">
            <div className="relative flex items-center gap-2 shrink-0">
              <img 
                src={homeTeam.badge} 
                alt={homeTeam.name} 
                className="w-10 h-10 sm:w-12 sm:h-12 object-contain drop-shadow-xs shrink-0"
                onError={(e) => { e.target.src = '/badges/1.svg'; }}
              />
              {/* Home Team Red Card Badge */}
              {homeRedCards > 0 && (
                <div 
                  className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-rose-50 border border-rose-300 shadow-xs" 
                  title={`${homeTeam.name} - ${homeRedCards} Kırmızı Kart`}
                >
                  <RedCardIcon className="w-3 h-4" />
                  {homeRedCards > 1 && (
                    <span className="text-xs font-mono font-black text-rose-700">x{homeRedCards}</span>
                  )}
                </div>
              )}
            </div>
            <div className="min-w-0">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
                Ev Sahibi
              </span>
              <h2 className="text-lg sm:text-xl md:text-2xl font-black text-slate-900 tracking-tight leading-tight truncate">
                {homeTeam.name}
              </h2>
              {homeManager && (
                <p className="text-xs text-slate-500 font-medium truncate">TD: {homeManager}</p>
              )}
              <div className="mt-1 flex items-center gap-1" aria-label={`${homeTeam.name} maç öncesi son 5 maç formu`}>
                {renderRecentForm(match?.home_id)}
              </div>
            </div>
          </div>

          {/* Center Scoreboard / Time Display */}
          <div className="flex flex-col items-center justify-center shrink-0 px-3 py-1 text-center">
            
            {/* Score or VS Badge */}
            <div className="flex items-center gap-2">
              {isCompleted ? (
                <div className="font-mono text-3xl sm:text-4xl font-black text-slate-900 px-4 py-1 rounded-xl bg-slate-100 border border-slate-200 shadow-2xs tracking-tight">
                  {match.home_score} - {match.away_score}
                </div>
              ) : (
                <div className="font-mono text-xl sm:text-2xl font-black text-slate-900 px-4 py-1 rounded-xl bg-slate-100 border border-slate-200 shadow-2xs tracking-widest">
                  VS
                </div>
              )}
            </div>

            {/* Halftime score */}
            {isCompleted && meta.halfTimeScore?.homeScore != null && meta.halfTimeScore?.awayScore != null && (
              <span className="text-[11px] font-mono text-slate-500 mt-1 font-bold">
                İY {meta.halfTimeScore.homeScore} - {meta.halfTimeScore.awayScore}
              </span>
            )}

            {/* xG Metric Pill */}
            {isCompleted && (
              <div className="mt-2">
                {((match.home_xg ?? meta.home_xg) != null || (match.away_xg ?? meta.away_xg) != null) ? (
                  <span className="text-xs font-mono font-bold text-rose-700 bg-rose-50 border border-rose-200 px-3 py-0.5 rounded-full inline-flex items-center gap-1.5 shadow-2xs">
                    <span className="text-[10px] font-sans font-bold text-rose-500 uppercase tracking-wider">xG:</span>
                    {(match.home_xg ?? meta.home_xg) != null ? Number(match.home_xg ?? meta.home_xg).toFixed(2) : '-'} - {(match.away_xg ?? meta.away_xg) != null ? Number(match.away_xg ?? meta.away_xg).toFixed(2) : '-'}
                  </span>
                ) : (
                  <span className="text-[11px] font-mono text-slate-400 italic">
                    xG: Not Found
                  </span>
                )}
              </div>
            )}

          </div>

          {/* Away Team */}
          <div className="flex items-center justify-end gap-3 sm:gap-4 flex-1 w-full md:w-auto text-right">
            <div className="min-w-0">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
                Deplasman
              </span>
              <h2 className="text-lg sm:text-xl md:text-2xl font-black text-slate-900 tracking-tight leading-tight truncate">
                {awayTeam.name}
              </h2>
              {awayManager && (
                <p className="text-xs text-slate-500 font-medium truncate">TD: {awayManager}</p>
              )}
              <div className="mt-1 flex items-center gap-1 justify-end" aria-label={`${awayTeam.name} maç öncesi son 5 maç formu`}>
                {renderRecentForm(match?.away_id)}
              </div>
            </div>
            <div className="relative flex items-center gap-2 shrink-0">
              {/* Away Team Red Card Badge */}
              {awayRedCards > 0 && (
                <div 
                  className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-rose-50 border border-rose-300 shadow-xs" 
                  title={`${awayTeam.name} - ${awayRedCards} Kırmızı Kart`}
                >
                  <RedCardIcon className="w-3 h-4" />
                  {awayRedCards > 1 && (
                    <span className="text-xs font-mono font-black text-rose-700">x{awayRedCards}</span>
                  )}
                </div>
              )}
              <img 
                src={awayTeam.badge} 
                alt={awayTeam.name} 
                className="w-10 h-10 sm:w-12 sm:h-12 object-contain drop-shadow-xs shrink-0"
                onError={(e) => { e.target.src = '/badges/1.svg'; }}
              />
            </div>
          </div>

        </div>

        {isCompleted && (homeGoals.length > 0 || awayGoals.length > 0) && (
          <div className="relative z-10 mt-5 border-t border-slate-100 pt-4">
            <div className="grid grid-cols-2 gap-4">
              {[{ goals: homeGoals, align: 'text-left' }, { goals: awayGoals, align: 'text-right' }].map((side, sideIndex) => (
                <div key={sideIndex} className={`min-w-0 space-y-1 ${side.align}`}>
                  {side.goals.map((goal, index) => (
                    <p key={`${goal.minute}-${goal.player_id || index}`} className="text-[10px] sm:text-xs leading-4 text-slate-600 truncate">
                      <span className="font-bold text-slate-800">{goal.minute}</span>{' '}
                      {goal.player_name || 'Bilinmeyen Oyuncu'}{goal.is_own_goal ? ' (KK)' : ''}
                    </p>
                  ))}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Hero Footer Meta Details (No emojis) */}
        <div className="mt-6 pt-4 border-t border-slate-100 flex flex-wrap items-center justify-center gap-5 sm:gap-8 text-xs text-slate-600 font-medium">
          <div className="flex items-center gap-1.5">
            <Calendar className="w-4 h-4 text-slate-400" />
            <span>{match.kickoff_label || meta.kickoff_label || match.time_label || 'Tarih Belirtilmedi'}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <MapPin className="w-4 h-4 text-slate-400" />
            <span>{match.ground_name || meta.ground || homeTeam.stadium || 'Premier League Stadı'}</span>
          </div>
          {(match.referee_name || meta.referee) && (
            <div className="flex items-center gap-1.5">
              <Scale className="w-4 h-4 text-slate-400" />
              <span>Hakem: <strong className="text-slate-900 font-bold">{match.referee_name || meta.referee}</strong></span>
            </div>
          )}
          {meta.attendance && (
            <div className="flex items-center gap-1.5">
              <Users className="w-4 h-4 text-slate-400" />
              <span>{Number(meta.attendance).toLocaleString()} Seyirci</span>
            </div>
          )}
        </div>

      </div>

      {/* Modern Navigation Tabs: Zaman Akışı is FIRST, NO EMOJIS! */}
      <div className="flex flex-wrap items-center gap-2 bg-white p-2 rounded-2xl border border-slate-200 shadow-xs">
        
        {/* Tab 1: Zaman Akışı (Main tab at the beginning) */}
        {isCompleted && (
          <button
            onClick={() => setActiveTab('timeline')}
            className={`px-4 py-2.5 rounded-xl text-xs font-bold transition-all flex items-center gap-2 cursor-pointer ${
              activeTab === 'timeline'
                ? 'bg-[#38003c] text-white shadow-sm'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
            }`}
          >
            <Clock className="w-4 h-4" />
            <span>Zaman Akışı {timeline.length > 0 ? `(${timeline.length})` : ''}</span>
          </button>
        )}

        {/* Tab 2: Kadrolar & Diziliş */}
        <button
          onClick={() => setActiveTab('lineups')}
          className={`px-4 py-2.5 rounded-xl text-xs font-bold transition-all flex items-center gap-2 cursor-pointer ${
            activeTab === 'lineups'
              ? 'bg-[#38003c] text-white shadow-sm'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
        >
          <Users className="w-4 h-4" />
          <span>{isCompleted ? 'İlk 11 & Kadrolar' : 'Kadro Bilgisi'}</span>
        </button>

        {/* Tab 3: Maç İstatistikleri */}
        {isCompleted && (
          <button
            onClick={() => setActiveTab('stats')}
            className={`px-4 py-2.5 rounded-xl text-xs font-bold transition-all flex items-center gap-2 cursor-pointer ${
              activeTab === 'stats'
                ? 'bg-[#38003c] text-white shadow-sm'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
            }`}
          >
            <BarChart3 className="w-4 h-4" />
            <span>Takım İstatistikleri</span>
          </button>
        )}

        {/* Tab 4: Model Tahminleri (only for unplayed matches) */}
        {!isCompleted && isPredictable && (
          <button
            onClick={() => setActiveTab('prediction')}
            className={`px-4 py-2.5 rounded-xl text-xs font-bold transition-all flex items-center gap-2 cursor-pointer ${
              activeTab === 'prediction'
                ? 'bg-[#38003c] text-white shadow-sm'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
            }`}
          >
            <Sparkles className="w-4 h-4" />
            <span>Model Tahminleri</span>
          </button>
        )}

        {!isCompleted && !isPredictable && (
          <span className="px-3 py-2 rounded-xl text-xs font-bold bg-amber-50 border border-amber-200 text-amber-800 flex items-center gap-1.5">
            <AlertCircle className="w-4 h-4 text-amber-600" />
            <span>Tahminler {match.gameweek}. Haftada Aktifleşir</span>
          </span>
        )}

        {/* Tab 5: Opta Olay Akışı */}
        {isCompleted && events.length > 0 && (
          <button
            onClick={() => setActiveTab('events')}
            className={`px-4 py-2.5 rounded-xl text-xs font-bold transition-all flex items-center gap-2 cursor-pointer ${
              activeTab === 'events'
                ? 'bg-[#38003c] text-white shadow-sm'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
            }`}
          >
            <Activity className="w-4 h-4" />
            <span>Opta Olay Günlüğü ({events.length})</span>
          </button>
        )}

        {/* Tab 6: Bahis & Piyasa Oranları */}
        {oddsData.length > 0 && (
          <button
            onClick={() => setActiveTab('odds')}
            className={`px-4 py-2.5 rounded-xl text-xs font-bold transition-all flex items-center gap-2 cursor-pointer ${
              activeTab === 'odds'
                ? 'bg-[#38003c] text-white shadow-sm'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
            }`}
          >
            <TrendingUp className="w-4 h-4 text-emerald-500" />
            <span>Piyasa Oranları ({oddsData.length})</span>
          </button>
        )}
      </div>

      {/* Main Tab Content Area */}
      <div className="bg-white rounded-3xl border border-slate-200 p-6 sm:p-8 shadow-xs">
        
        {loading ? (
          <div className="py-24 text-center">
            <div className="w-10 h-10 border-4 border-[#38003c] border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <p className="text-sm font-bold text-slate-800">Maç detayları yükleniyor...</p>
            <p className="text-xs text-slate-500 mt-1">Premier League API ve Opta veri akışı senkronize ediliyor</p>
          </div>
        ) : activeTab === 'timeline' ? (

          /* ================= TIMELINE TAB: Split Left (Home) vs Right (Away) ================= */
          <div className="space-y-6 max-w-5xl mx-auto py-2">
            
            {/* Header with team names */}
            <div className="grid grid-cols-2 text-center pb-4 border-b border-slate-200">
              <div className="flex items-center justify-center gap-2 pr-4 border-r border-slate-200">
                <img src={homeTeam.badge} alt="" className="w-5 h-5 object-contain" />
                <h4 className="text-xs sm:text-sm font-black text-slate-900 uppercase tracking-wider truncate">
                  {homeTeam.name}
                </h4>
              </div>
              <div className="flex items-center justify-center gap-2 pl-4">
                <h4 className="text-xs sm:text-sm font-black text-slate-900 uppercase tracking-wider truncate">
                  {awayTeam.name}
                </h4>
                <img src={awayTeam.badge} alt="" className="w-5 h-5 object-contain" />
              </div>
            </div>

            {timeline.length === 0 ? (
              <div className="py-16 text-center text-sm text-slate-500 font-medium">
                Bu karşılaşma için zaman akışı kaydı bulunamadı.
              </div>
            ) : (
              <div className="relative py-4 before:content-[''] before:absolute before:left-1/2 before:-translate-x-1/2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
                <div className="space-y-6">
                  {timeline.map((item, idx) => {
                    const isGoal = item.type === 'goal';
                    const isPenaltyGoal = isGoal && item.is_penalty;
                    const isOwnGoal = isGoal && item.is_own_goal;
                    const isMissedPenalty = item.type === 'penalty_missed';
                    const isYellowCard = item.type === 'yellow_card';
                    const isRedCard = item.type === 'red_card';
                    const isSub = item.type === 'substitution';
                    const isAddedTime = item.type === 'added_time';
                    const isPeriod = item.type === 'period_start' || item.type === 'period_end';

                    // Center Neutral Banners (Period start / end, added time)
                    if (isPeriod || isAddedTime) {
                      return (
                        <div key={idx} className="relative z-10 flex items-center justify-center my-4">
                          <div className="bg-slate-100 hover:bg-slate-200 border border-slate-300 text-slate-800 px-4 py-1.5 rounded-full shadow-2xs flex items-center gap-2.5 text-xs transition-colors">
                            {isAddedTime ? (
                              <Timer className="w-3.5 h-3.5 text-purple-700" />
                            ) : (
                              <Clock className="w-3.5 h-3.5 text-slate-700" />
                            )}
                            <span className="font-bold text-slate-900">
                              {item.label} {isAddedTime ? `(${item.description})` : ''}
                            </span>
                            {item.score && (
                              <span className="font-mono font-black text-slate-900 bg-white px-2 py-0.5 rounded border border-slate-200 text-xs">
                                {item.score}
                              </span>
                            )}
                            <span className="font-mono font-bold text-slate-500 text-[11px]">
                              {item.minute}
                            </span>
                          </div>
                        </div>
                      );
                    }

                    // Determine if Home or Away
                    const isHome = Boolean(
                      (item.team_id && Number(item.team_id) === Number(match?.home_id)) ||
                      (item.team_name && homeTeam.name && item.team_name.toLowerCase().includes(homeTeam.name.toLowerCase()))
                    );

                    const renderEventBadgeIcon = () => {
                      if (isPenaltyGoal) return <PenaltyBallIcon className="w-3.5 h-3.5 text-emerald-600" />;
                      if (isOwnGoal) return <BallIcon className="w-3.5 h-3.5 text-rose-600" />;
                      if (isGoal) return <BallIcon className="w-3.5 h-3.5 text-slate-900" />;
                      if (isMissedPenalty) return <MissedPenaltyIcon className="w-3.5 h-3.5 text-rose-600" />;
                      if (isYellowCard) return <YellowCardIcon className="w-2.5 h-3.5" />;
                      if (isRedCard) return <RedCardIcon className="w-2.5 h-3.5" />;
                      if (isSub) return <ArrowRightLeft className="w-3.5 h-3.5 text-slate-600" />;
                      return <Clock className="w-3.5 h-3.5 text-slate-500" />;
                    };

                    const renderCardContent = () => (
                      <div className="p-3 rounded-xl border border-slate-200 hover:border-slate-300 bg-white shadow-2xs transition-all text-xs">
                        {/* Goal */}
                        {isGoal && (
                          <div className={`flex items-center gap-2.5 ${isHome ? 'flex-row-reverse text-right' : 'flex-row text-left'}`}>
                            <PlayerAvatar 
                              photoUrl={item.photo_url} 
                              name={item.player_name} 
                              size="w-7 h-7 text-[10px]" 
                              className="shrink-0"
                            />
                            <div className="min-w-0 flex-1">
                              <div className={`flex items-center gap-1.5 font-bold text-slate-900 text-xs sm:text-sm ${isHome ? 'justify-end' : 'justify-start'}`}>
                                <span className="truncate">{item.player_name}</span>
                                {isPenaltyGoal && (
                                  <span className="text-[10px] font-mono font-bold text-emerald-800 bg-emerald-50 border border-emerald-200 px-1.5 py-0.2 rounded shrink-0">
                                    Penaltı
                                  </span>
                                )}
                                {isOwnGoal && (
                                  <span className="text-[10px] font-mono font-bold text-rose-800 bg-rose-50 border border-rose-200 px-1.5 py-0.2 rounded shrink-0">
                                    Kendi Kalesine
                                  </span>
                                )}
                              </div>
                              <div className="text-[11px] text-slate-500 mt-0.5">
                                {item.assist_name && (
                                  <span>Asist: <strong className="text-slate-700">{item.assist_name}</strong></span>
                                )}
                              </div>
                            </div>
                            {item.score && (
                              <span className="font-mono font-black text-slate-900 bg-slate-100 border border-slate-200 px-2.5 py-1 rounded-lg text-xs sm:text-sm shrink-0">
                                {item.score}
                              </span>
                            )}
                          </div>
                        )}

                        {/* Missed Penalty */}
                        {isMissedPenalty && (
                          <div className={`space-y-0.5 ${isHome ? 'text-right' : 'text-left'}`}>
                            <div className="font-bold text-rose-700 text-xs flex items-center gap-1.5">
                              <span>Kaçan Penaltı</span>
                              {item.player_name && <span className="text-slate-900">• {item.player_name}</span>}
                            </div>
                            <p className="text-[11px] text-slate-500 truncate">
                              {item.description}
                            </p>
                          </div>
                        )}

                        {/* Yellow Card or Red Card */}
                        {(isYellowCard || isRedCard) && (
                          <div className={`flex items-center gap-2.5 ${isHome ? 'flex-row-reverse text-right' : 'flex-row text-left'}`}>
                            <PlayerAvatar 
                              photoUrl={item.photo_url} 
                              name={item.player_name} 
                              size="w-7 h-7 text-[10px]" 
                              className="shrink-0"
                            />
                            <div className="min-w-0 flex-1">
                              <span className="font-bold text-slate-900 block truncate">
                                {item.player_name}
                              </span>
                              <span className="text-[10px] font-mono font-bold text-slate-500 uppercase">
                                {isYellowCard ? 'Sarı Kart' : 'Kırmızı Kart'}
                              </span>
                            </div>
                            <div className="shrink-0">
                              {isYellowCard ? <YellowCardIcon /> : <RedCardIcon />}
                            </div>
                          </div>
                        )}

                        {/* Substitution */}
                        {isSub && (
                          <div className={`space-y-1 ${isHome ? 'text-right' : 'text-left'}`}>
                            <div className={`flex items-center gap-1.5 text-xs ${isHome ? 'justify-end' : 'justify-start'}`}>
                              <span className="text-emerald-600 font-bold font-mono">▲</span>
                              <span className="font-bold text-slate-900 truncate">{item.player_in_name}</span>
                            </div>
                            <div className={`flex items-center gap-1.5 text-xs text-slate-500 ${isHome ? 'justify-end' : 'justify-start'}`}>
                              <span className="text-rose-500 font-bold font-mono">▼</span>
                              <span className="text-slate-600 truncate">{item.player_out_name}</span>
                            </div>
                          </div>
                        )}
                      </div>
                    );

                    return (
                      <div key={idx} className="relative grid grid-cols-2 gap-8 items-center">
                        
                        {/* Center Minute Marker & Icon on the line */}
                        <div className="absolute left-1/2 -translate-x-1/2 top-1/2 -translate-y-1/2 z-10 flex flex-col items-center">
                          <div className="w-8 h-8 rounded-full border-2 border-slate-200 bg-white flex items-center justify-center shadow-xs">
                            {renderEventBadgeIcon()}
                          </div>
                          <span className="font-mono font-black text-[10px] text-slate-600 bg-slate-100 border border-slate-200 px-1.5 py-0.2 rounded-md mt-0.5 shadow-2xs">
                            {item.minute}
                          </span>
                        </div>

                        {/* Left Side (Home Team) */}
                        <div className="pr-6">
                          {isHome ? renderCardContent() : <div />}
                        </div>

                        {/* Right Side (Away Team) */}
                        <div className="pl-6">
                          {!isHome ? renderCardContent() : <div />}
                        </div>

                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

        ) : activeTab === 'lineups' ? (

          /* ================= LINEUPS TAB: FotMob / SofaScore Tactical Pitch & Categorized List ================= */
          <div className="space-y-6">
            {!homeLineup && !awayLineup ? (
              <div className="py-16 text-center text-sm text-slate-500 font-medium">
                Bu maç için henüz resmi kadro veya ilk 11 verisi açıklanmamış.
              </div>
            ) : (
              <>
                {/* View Switcher Header: Taktik Saha vs Detaylı Liste */}
                <div className="flex items-center justify-between flex-wrap gap-3 pb-3 border-b border-slate-200">
                  <div className="flex items-center gap-2">
                    <Users className="w-5 h-5 text-[#38003c]" />
                    <h3 className="text-sm font-black text-slate-900">
                      İlk 11 & Kadrolar
                    </h3>
                    <span className="text-xs text-slate-500 font-medium hidden sm:inline">
                      · Taktik diziliş ve yedek kulübesi
                    </span>
                  </div>

                  {/* Segmented Control */}
                  <div className="flex items-center bg-slate-100 p-1 rounded-xl border border-slate-200 gap-1">
                    <button
                      type="button"
                      onClick={() => setLineupViewMode('pitch')}
                      className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                        lineupViewMode === 'pitch'
                          ? 'bg-[#38003c] text-white shadow-xs'
                          : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
                      }`}
                    >
                      Taktik Saha
                    </button>
                    <button
                      type="button"
                      onClick={() => setLineupViewMode('list')}
                      className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                        lineupViewMode === 'list'
                          ? 'bg-[#38003c] text-white shadow-xs'
                          : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
                      }`}
                    >
                      Detaylı Liste
                    </button>
                  </div>
                </div>

                {/* Conditional Rendering: Pitch View vs List View */}
                {lineupViewMode === 'pitch' ? (
                  <PitchLineup
                    homeLineup={homeLineup}
                    awayLineup={awayLineup}
                    homeTeam={homeTeam}
                    awayTeam={awayTeam}
                    playerStats={playerStats}
                    onPlayerClick={handlePlayerClick}
                  />
                ) : (
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                
                {/* Home Team Column */}
                <div className="space-y-6">
                  {/* Team Card Header */}
                  <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <img src={homeTeam.badge} alt="" className="w-8 h-8 object-contain shrink-0" />
                      <div>
                        <h4 className="font-black text-sm text-slate-900 leading-tight">{homeTeam.name}</h4>
                        <span className="text-[11px] font-bold text-slate-500">Ev Sahibi</span>
                      </div>
                    </div>
                    {homeLineup?.formation && (
                      <span className="text-xs font-mono font-black px-3 py-1 rounded-xl bg-purple-100 text-[#38003c] border border-purple-200">
                        {homeLineup.formation}
                      </span>
                    )}
                  </div>

                  {/* Starting XI Grouped By Position Lines */}
                  <div className="space-y-4">
                    <div className="flex items-center justify-between pb-1.5 border-b border-slate-200">
                      <span className="text-xs font-black uppercase tracking-wider text-slate-800">
                        Başlangıç 11'i ({homeLineup?.starters?.length || 0})
                      </span>
                      <span className="text-[10px] text-slate-500 font-medium">
                        İstatistik için oyuncuya tıklayın
                      </span>
                    </div>

                    {groupPlayersByPosition(homeLineup?.starters).map((group) => (
                      <div key={group.key} className="space-y-2">
                        <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-500 block px-1">
                          {group.label} ({group.list.length})
                        </span>
                        <div className="space-y-1.5">
                          {group.list.map((p, idx) => (
                            <div 
                              key={p.id || idx}
                              onClick={() => handlePlayerClick(p, 'home')}
                              className="flex items-center justify-between p-2.5 rounded-xl bg-white border border-slate-200/90 hover:border-[#38003c]/40 hover:bg-slate-50/80 transition-all cursor-pointer group shadow-2xs"
                              title={`${p.name} maç performansını görüntüle`}
                            >
                              <div className="flex items-center gap-3 min-w-0">
                                <PlayerAvatar 
                                  photoUrl={p.photo_url}
                                  name={p.name}
                                  shirt={p.shirt || idx + 1}
                                  fallback="initials"
                                  size="w-8 h-8 text-xs"
                                  className="shrink-0 group-hover:scale-105 transition-transform"
                                />
                                <span className="w-6 h-6 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center font-mono font-bold text-xs text-slate-800 shrink-0">
                                  {p.shirt || idx + 1}
                                </span>
                                <div className="min-w-0">
                                  <div className="flex items-center gap-1.5">
                                    <span className="font-bold text-slate-900 group-hover:text-[#38003c] transition-colors truncate text-xs sm:text-sm">
                                      {p.name}
                                    </span>
                                    {p.captain && (
                                      <span className="text-[9px] font-black px-1.5 py-0.2 rounded bg-amber-200 text-amber-900 shrink-0">
                                        KAPTAN
                                      </span>
                                    )}
                                  </div>
                                </div>
                              </div>
                              <div className="flex items-center gap-2 shrink-0">
                                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md border ${getPositionBadgeClass(p.position)}`}>
                                  {formatPosition(p.position)}
                                </span>
                                <ExternalLink className="w-3.5 h-3.5 text-slate-300 group-hover:text-slate-600 transition-colors" />
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Substitutes Bench */}
                  {homeLineup?.substitutes?.length > 0 && (
                    <div className="pt-4 border-t border-slate-200 space-y-2.5">
                      <span className="text-xs font-black uppercase tracking-wider text-slate-800 block">
                        Yedek Kulübesi ({homeLineup.substitutes.length})
                      </span>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {homeLineup.substitutes.map((sub, idx) => (
                          <div 
                            key={sub.id || idx}
                            onClick={() => handlePlayerClick(sub, 'home')}
                            className="flex items-center justify-between p-2 rounded-xl bg-white border border-slate-200 hover:border-slate-300 hover:bg-slate-50 transition-all cursor-pointer group text-xs shadow-2xs"
                            title={`${sub.name} maç performansını görüntüle`}
                          >
                            <div className="flex items-center gap-2 min-w-0">
                              <PlayerAvatar 
                                photoUrl={sub.photo_url}
                                name={sub.name}
                                shirt={sub.shirt}
                                fallback="initials"
                                size="w-6 h-6 text-[10px]"
                                className="shrink-0"
                              />
                              <span className="font-mono text-xs font-bold text-slate-500">#{sub.shirt}</span>
                              <span className="font-medium text-slate-800 truncate">{sub.name}</span>
                            </div>
                            <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded border shrink-0 ${getPositionBadgeClass(sub.position)}`}>
                              {formatPosition(sub.position)}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Away Team Column */}
                <div className="space-y-6">
                  {/* Team Card Header */}
                  <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <img src={awayTeam.badge} alt="" className="w-8 h-8 object-contain shrink-0" />
                      <div>
                        <h4 className="font-black text-sm text-slate-900 leading-tight">{awayTeam.name}</h4>
                        <span className="text-[11px] font-bold text-slate-500">Deplasman</span>
                      </div>
                    </div>
                    {awayLineup?.formation && (
                      <span className="text-xs font-mono font-black px-3 py-1 rounded-xl bg-purple-100 text-[#38003c] border border-purple-200">
                        {awayLineup.formation}
                      </span>
                    )}
                  </div>

                  {/* Starting XI Grouped By Position Lines */}
                  <div className="space-y-4">
                    <div className="flex items-center justify-between pb-1.5 border-b border-slate-200">
                      <span className="text-xs font-black uppercase tracking-wider text-slate-800">
                        Başlangıç 11'i ({awayLineup?.starters?.length || 0})
                      </span>
                      <span className="text-[10px] text-slate-500 font-medium">
                        İstatistik için oyuncuya tıklayın
                      </span>
                    </div>

                    {groupPlayersByPosition(awayLineup?.starters).map((group) => (
                      <div key={group.key} className="space-y-2">
                        <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-500 block px-1">
                          {group.label} ({group.list.length})
                        </span>
                        <div className="space-y-1.5">
                          {group.list.map((p, idx) => (
                            <div 
                              key={p.id || idx}
                              onClick={() => handlePlayerClick(p, 'away')}
                              className="flex items-center justify-between p-2.5 rounded-xl bg-white border border-slate-200/90 hover:border-[#38003c]/40 hover:bg-slate-50/80 transition-all cursor-pointer group shadow-2xs"
                              title={`${p.name} maç performansını görüntüle`}
                            >
                              <div className="flex items-center gap-3 min-w-0">
                                <PlayerAvatar 
                                  photoUrl={p.photo_url}
                                  name={p.name}
                                  shirt={p.shirt || idx + 1}
                                  fallback="initials"
                                  size="w-8 h-8 text-xs"
                                  className="shrink-0 group-hover:scale-105 transition-transform"
                                />
                                <span className="w-6 h-6 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center font-mono font-bold text-xs text-slate-800 shrink-0">
                                  {p.shirt || idx + 1}
                                </span>
                                <div className="min-w-0">
                                  <div className="flex items-center gap-1.5">
                                    <span className="font-bold text-slate-900 group-hover:text-[#38003c] transition-colors truncate text-xs sm:text-sm">
                                      {p.name}
                                    </span>
                                    {p.captain && (
                                      <span className="text-[9px] font-black px-1.5 py-0.2 rounded bg-amber-200 text-amber-900 shrink-0">
                                        KAPTAN
                                      </span>
                                    )}
                                  </div>
                                </div>
                              </div>
                              <div className="flex items-center gap-2 shrink-0">
                                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md border ${getPositionBadgeClass(p.position)}`}>
                                  {formatPosition(p.position)}
                                </span>
                                <ExternalLink className="w-3.5 h-3.5 text-slate-300 group-hover:text-slate-600 transition-colors" />
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Substitutes Bench */}
                  {awayLineup?.substitutes?.length > 0 && (
                    <div className="pt-4 border-t border-slate-200 space-y-2.5">
                      <span className="text-xs font-black uppercase tracking-wider text-slate-800 block">
                        Yedek Kulübesi ({awayLineup.substitutes.length})
                      </span>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {awayLineup.substitutes.map((sub, idx) => (
                          <div 
                            key={sub.id || idx}
                            onClick={() => handlePlayerClick(sub, 'away')}
                            className="flex items-center justify-between p-2 rounded-xl bg-white border border-slate-200 hover:border-slate-300 hover:bg-slate-50 transition-all cursor-pointer group text-xs shadow-2xs"
                            title={`${sub.name} maç performansını görüntüle`}
                          >
                            <div className="flex items-center gap-2 min-w-0">
                              <PlayerAvatar 
                                photoUrl={sub.photo_url}
                                name={sub.name}
                                shirt={sub.shirt}
                                fallback="initials"
                                size="w-6 h-6 text-[10px]"
                                className="shrink-0"
                              />
                              <span className="font-mono text-xs font-bold text-slate-500">#{sub.shirt}</span>
                              <span className="font-medium text-slate-800 truncate">{sub.name}</span>
                            </div>
                            <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded border shrink-0 ${getPositionBadgeClass(sub.position)}`}>
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
              </>
            )}
          </div>

        ) : activeTab === 'stats' ? (

          /* ================= STATS TAB: Team Comparison Only (Player table removed per user request) ================= */
          <div className="space-y-8">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-200">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-xl bg-slate-100 text-[#38003c]">
                  <BarChart3 className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-black uppercase tracking-wider text-slate-900">
                    Takım Karşılaştırmalı İstatistikleri
                  </h3>
                  <p className="text-xs text-slate-500">
                    İki takımın maç boyunca ürettiği tüm metrikler
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-4 text-xs font-bold font-mono">
                <span className="flex items-center gap-1.5 text-[#38003c]">
                  <span className="w-3 h-3 rounded-full bg-[#38003c]" />
                  {homeTeam.short}
                </span>
                <span className="flex items-center gap-1.5 text-emerald-700">
                  <span className="w-3 h-3 rounded-full bg-emerald-600" />
                  {awayTeam.short}
                </span>
              </div>
            </div>

            {teamStats.length === 0 ? (
              <div className="py-12 text-center text-sm text-slate-500 font-medium">
                Bu karşılaşma henüz oynanmadığı için takım istatistikleri bulunmamaktadır.
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {teamStats.map((cat, catIdx) => (
                  <div 
                    key={catIdx} 
                    className="bg-slate-50 border border-slate-200 rounded-2xl p-5 space-y-4 hover:border-slate-300 transition-colors"
                  >
                    <h4 className="text-xs font-black uppercase tracking-wider text-slate-800 pb-2 border-b border-slate-200 flex items-center justify-between">
                      <span>{cat.category}</span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-200 text-slate-700">
                        {cat.items.length} Metrik
                      </span>
                    </h4>

                    <div className="space-y-3">
                      {cat.items.map((item, itemIdx) => {
                        const { homePct, awayPct } = calcBarWidths(item);
                        const hVal = item.home !== undefined ? item.home : '-';
                        const aVal = item.away !== undefined ? item.away : '-';
                        const suffix = item.suffix || '';
                        const isNotFound = (hVal === 'Not Found' && aVal === 'Not Found') || Boolean(item.notFound);
                        const isXg = Boolean(item.isXg || item.label?.includes('xG'));

                        return (
                          <div key={itemIdx} className={`space-y-1.5 text-xs ${isXg ? 'bg-rose-50/60 p-2.5 rounded-xl border border-rose-200/80' : ''}`}>
                            <div className="flex items-center justify-between text-xs font-semibold text-slate-700">
                              <span className={`font-mono min-w-[40px] ${isXg ? 'text-rose-700 font-black text-sm' : 'font-bold text-slate-900'}`}>
                                {hVal === 'Not Found' ? (
                                  <span className="text-slate-400 font-normal italic text-[11px]">Yok</span>
                                ) : (
                                  `${hVal}${suffix}`
                                )}
                              </span>
                              <span className={`font-bold text-center truncate px-2 ${isXg ? 'text-rose-900 font-black' : 'text-slate-700'}`}>
                                {item.label}
                              </span>
                              <span className={`font-mono min-w-[40px] text-right ${isXg ? 'text-rose-700 font-black text-sm' : 'font-bold text-slate-900'}`}>
                                {aVal === 'Not Found' ? (
                                  <span className="text-slate-400 font-normal italic text-[11px]">Yok</span>
                                ) : (
                                  `${aVal}${suffix}`
                                )}
                              </span>
                            </div>

                            {/* Dual Bar */}
                            {isNotFound ? (
                              <div className="h-2 rounded-full overflow-hidden bg-slate-100 border border-dashed border-slate-200" title="Veri Bulunamadı" />
                            ) : (
                              <div className="h-2 rounded-full overflow-hidden flex bg-slate-200 gap-0.5">
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

        ) : activeTab === 'prediction' ? (

          /* PREDICTION TAB: Simple, Clean & Basic with Sub-Tabs */
          <div className="space-y-3 max-w-xl mx-auto py-2">

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

        ) : activeTab === 'odds' ? (
          
          /* ================= ODDS TAB (BAHİS / PİYASA ORANLARI) ================= */
          <div className="space-y-4 max-w-2xl mx-auto py-2">
            {loadingOdds ? (
              <div className="py-12 text-center">
                <div className="w-6 h-6 border-2 border-slate-900 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                <p className="text-xs font-semibold text-slate-700">Piyasa oranları yükleniyor...</p>
              </div>
            ) : oddsData.length === 0 ? (
              <div className="py-12 text-center bg-slate-50 border border-slate-200 rounded-xl p-6">
                <TrendingUp className="w-8 h-8 text-slate-400 mx-auto mb-2" />
                <p className="text-xs font-semibold text-slate-700">Bu karşılaşma için kaydedilmiş bahis piyasası oranı bulunmuyor.</p>
                <p className="text-[11px] text-slate-500 mt-1">Oranlar şu anda 2026/27 sezonunda tamamlanan maçlar için aktiftir.</p>
              </div>
            ) : (
              <>
                {/* Bookmaker Selector Tabs */}
                <div className="flex items-center gap-1.5 p-1 bg-slate-100 rounded-xl border border-slate-200 overflow-x-auto">
                  {oddsData.map((bm) => (
                    <button
                      key={bm.bookmaker}
                      onClick={() => setSelectedBookmaker(bm.bookmaker)}
                      className={`flex-1 min-w-[100px] py-1.5 px-3 text-xs font-bold rounded-lg transition-all text-center ${
                        selectedBookmaker === bm.bookmaker
                          ? 'bg-white text-slate-900 shadow-xs border border-slate-200/80'
                          : 'text-slate-600 hover:text-slate-900'
                      }`}
                    >
                      {bm.bookmaker}
                    </button>
                  ))}
                </div>

                {(() => {
                  const currentBm = oddsData.find(b => b.bookmaker === selectedBookmaker) || oddsData[0];
                  if (!currentBm) return null;

                  return (
                    <div className="space-y-3">
                      {/* 1X2 Kapanış Oranları */}
                      <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3">
                        <div className="flex items-center justify-between pb-2 border-b border-slate-200 text-xs">
                          <span className="font-bold text-slate-800">1X2 Maç Sonucu (Kapanış Oranları)</span>
                          <span className="font-semibold text-slate-600 bg-white px-2 py-0.5 rounded border border-slate-200">
                            {currentBm.bookmaker}
                          </span>
                        </div>

                        <div className="grid grid-cols-3 gap-3 pt-1 text-center">
                          <div className="bg-white p-3 rounded-lg border border-slate-200">
                            <span className="text-xs font-semibold text-slate-600 truncate block">{homeTeam.name}</span>
                            <div className="text-2xl font-black font-mono text-slate-900 my-1">
                              {currentBm.home_last_seen ? currentBm.home_last_seen.toFixed(2) : '-'}
                            </div>
                            <span className="text-[11px] text-slate-400">1 (Ev Sahibi)</span>
                            {currentBm.home_open && (
                              <span className="text-[10px] text-slate-400 block mt-0.5">Açılış: {currentBm.home_open.toFixed(2)}</span>
                            )}
                          </div>

                          <div className="bg-white p-3 rounded-lg border border-slate-200">
                            <span className="text-xs font-semibold text-slate-600 block">Beraberlik</span>
                            <div className="text-2xl font-black font-mono text-slate-900 my-1">
                              {currentBm.draw_last_seen ? currentBm.draw_last_seen.toFixed(2) : '-'}
                            </div>
                            <span className="text-[11px] text-slate-400">X (Eşitlik)</span>
                            {currentBm.draw_open && (
                              <span className="text-[10px] text-slate-400 block mt-0.5">Açılış: {currentBm.draw_open.toFixed(2)}</span>
                            )}
                          </div>

                          <div className="bg-white p-3 rounded-lg border border-slate-200">
                            <span className="text-xs font-semibold text-slate-600 truncate block">{awayTeam.name}</span>
                            <div className="text-2xl font-black font-mono text-slate-900 my-1">
                              {currentBm.away_last_seen ? currentBm.away_last_seen.toFixed(2) : '-'}
                            </div>
                            <span className="text-[11px] text-slate-400">2 (Deplasman)</span>
                            {currentBm.away_open && (
                              <span className="text-[10px] text-slate-400 block mt-0.5">Açılış: {currentBm.away_open.toFixed(2)}</span>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Gol & KG Piyasaları */}
                      <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3">
                        <div className="flex items-center justify-between pb-2 border-b border-slate-200 text-xs">
                          <span className="font-bold text-slate-800">Gol & Karşılıklı Skor Oranları</span>
                          <span className="text-[11px] text-slate-500">Piyasa Kapanışı</span>
                        </div>

                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 text-center">
                          <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                            <span className="text-[11px] text-slate-500 block">2.5 Gol Üst</span>
                            <strong className="text-lg font-black font-mono text-slate-900">
                              {currentBm.over_25_last_seen ? currentBm.over_25_last_seen.toFixed(2) : '-'}
                            </strong>
                            {currentBm.over_25_open && (
                              <span className="text-[10px] text-slate-400 block">Açılış: {currentBm.over_25_open.toFixed(2)}</span>
                            )}
                          </div>

                          <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                            <span className="text-[11px] text-slate-500 block">2.5 Gol Alt</span>
                            <strong className="text-lg font-black font-mono text-slate-900">
                              {currentBm.under_25_last_seen ? currentBm.under_25_last_seen.toFixed(2) : '-'}
                            </strong>
                            {currentBm.under_25_open && (
                              <span className="text-[10px] text-slate-400 block">Açılış: {currentBm.under_25_open.toFixed(2)}</span>
                            )}
                          </div>

                          <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                            <span className="text-[11px] text-slate-500 block">KG Var (Evet)</span>
                            <strong className="text-lg font-black font-mono text-slate-900">
                              {currentBm.btts_yes_last_seen ? currentBm.btts_yes_last_seen.toFixed(2) : '-'}
                            </strong>
                            {currentBm.btts_yes_open && (
                              <span className="text-[10px] text-slate-400 block">Açılış: {currentBm.btts_yes_open.toFixed(2)}</span>
                            )}
                          </div>

                          <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                            <span className="text-[11px] text-slate-500 block">KG Yok (Hayır)</span>
                            <strong className="text-lg font-black font-mono text-slate-900">
                              {currentBm.btts_no_last_seen ? currentBm.btts_no_last_seen.toFixed(2) : '-'}
                            </strong>
                            {currentBm.btts_no_open && (
                              <span className="text-[10px] text-slate-400 block">Açılış: {currentBm.btts_no_open.toFixed(2)}</span>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Korner & Kart Piyasaları (Varsa) */}
                      {(currentBm.corners_over_last_seen || currentBm.cards_over_last_seen) && (
                        <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3">
                          <div className="flex items-center justify-between pb-2 border-b border-slate-200 text-xs">
                            <span className="font-bold text-slate-800">Özel Bahis Pazarları (Korner & Kart)</span>
                            <span className="text-[11px] text-slate-500">Piyasa Çizgileri</span>
                          </div>

                          <div className="grid grid-cols-2 gap-3 pt-1">
                            {currentBm.corners_over_last_seen && (
                              <div className="bg-white p-3 rounded-lg border border-slate-200 flex items-center justify-between">
                                <div>
                                  <span className="text-xs font-bold text-slate-800 block">9.5 Korner</span>
                                  <span className="text-[11px] text-slate-500">Kapanış Çizgisi</span>
                                </div>
                                <div className="text-right">
                                  <span className="text-xs font-mono font-bold text-slate-900 block">Üst: {currentBm.corners_over_last_seen.toFixed(2)}</span>
                                  {currentBm.corners_under_last_seen && (
                                    <span className="text-[11px] font-mono text-slate-600 block">Alt: {currentBm.corners_under_last_seen.toFixed(2)}</span>
                                  )}
                                </div>
                              </div>
                            )}

                            {currentBm.cards_over_last_seen && (
                              <div className="bg-white p-3 rounded-lg border border-slate-200 flex items-center justify-between">
                                <div>
                                  <span className="text-xs font-bold text-slate-800 block">4.5 Kart</span>
                                  <span className="text-[11px] text-slate-500">Disiplin Pazarı</span>
                                </div>
                                <div className="text-right">
                                  <span className="text-xs font-mono font-bold text-slate-900 block">Üst: {currentBm.cards_over_last_seen.toFixed(2)}</span>
                                  {currentBm.cards_under_last_seen && (
                                    <span className="text-[11px] font-mono text-slate-600 block">Alt: {currentBm.cards_under_last_seen.toFixed(2)}</span>
                                  )}
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Tüm Bahis Şirketleri Karşılaştırma Tablosu */}
                      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden mt-3">
                        <div className="px-4 py-2.5 bg-slate-50 border-b border-slate-200 text-xs font-bold text-slate-800 flex items-center justify-between">
                          <span>Tüm Sağlayıcıların Kapanış Oranları</span>
                          <span className="text-[11px] font-normal text-slate-500">{oddsData.length} Sağlayıcı</span>
                        </div>
                        <div className="overflow-x-auto">
                          <table className="w-full text-xs text-left">
                            <thead className="bg-slate-50/50 text-[11px] text-slate-500 border-b border-slate-100">
                              <tr>
                                <th className="py-2 px-3 font-semibold">Bahis Şirketi</th>
                                <th className="py-2 px-3 font-semibold text-center">1 (Ev)</th>
                                <th className="py-2 px-3 font-semibold text-center">X (Eşitlik)</th>
                                <th className="py-2 px-3 font-semibold text-center">2 (Deplasman)</th>
                                <th className="py-2 px-3 font-semibold text-center">2.5 Üst</th>
                                <th className="py-2 px-3 font-semibold text-center">KG Var</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 font-mono">
                              {oddsData.map(b => (
                                <tr key={b.bookmaker} className={b.bookmaker === selectedBookmaker ? 'bg-purple-50/40 font-bold' : 'hover:bg-slate-50/50'}>
                                  <td className="py-2 px-3 font-sans font-medium text-slate-800">{b.bookmaker}</td>
                                  <td className="py-2 px-3 text-center text-slate-900">{b.home_last_seen ? b.home_last_seen.toFixed(2) : '-'}</td>
                                  <td className="py-2 px-3 text-center text-slate-700">{b.draw_last_seen ? b.draw_last_seen.toFixed(2) : '-'}</td>
                                  <td className="py-2 px-3 text-center text-slate-900">{b.away_last_seen ? b.away_last_seen.toFixed(2) : '-'}</td>
                                  <td className="py-2 px-3 text-center text-slate-700">{b.over_25_last_seen ? b.over_25_last_seen.toFixed(2) : '-'}</td>
                                  <td className="py-2 px-3 text-center text-slate-700">{b.btts_yes_last_seen ? b.btts_yes_last_seen.toFixed(2) : '-'}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>

                    </div>
                  );
                })()}
              </>
            )}
          </div>

        ) : (

          /* ================= EVENTS TAB (OPTA COMMENTARY) ================= */
          <div className="space-y-3">
            {events.length === 0 ? (
              <div className="py-16 text-center text-sm text-slate-500 font-medium">
                Bu karşılaşma için Opta olay akışı kaydı bulunamadı.
              </div>
            ) : (
              events.map((ev, idx) => {
                const min = ev.time?.label || ev.minute || '-';
                const type = ev.type || ev.event_type || 'olay';
                return (
                  <div
                    key={ev.id || idx}
                    className="flex items-start gap-3.5 p-3 rounded-xl bg-slate-50 hover:bg-slate-100 border border-slate-200 transition-colors text-xs"
                  >
                    <span className="font-mono font-bold text-slate-700 min-w-[36px] pt-0.5 text-xs">
                      {min}'
                    </span>
                    <div className="flex-1">
                      <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-600 block mb-0.5">
                        {type}
                      </span>
                      <p className="text-slate-800 font-medium leading-relaxed text-xs">
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

      {/* ================= PLAYER MATCH PERFORMANCE MODAL ================= */}
      {selectedPlayerModal && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn"
          onClick={() => setSelectedPlayerModal(null)}
        >
          <div 
            className="bg-white border border-slate-200 rounded-3xl max-w-lg w-full shadow-2xl overflow-hidden relative animate-scaleUp"
            onClick={e => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="p-5 sm:p-6 border-b border-slate-100 bg-gradient-to-b from-slate-50 to-white relative">
              <button
                onClick={() => setSelectedPlayerModal(null)}
                className="absolute top-4 right-4 p-2 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-500 hover:text-slate-900 transition-colors"
                title="Kapat"
              >
                <X className="w-4 h-4" />
              </button>

              <div className="flex items-center gap-4">
                <PlayerAvatar 
                  photoUrl={selectedPlayerModal.player.photo_url}
                  name={selectedPlayerModal.player.name}
                  shirt={selectedPlayerModal.player.shirt}
                  fallback="initials"
                  size="w-16 h-16 text-lg"
                  className="border-2 border-slate-200 bg-white shadow-xs shrink-0"
                />
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-black text-slate-400">
                      #{selectedPlayerModal.player.shirt || '-'}
                    </span>
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md border ${getPositionBadgeClass(selectedPlayerModal.player.position)}`}>
                      {formatPosition(selectedPlayerModal.player.position)}
                    </span>
                    {selectedPlayerModal.player.captain && (
                      <span className="text-[9px] font-black px-1.5 py-0.2 rounded bg-amber-200 text-amber-900">
                        KAPTAN
                      </span>
                    )}
                  </div>
                  <h3 className="text-lg font-black text-slate-900 truncate mt-1">
                    {selectedPlayerModal.player.name}
                  </h3>
                  <div className="flex items-center gap-1.5 text-xs text-slate-500 mt-0.5">
                    <img src={selectedPlayerModal.team.badge} alt="" className="w-3.5 h-3.5 object-contain" />
                    <span>{selectedPlayerModal.team.name}</span>
                  </div>
                </div>
              </div>

              {/* Status bar */}
              <div className="mt-4 pt-3 border-t border-slate-200/80 flex items-center justify-between text-xs text-slate-600">
                <span className="font-semibold">
                  Rol: <strong className="text-slate-900">{selectedPlayerModal.stats.is_starter ? 'İlk 11 Başlangıç' : 'Yedek (Sonradan Girdi)'}</strong>
                </span>
                <span className="font-mono font-bold text-slate-900 bg-slate-100 px-2 py-0.5 rounded-md">
                  {selectedPlayerModal.stats.minutes}' dakika süre
                </span>
              </div>
            </div>

            {/* Modal Body: Metrics Grid */}
            <div className="p-5 sm:p-6 space-y-4">
              <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400 block">
                Bu Karşılaşmadaki Bireysel İstatistikleri
              </span>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {/* Goals */}
                <div className={`p-3 rounded-2xl border text-center transition-all ${
                  selectedPlayerModal.stats.goals > 0 ? 'bg-emerald-50/70 border-emerald-300' : 'bg-slate-50 border-slate-200'
                }`}>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">Gol</span>
                  <div className={`text-2xl font-black font-mono mt-1 ${selectedPlayerModal.stats.goals > 0 ? 'text-emerald-700' : 'text-slate-900'}`}>
                    {selectedPlayerModal.stats.goals || 0}
                  </div>
                </div>

                {/* Assists */}
                <div className={`p-3 rounded-2xl border text-center transition-all ${
                  selectedPlayerModal.stats.assists > 0 ? 'bg-purple-50/70 border-purple-300' : 'bg-slate-50 border-slate-200'
                }`}>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">Asist</span>
                  <div className={`text-2xl font-black font-mono mt-1 ${selectedPlayerModal.stats.assists > 0 ? 'text-purple-700' : 'text-slate-900'}`}>
                    {selectedPlayerModal.stats.assists || 0}
                  </div>
                </div>

                {/* Shots */}
                <div className="p-3 rounded-2xl border border-slate-200 bg-slate-50 text-center">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">Şut (İsabet)</span>
                  <div className="text-2xl font-black font-mono text-slate-900 mt-1">
                    {selectedPlayerModal.stats.shots || 0}
                    <span className="text-xs font-normal text-slate-500 ml-1">
                      ({selectedPlayerModal.stats.shots_ontarget || 0})
                    </span>
                  </div>
                </div>

                {/* Fouls Committed */}
                <div className="p-3 rounded-2xl border border-slate-200 bg-slate-50 text-center">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">Faul Yaptı</span>
                  <div className="text-2xl font-black font-mono text-slate-900 mt-1">
                    {selectedPlayerModal.stats.fouls_committed || 0}
                  </div>
                </div>

                {/* Fouls Won */}
                <div className="p-3 rounded-2xl border border-slate-200 bg-slate-50 text-center">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">Faul Kazandı</span>
                  <div className="text-2xl font-black font-mono text-slate-900 mt-1">
                    {selectedPlayerModal.stats.fouls_won || 0}
                  </div>
                </div>

                {/* Offsides */}
                <div className="p-3 rounded-2xl border border-slate-200 bg-slate-50 text-center">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">Ofsayt</span>
                  <div className="text-2xl font-black font-mono text-slate-900 mt-1">
                    {selectedPlayerModal.stats.offsides || 0}
                  </div>
                </div>
              </div>

              {/* Cards Summary */}
              <div className="p-3 rounded-2xl bg-slate-50 border border-slate-200 flex items-center justify-between text-xs">
                <span className="font-semibold text-slate-600">Disiplin Karnesi:</span>
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-1 font-mono font-bold text-slate-800">
                    <YellowCardIcon />
                    <span>{selectedPlayerModal.stats.yellow_cards || 0} Sarı Kart</span>
                  </div>
                  <div className="flex items-center gap-1 font-mono font-bold text-slate-800">
                    <RedCardIcon />
                    <span>{selectedPlayerModal.stats.red_cards || 0} Kırmızı Kart</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-slate-100 bg-slate-50 flex justify-end">
              <button
                onClick={() => setSelectedPlayerModal(null)}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-900 text-white font-bold text-xs transition-colors cursor-pointer"
              >
                Kapat
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
