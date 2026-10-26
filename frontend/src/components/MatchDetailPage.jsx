import MatchScoreboard from './match-detail/MatchScoreboard';
import MatchEventsTab from './match-detail/MatchEventsTab';
import MatchDetailSkeleton from './match-detail/MatchDetailSkeleton';
import TabBar from './common/TabBar';
import InlineError from './common/InlineError';
import MatchPageOddsTab from './match-detail/MatchPageOddsTab';
import PlayerMatchPanel from './match-detail/PlayerMatchPanel';
import MatchPredictionTab from './match-detail/MatchPredictionTab';
import React, { useCallback, useEffect, useState } from 'react';
import { Clock, Users, BarChart3, Activity, AlertCircle, Sparkles, TrendingUp } from 'lucide-react';
import { getTeam } from '../data/teams';
import { useCompetition } from '../context/CompetitionContext';
import { hasModelPrediction } from '../utils/matchModel';
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
  const { hasModel: competitionHasModel, competitionKey } = useCompetition();
  const hasModel = hasModelPrediction(match, competitionHasModel);
  const isPredictable = hasModel && !isCompleted && (
    currentGameweek ? Number(match?.gameweek) === Number(currentGameweek) : true
  );

  // Main tab: default to 'timeline' for completed matches as requested
  const [activeTab, setActiveTab] = useState(
    isCompleted ? 'timeline' : isPredictable ? 'prediction' : 'lineups'
  );
  const [details, setDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [prediction, setPrediction] = useState(null);
  const [loadingPrediction, setLoadingPrediction] = useState(false);
  const [predictionFailed, setPredictionFailed] = useState(false);
  const [predictionKey, setPredictionKey] = useState(0);
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
    setLoadError(false);
    getMatchDetails(match.match_id)
      .then(data => {
        setDetails(data);
        // Freeze only finished matches whose full provider stats are downloaded (event-count fallbacks may still be upgraded); otherwise a partial/empty response would stay forever
        if (isCompleted && data?.team_stats?.length > 0 && data?.metadata?.stats_source !== 'UEFA olay akışı') {
          setCachedTeamData('match_detail', match.match_id, 'all', data, null, 'Tamamlanan maç detayı');
        }
        setLoading(false);
      })
      .catch(err => {
        console.error('Error fetching match details:', err);
        setLoadError(true);
        setLoading(false);
      });
  }, [match?.match_id, isCompleted, refreshKey]);

  // Fetch model predictions for upcoming current gameweek matches
  useEffect(() => {
    if (isCompleted || !isPredictable) return;
    if (!match?.home_id || !match?.away_id) return;
    setLoadingPrediction(true);
    setPredictionFailed(false);
    getMatchPrediction(match.home_id, match.away_id, match?.match_id, match?.season, competitionKey)
      .then(data => {
        setPrediction(data);
        setLoadingPrediction(false);
      })
      .catch(err => {
        console.error('Error fetching prediction:', err);
        setPredictionFailed(true);
        setLoadingPrediction(false);
      });
  }, [match?.home_id, match?.away_id, isCompleted, isPredictable, predictionKey]);

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
    if (!pos) return 'bg-background-tertiary text-text-primary border-border';
    const p = String(pos).toUpperCase();
    if (['G', 'GK', 'GOALKEEPER'].includes(p)) return 'bg-background-tertiary text-status-warning border-status-warning';
    if (['D', 'DEF', 'DEFENDER', 'CB', 'LB', 'RB', 'LWB', 'RWB'].includes(p)) return 'bg-background-tertiary text-primary border-primary';
    if (['M', 'MID', 'MIDFIELDER', 'CM', 'DM', 'AM', 'LM', 'RM'].includes(p)) return 'bg-background-tertiary text-primary border-primary';
    if (['F', 'FWD', 'FORWARD', 'ST', 'CF', 'RW', 'LW', 'ATT'].includes(p)) return 'bg-background-tertiary text-status-error border-status-error';
    return 'bg-background-tertiary text-text-primary border-border';
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

  const closePlayerPanel = useCallback(() => setSelectedPlayerModal(null), []);

  const handlePlayerClick = (player, side, e) => {
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
      side,
      anchor: e?.currentTarget?.getBoundingClientRect?.() || null
    });
  };

  if (!match) return null;

  if (!match) return null;

  const tabs = [
    isCompleted && { id: 'timeline', label: 'Zaman akışı', icon: Clock, count: timeline.length },
    { id: 'lineups', label: isCompleted ? 'Kadrolar' : 'Kadro bilgisi', icon: Users },
    isCompleted && { id: 'stats', label: 'İstatistikler', icon: BarChart3 },
    !isCompleted && isPredictable && { id: 'prediction', label: 'Model tahminleri', icon: Sparkles },
    isCompleted && events.length > 0 && { id: 'events', label: 'Olay günlüğü', icon: Activity, count: events.length },
    oddsData.length > 0 && { id: 'odds', label: 'Piyasa oranları', icon: TrendingUp, count: oddsData.length },
  ].filter(Boolean);

  return (
    <div className="w-full space-y-4 pb-16 animate-fadeIn motion-reduce:animate-none">

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

      <TabBar tabs={tabs} active={activeTab} onChange={setActiveTab} label="Maç detay sekmeleri" idPrefix="match-tab" />

      {!isCompleted && hasModel && !isPredictable && (
        <p className="flex items-center gap-2 text-xs text-text-secondary">
          <AlertCircle className="w-4 h-4" strokeWidth={1.5} aria-hidden="true" />
          <span>Model tahminleri {match.gameweek}. haftada etkinleşir.</span>
        </p>
      )}

      <div role="tabpanel" id="match-tab-panel" aria-labelledby={`match-tab-${activeTab}`}>
        {loading ? (
          <MatchDetailSkeleton />
        ) : loadError && activeTab !== 'prediction' && activeTab !== 'odds' ? (
          <InlineError message="Maç detayları yüklenemedi." onRetry={() => setRefreshKey(key => key + 1)} />
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
            failed={predictionFailed}
            onRetry={() => setPredictionKey(key => key + 1)}
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
          <MatchEventsTab events={events} />
        )}
      </div>

      <PlayerMatchPanel
        selectedPlayer={selectedPlayerModal}
        onClose={closePlayerPanel}
        isCompleted={isCompleted}
        formatPosition={formatPosition}
      />
    </div>
  );
}
