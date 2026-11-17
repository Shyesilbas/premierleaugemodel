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
import { useCompetition } from '../context/competitionState';
import { hasModelPrediction } from '../utils/matchModel';
import { clearAllCaches } from '../utils/teamProfileCache';
import { invalidateApiCache } from '../services/apiClient';
import { getSingleMatchRefreshStatus, startSingleMatchRefresh } from '../services/competitionService';
import { getMatchDetails, getMatchOdds, getMatchPrediction, getRecentMatchForm } from '../services/matchService';
import { getTeamManagers } from '../services/teamService';
import MatchStatsTab from './match-detail/MatchStatsTab';
import MatchTimelineTab from './match-detail/MatchTimelineTab';
import MatchLineupsTab from './match-detail/MatchLineupsTab';

export default function MatchDetailPage({ match, onBack, currentGameweek, selectedSeason }) {
  const { hasModel: competitionHasModel, competitionKey } = useCompetition();
  const [detailsResult, setDetailsResult] = useState(null);
  const [predictionResult, setPredictionResult] = useState(null);
  const [predictionSeq, setPredictionSeq] = useState(0);
  const [refreshKey, setRefreshKey] = useState(0);
  const [refreshingMatch, setRefreshingMatch] = useState(false);
  const [managersResult, setManagersResult] = useState(null);
  const [formResult, setFormResult] = useState(null);

  const [selectedPlayerModal, setSelectedPlayerModal] = useState(null);
  const [lineupViewMode, setLineupViewMode] = useState('pitch');
  const [predSubTab, setPredSubTab] = useState('outcome');
  const [oddsResult, setOddsResult] = useState(null);
  const [selectedBookmaker, setSelectedBookmaker] = useState('Bet365');

  const detailsKey = `${match?.match_id}:${refreshKey}`;
  const details = detailsResult?.key === detailsKey ? detailsResult.data : null;
  const loadError = Boolean(detailsResult?.key === detailsKey && detailsResult.error);
  const loading = Boolean(match?.match_id && detailsResult?.key !== detailsKey);

  const resolvedMatch = React.useMemo(() => {
    if (!match) return null;
    const lus = details?.lineups || [];
    const hLu = lus.find((l) => Number(l.team_id) === Number(match.home_id)) || lus[0];
    const aLu = lus.find((l) => Number(l.team_id) === Number(match.away_id)) || lus[1];
    const hScore = match.home_score ?? hLu?.score ?? null;
    const aScore = match.away_score ?? aLu?.score ?? null;
    const derivedCompleted = Boolean(
      match.status === 'COMPLETED' || (hScore !== null && hScore !== undefined && aScore !== null && aScore !== undefined),
    );
    return {
      ...match,
      home_id: match.home_id ?? hLu?.team_id,
      home_name: match.home_name ?? hLu?.team_name,
      away_id: match.away_id ?? aLu?.team_id,
      away_name: match.away_name ?? aLu?.team_name,
      home_score: hScore,
      away_score: aScore,
      status: derivedCompleted ? 'COMPLETED' : (match.status || 'UPCOMING'),
      kickoff_label: match.kickoff_label || details?.metadata?.kickoff_label,
      ground_name: match.ground_name || details?.metadata?.ground,
      referee_name: match.referee_name || details?.metadata?.referee,
    };
  }, [match, details]);

  const isCompleted = Boolean(
    resolvedMatch?.status === 'COMPLETED' ||
    (resolvedMatch?.home_score !== null && resolvedMatch?.home_score !== undefined && resolvedMatch?.home_score !== ''),
  );
  const hasModel = hasModelPrediction(resolvedMatch, competitionHasModel);
  const isPredictable = hasModel && !isCompleted && (
    currentGameweek ? Number(resolvedMatch?.gameweek) === Number(currentGameweek) : true
  );

  const [activeTab, setActiveTab] = useState(
    isCompleted ? 'timeline' : isPredictable ? 'prediction' : 'lineups',
  );

  const resolvedTab = (isCompleted || !isPredictable) && activeTab === 'prediction'
    ? (isCompleted ? 'timeline' : 'lineups')
    : activeTab;

  const teamManagers = managersResult?.season === (selectedSeason || resolvedMatch?.season || '2026_27')
    ? managersResult.data
    : {};
  const homeTeam = getTeam(resolvedMatch?.home_id, resolvedMatch?.home_name);
  const awayTeam = getTeam(resolvedMatch?.away_id, resolvedMatch?.away_name);
  const homeManager = resolvedMatch?.home_manager || teamManagers[String(resolvedMatch?.home_id)];
  const awayManager = resolvedMatch?.away_manager || teamManagers[String(resolvedMatch?.away_id)];

  const managerSeason = selectedSeason || resolvedMatch?.season || '2026_27';
  useEffect(() => {
    let cancelled = false;
    getTeamManagers(managerSeason)
      .then(data => {
        if (!cancelled) setManagersResult({ season: managerSeason, data: data.managers || {} });
      })
      .catch(err => {
        console.error('Error fetching match team managers:', err);
        if (!cancelled) setManagersResult({ season: managerSeason, data: {} });
      });
    return () => { cancelled = true; };
  }, [managerSeason]);

  const recentForm = formResult?.matchId === match?.match_id ? formResult.data : {};
  useEffect(() => {
    if (!match?.match_id) return undefined;
    let cancelled = false;
    getRecentMatchForm(match.match_id)
      .then(data => {
        if (!cancelled) setFormResult({ matchId: match.match_id, data: data.form || {} });
      })
      .catch(err => {
        console.error('Error fetching pre-match form:', err);
        if (!cancelled) setFormResult({ matchId: match.match_id, data: {} });
      });
    return () => { cancelled = true; };
  }, [match?.match_id]);

  // Fetch match details (revalidating with server ETag cleanly)
  useEffect(() => {
    if (!match?.match_id) return undefined;
    let cancelled = false;
    getMatchDetails(match.match_id)
      .then(data => {
        if (!cancelled) setDetailsResult({ key: detailsKey, data, error: false });
      })
      .catch(err => {
        console.error('Error fetching match details:', err);
        if (!cancelled) setDetailsResult({ key: detailsKey, data: null, error: true });
      });
    return () => { cancelled = true; };
  }, [match?.match_id, detailsKey]);

  const handleServerMatchRefresh = useCallback(async () => {
    if (!match?.match_id || refreshingMatch) return;
    setRefreshingMatch(true);
    try {
      const season = selectedSeason && selectedSeason !== 'all' ? selectedSeason : '2026_27';
      await startSingleMatchRefresh(match.match_id, season, competitionKey);
      for (let i = 0; i < 30; i += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, 900));
        const st = await getSingleMatchRefreshStatus(match.match_id);
        if (st.status === 'completed' || st.status === 'failed' || st.status === 'idle') break;
      }
      clearAllCaches();
      invalidateApiCache();
      setRefreshKey((k) => k + 1);
      setPredictionSeq((s) => s + 1);
    } catch (err) {
      console.error('Match refresh failed:', err);
      setRefreshKey((k) => k + 1);
    } finally {
      setRefreshingMatch(false);
    }
  }, [match, refreshingMatch, selectedSeason, competitionKey]);

  const predRequestKey = `${resolvedMatch?.match_id}:${resolvedMatch?.home_id}:${resolvedMatch?.away_id}:${resolvedMatch?.season}:${competitionKey}:${predictionSeq}`;
  const prediction = predictionResult?.key === predRequestKey ? predictionResult.data : null;
  const predictionFailed = Boolean(predictionResult?.key === predRequestKey && predictionResult.error);
  const loadingPrediction = Boolean(
    !isCompleted && isPredictable && resolvedMatch?.home_id && resolvedMatch?.away_id && predictionResult?.key !== predRequestKey,
  );

  // Fetch model predictions for upcoming current gameweek matches
  useEffect(() => {
    if (isCompleted || !isPredictable || !resolvedMatch?.home_id || !resolvedMatch?.away_id) return undefined;
    let cancelled = false;
    getMatchPrediction(resolvedMatch.home_id, resolvedMatch.away_id, resolvedMatch?.match_id, resolvedMatch?.season, competitionKey)
      .then(data => {
        if (!cancelled) setPredictionResult({ key: predRequestKey, data, error: false });
      })
      .catch(err => {
        console.error('Error fetching prediction:', err);
        if (!cancelled) setPredictionResult({ key: predRequestKey, data: null, error: true });
      });
    return () => { cancelled = true; };
  }, [isCompleted, isPredictable, resolvedMatch?.home_id, resolvedMatch?.away_id, resolvedMatch?.match_id, resolvedMatch?.season, competitionKey, predRequestKey]);

  const oddsData = oddsResult?.matchId === match?.match_id ? oddsResult.data : [];
  const loadingOdds = Boolean(match?.match_id && oddsResult?.matchId !== match?.match_id);

  // Fetch betting market odds
  useEffect(() => {
    if (!match?.match_id) return undefined;
    let cancelled = false;
    getMatchOdds(match.match_id)
      .then(data => {
        if (cancelled) return;
        const list = data.odds || [];
        setOddsResult({ matchId: match.match_id, data: list });
        if (list.length > 0) {
          const hasBet365 = list.some(b => b.bookmaker === 'Bet365');
          setSelectedBookmaker(hasBet365 ? 'Bet365' : list[0].bookmaker);
        }
      })
      .catch(err => {
        console.error('Error fetching odds:', err);
        if (!cancelled) setOddsResult({ matchId: match.match_id, data: [] });
      });
    return () => { cancelled = true; };
  }, [match?.match_id]);

  const lineups = details?.lineups || [];
  const homeLineup = lineups.find(l => l.team_id === resolvedMatch?.home_id) || lineups[0];
  const awayLineup = lineups.find(l => l.team_id === resolvedMatch?.away_id) || lineups[1];
  const teamStats = details?.team_stats || [];
  const playerStats = details?.player_stats || { home: [], away: [] };
  const events = details?.events || [];
  const timeline = details?.timeline || [];
  const goalEvents = timeline.filter(item => item.type === 'goal');
  const homeGoals = goalEvents.filter(item => Number(item.team_id) === Number(resolvedMatch?.home_id));
  const awayGoals = goalEvents.filter(item => Number(item.team_id) === Number(resolvedMatch?.away_id));

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
    if (['D', 'DEF', 'DEFENDER', 'CB', 'LB', 'RB', 'LWB', 'RWB'].includes(p)) return 'bg-background-tertiary text-status-info border-status-info';
    if (['M', 'MID', 'MIDFIELDER', 'CM', 'DM', 'AM', 'LM', 'RM'].includes(p)) return 'bg-background-tertiary text-text-primary border-border';
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
        match={resolvedMatch}
        homeTeam={homeTeam}
        awayTeam={awayTeam}
        homeManager={homeManager}
        awayManager={awayManager}
        isCompleted={isCompleted}
        loading={loading || refreshingMatch}
        meta={details?.metadata || {}}
        homeRedCards={homeRedCards}
        awayRedCards={awayRedCards}
        homeGoals={homeGoals}
        awayGoals={awayGoals}
        recentForm={recentForm}
        onBack={onBack}
        onRefresh={handleServerMatchRefresh}
      />

      <TabBar tabs={tabs} active={resolvedTab} onChange={setActiveTab} label="Maç detay sekmeleri" idPrefix="match-tab" />

      {!isCompleted && hasModel && !isPredictable && (
        <p className="flex items-center gap-2 text-xs text-text-secondary">
          <AlertCircle className="w-4 h-4" strokeWidth={1.5} aria-hidden="true" />
          <span>Model tahminleri {resolvedMatch.gameweek}. haftada etkinleşir.</span>
        </p>
      )}

      <div role="tabpanel" id="match-tab-panel" aria-labelledby={`match-tab-${resolvedTab}`}>
        {loading ? (
          <MatchDetailSkeleton />
        ) : loadError && resolvedTab !== 'prediction' && resolvedTab !== 'odds' ? (
          <InlineError message="Maç detayları yüklenemedi." onRetry={() => setRefreshKey(key => key + 1)} />
        ) : resolvedTab === 'timeline' ? (
          <MatchTimelineTab timeline={timeline} homeTeam={homeTeam} awayTeam={awayTeam} homeTeamId={resolvedMatch?.home_id} />
        ) : resolvedTab === 'lineups' ? (
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
        ) : resolvedTab === 'stats' ? (
          <MatchStatsTab teamStats={teamStats} homeTeam={homeTeam} awayTeam={awayTeam} calcBarWidths={calcBarWidths} />
        ) : resolvedTab === 'prediction' ? (
          <MatchPredictionTab
            prediction={prediction}
            loadingPrediction={loadingPrediction}
            failed={predictionFailed}
            onRetry={() => setPredictionSeq(seq => seq + 1)}
            predSubTab={predSubTab}
            setPredSubTab={setPredSubTab}
            homeTeam={homeTeam}
            awayTeam={awayTeam}
          />
        ) : resolvedTab === 'odds' ? (
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
