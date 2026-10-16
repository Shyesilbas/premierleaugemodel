import MatchScoreboard from './match-detail/MatchScoreboard';
import MatchPageOddsTab from './match-detail/MatchPageOddsTab';
import PlayerMatchPerformanceModal from './match-detail/PlayerMatchPerformanceModal';
import MatchPredictionTab from './match-detail/MatchPredictionTab';
import React, { useEffect, useState } from 'react';
import { Clock, Users, BarChart3, Activity, AlertCircle, Sparkles, TrendingUp } from 'lucide-react';
import { getTeam } from '../data/teams';
import { getCachedTeamData, setCachedTeamData } from '../utils/teamProfileCache';
import { getMatchDetails, getMatchOdds, getMatchPrediction, getRecentMatchForm } from '../services/matchService';
import { getTeamManagers } from '../services/teamService';
import MatchStatsTab from './match-detail/MatchStatsTab';
import MatchTimelineTab from './match-detail/MatchTimelineTab';
import MatchLineupsTab from './match-detail/MatchLineupsTab';

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
  const [modalTab, setModalTab] = useState('general'); // 'general' | 'attack' | 'defense'
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
    getTeamManagers(season)
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
    getRecentMatchForm(match.match_id)
      .then(data => {
        if (!cancelled) setRecentForm(data.form || {});
      })
      .catch(err => {
        console.error('Error fetching pre-match form:', err);
        if (!cancelled) setRecentForm({});
      });
    return () => { cancelled = true; };
  }, [match?.match_id]);

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
  }, [match?.match_id, isCompleted, refreshKey]);

  // Fetch model predictions for upcoming current gameweek matches
  useEffect(() => {
    if (isCompleted || !isPredictable) return;
    if (!match?.home_id || !match?.away_id) return;
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
  }, [match?.home_id, match?.away_id, isCompleted, isPredictable]);

  // Fetch betting market odds
  useEffect(() => {
    if (!match?.match_id) return;
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
  }, [match?.match_id]);

  const lineups = details?.lineups || [];
  const homeLineup = lineups.find(l => l.team_id === match?.home_id) || lineups[0];
  const awayLineup = lineups.find(l => l.team_id === match?.away_id) || lineups[1];
  const teamStats = details?.team_stats || [];
  const playerStats = details?.player_stats || { home: [], away: [] };
  const events = details?.events || [];
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
      penalties_won: 0,
      penalties_conceded: 0,
      penalties_missed: 0,
      saves: 0,
      rating: player.rating != null ? player.rating : null,
      attack_rating: null,
      defense_rating: null,
      team_score: side === 'home' ? match?.home_score : match?.away_score,
      opp_score: side === 'home' ? match?.away_score : match?.home_score,
    };
    setSelectedPlayerModal({
      player,
      stats: statsObj,
      team: side === 'home' ? homeTeam : awayTeam,
      side
    });
    setModalTab('general');
  };

  if (!match) return null;

  return (
    <div className="w-full space-y-6 pb-16 animate-fadeIn">
      
      <MatchScoreboard
        match={match}
        homeTeam={homeTeam}
        awayTeam={awayTeam}
        homeManager={homeManager}
        awayManager={awayManager}
        isCompleted={isCompleted}
        loading={loading}
        meta={details?.metadata || {}}
        homeRedCards={homeRedCards}
        awayRedCards={awayRedCards}
        homeGoals={homeGoals}
        awayGoals={awayGoals}
        recentForm={recentForm}
        onBack={onBack}
        onRefresh={() => setRefreshKey(key => key + 1)}
      />

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

          <MatchTimelineTab timeline={timeline} homeTeam={homeTeam} awayTeam={awayTeam} homeTeamId={match?.home_id} />

        ) : activeTab === 'lineups' ? (

                    <MatchLineupsTab
            homeLineup={homeLineup}
            awayLineup={awayLineup}
            homeTeam={homeTeam}
            awayTeam={awayTeam}
            playerStats={playerStats}
            lineupViewMode={lineupViewMode}
            setLineupViewMode={setLineupViewMode}
            isCompleted={isCompleted}
            prediction={prediction}
            handlePlayerClick={handlePlayerClick}
            groupPlayersByPosition={groupPlayersByPosition}
            formatPosition={formatPosition}
            getPositionBadgeClass={getPositionBadgeClass}
          />
) : activeTab === 'stats' ? (

          <MatchStatsTab teamStats={teamStats} homeTeam={homeTeam} awayTeam={awayTeam} calcBarWidths={calcBarWidths} />

        ) : activeTab === 'prediction' ? (
          <MatchPredictionTab
            prediction={prediction}
            loadingPrediction={loadingPrediction}
            predSubTab={predSubTab}
            setPredSubTab={setPredSubTab}
            homeTeam={homeTeam}
            awayTeam={awayTeam}
          />
        ) : activeTab === 'odds' ? (
          <MatchPageOddsTab
            loadingOdds={loadingOdds}
            oddsData={oddsData}
            selectedBookmaker={selectedBookmaker}
            setSelectedBookmaker={setSelectedBookmaker}
            homeTeam={homeTeam}
            awayTeam={awayTeam}
          />
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
      <PlayerMatchPerformanceModal
        selectedPlayerModal={selectedPlayerModal}
        onClose={() => setSelectedPlayerModal(null)}
        modalTab={modalTab}
        setModalTab={setModalTab}
        formatPosition={formatPosition}
        getPositionBadgeClass={getPositionBadgeClass}
      />

    </div>
  );
}
