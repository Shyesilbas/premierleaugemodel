import { TEAM_TACTICAL_TABS } from './team-profile/tacticalTabs';
import TeamMarketValueDialogs from './team-profile/TeamMarketValueDialogs';
import TeamProfileNavigation from './team-profile/TeamProfileNavigation';
import TeamProfileHero from './team-profile/TeamProfileHero';
import TeamManagerHistorySection from './team-profile/TeamManagerHistorySection';
import TeamManagerPerformanceModal from './team-profile/TeamManagerPerformanceModal';
import React, { useState, useEffect, useMemo } from 'react';
import { getTeam } from '../data/teams';

import TeamTransfersSection from './TeamTransfersSection';
import TeamSquadSection from './team-profile/TeamSquadSection';
import TeamGameProfileSection from './team-profile/TeamGameProfileSection';
import TeamFixturesSection from './team-profile/TeamFixturesSection';
import { getPlayerCategory, getPositionOrder } from './team-profile/teamProfileUtils';
import { getCachedTeamData, setCachedTeamData, calculateTeamExpiry, clearTeamCache } from '../utils/teamProfileCache';
import { invalidateApiCache } from '../services/apiClient';
import { getStandings, getTeams } from '../services/competitionService';
import { useCompetition } from '../context/competitionState';
import { seasonsFor } from '../data/seasons';
import {
  getManagerChanges,
  getManagerPerformance,
  getTeamAttackingLeaders,
  getTeamProfile,
  getTeamScenarios,
  getTeamStaff,
  getTeamTactics,
} from '../services/teamService';

export default function TeamProfilesTab({ selectedSeason, setSelectedSeason, onSelectMatch, selectedTeamId = 1, onSelectTeam }) {
  const { competitionKey, hasRichData } = useCompetition();
  const [seasonOverride, setSeasonOverride] = useState({ prop: selectedSeason, value: selectedSeason });
  const [activeTeamTab, setActiveTeamTab] = useState('fixtures');
  const [tacticalVenue, setTacticalVenue] = useState('all');
  const [standingsResult, setStandingsResult] = useState({ key: '', data: [] });
  const [teamsResult, setTeamsResult] = useState({ key: '', data: [] });
  const [profileResult, setProfileResult] = useState({ key: '', data: null });
  const [tacticsResult, setTacticsResult] = useState({ key: '', data: null });
  const [attackersResult, setAttackersResult] = useState({ key: '', data: null });
  const [scenariosResult, setScenariosResult] = useState({ key: '', data: null });
  const [staffResult, setStaffResult] = useState({ key: '', data: null });
  const [changesResult, setChangesResult] = useState({ key: '', data: [] });
  const [activeTacticalTab, setActiveTacticalTab] = useState('general');
  const [selectedSquadTab, setSelectedSquadTab] = useState('all');
  const [selectedManager, setSelectedManager] = useState(null);
  const [managerPerfResult, setManagerPerfResult] = useState({ key: '', data: null });
  const [refreshKey, setRefreshKey] = useState(0);
  const [manualRefreshKey, setManualRefreshKey] = useState('');
  const [squadSortField, setSquadSortField] = useState('position');
  const [squadSortDirection, setSquadSortDirection] = useState('asc');
  const [showMarketValueModal, setShowMarketValueModal] = useState(false);
  const [selectedPlayerForMv, setSelectedPlayerForMv] = useState(null);

  const availableSeasons = seasonsFor(competitionKey);
  const rawTeamSeason = seasonOverride.prop === selectedSeason
    ? (seasonOverride.value || '2026_27')
    : (selectedSeason || '2026_27');
  const teamSeason = availableSeasons.includes(rawTeamSeason)
    ? rawTeamSeason
    : (availableSeasons.includes(selectedSeason) ? selectedSeason : '2026_27');
  const setTeamSeason = (value) => setSeasonOverride({ prop: selectedSeason, value });

  // Notify parent when competition restriction falls back from an unsupported season (e.g. 'all').
  useEffect(() => {
    if (teamSeason !== rawTeamSeason && setSelectedSeason) {
      setSelectedSeason(teamSeason);
    }
  }, [teamSeason, rawTeamSeason, setSelectedSeason]);

  const handleSquadSort = (field) => {
    if (squadSortField === field) {
      setSquadSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSquadSortField(field);
      if (['appearances', 'starts', 'goals', 'assists', 'yellow_cards', 'red_cards'].includes(field)) {
        setSquadSortDirection('desc');
      } else {
        setSquadSortDirection('asc');
      }
    }
  };

  // Standings data & Quick Club Selector Popover
  const [isTeamSelectorOpen, setIsTeamSelectorOpen] = useState(false);
  const [teamSearchQuery, setTeamSearchQuery] = useState('');
  const teamSelectorRef = React.useRef(null);

  const standingsKey = `${teamSeason}:${competitionKey}`;
  useEffect(() => {
    if (teamSeason === 'all') return undefined;
    let cancelled = false;
    getStandings(teamSeason, competitionKey)
      .then(data => {
        if (!cancelled) setStandingsResult({ key: standingsKey, data: data.standings || [] });
      })
      .catch(err => {
        console.error('Error fetching standings for team profile:', err);
        if (!cancelled) setStandingsResult({ key: standingsKey, data: [] });
      });
    return () => { cancelled = true; };
  }, [teamSeason, competitionKey, standingsKey]);

  const standings = useMemo(
    () => (teamSeason !== 'all' && standingsResult.key === standingsKey ? standingsResult.data : []),
    [teamSeason, standingsResult, standingsKey],
  );

  const standingsMap = useMemo(() => {
    const map = {};
    standings.forEach((s, idx) => {
      map[s.id] = { rank: idx + 1, points: s.points, played: s.played };
    });
    return map;
  }, [standings]);

  useEffect(() => {
    if (!isTeamSelectorOpen) return undefined;
    const handleClickOutside = (e) => {
      if (teamSelectorRef.current && !teamSelectorRef.current.contains(e.target)) {
        setIsTeamSelectorOpen(false);
      }
    };
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') setIsTeamSelectorOpen(false);
    };
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isTeamSelectorOpen]);

  const teamsSeason = teamSeason === 'all' ? '2026_27' : teamSeason;
  const teamsKey = `${teamsSeason}:${competitionKey}`;
  useEffect(() => {
    let cancelled = false;
    getTeams(teamsSeason, competitionKey)
      .then(data => {
        if (!cancelled) setTeamsResult({ key: teamsKey, data: data.teams || [] });
      })
      .catch(err => {
        console.error('Error fetching current season teams:', err);
        if (!cancelled) setTeamsResult({ key: teamsKey, data: [] });
      });
    return () => { cancelled = true; };
  }, [teamsSeason, competitionKey, teamsKey]);

  const currentLeagueTeams = useMemo(
    () => (teamsResult.key === teamsKey ? teamsResult.data : []),
    [teamsResult, teamsKey],
  );

  const currentSeasonTeams = useMemo(
    () => currentLeagueTeams.map(team => getTeam(team.id, team.name)),
    [currentLeagueTeams],
  );

  const filteredClubs = useMemo(() => {
    if (!teamSearchQuery.trim()) return currentSeasonTeams;
    const q = teamSearchQuery.toLowerCase().trim();
    return currentSeasonTeams.filter(t =>
      t.name.toLowerCase().includes(q) ||
      (t.short && t.short.toLowerCase().includes(q)) ||
      (t.abbr && t.abbr.toLowerCase().includes(q)),
    );
  }, [currentSeasonTeams, teamSearchQuery]);

  useEffect(() => {
    if (currentSeasonTeams.length && !currentSeasonTeams.some(team => team.id === selectedTeamId)) {
      onSelectTeam?.(currentSeasonTeams[0].id);
    }
  }, [currentSeasonTeams, selectedTeamId, onSelectTeam]);

  const cacheKey = `${selectedTeamId}_${competitionKey}`;
  const profileKey = `${selectedTeamId}:${teamSeason}:${competitionKey}:${refreshKey}`;
  const cachedProfile = useMemo(
    () => (refreshKey >= 0 ? getCachedTeamData('profile', cacheKey, teamSeason)?.data || null : null),
    [cacheKey, teamSeason, refreshKey],
  );

  useEffect(() => {
    if (cachedProfile) return undefined;
    let cancelled = false;
    getTeamProfile(selectedTeamId, teamSeason, undefined, competitionKey)
      .then(data => {
        if (cancelled) return;
        setProfileResult({ key: profileKey, data });
        const { expiresAt, label } = calculateTeamExpiry(data?.next_match, teamSeason);
        setCachedTeamData('profile', cacheKey, teamSeason, data, expiresAt, label);
      })
      .catch(err => {
        console.error('Error fetching team profile:', err);
        if (!cancelled) setProfileResult({ key: profileKey, data: null });
      });
    return () => { cancelled = true; };
  }, [cachedProfile, selectedTeamId, teamSeason, competitionKey, cacheKey, profileKey]);

  const profile = cachedProfile || (profileResult.key === profileKey ? profileResult.data : null);
  const loading = Boolean(!cachedProfile && profileResult.key !== profileKey);

  const nextMatchRef = React.useRef(null);
  useEffect(() => {
    nextMatchRef.current = profile?.next_match || null;
  }, [profile?.next_match]);

  const staffSeason = teamSeason === 'all' ? '2026_27' : teamSeason;
  const staffKey = `${selectedTeamId}:${staffSeason}:${competitionKey}`;
  useEffect(() => {
    const controller = new AbortController();
    getTeamStaff(staffSeason, selectedTeamId, { signal: controller.signal }, competitionKey)
      .then(data => setStaffResult({ key: staffKey, data: data?.staff || null }))
      .catch(err => {
        if (err.name !== 'AbortError') {
          console.error('Error fetching team staff:', err);
          setStaffResult({ key: staffKey, data: null });
        }
      });
    return () => controller.abort();
  }, [staffSeason, selectedTeamId, competitionKey, staffKey]);

  const teamStaff = staffResult.key === staffKey ? staffResult.data : null;

  const requestedChangesSeason = teamSeason === 'all' ? 'all' : teamSeason;
  const isPastSeason = requestedChangesSeason !== '2026_27' && requestedChangesSeason !== 'all';
  const changesKey = `${selectedTeamId}:${requestedChangesSeason}:${refreshKey}`;

  const cachedChanges = useMemo(() => {
    if (!isPastSeason) return null;
    const cached = getCachedTeamData('manager_changes', 'all', requestedChangesSeason);
    if (!cached?.data) return null;
    return Object.values(cached.data.events_by_match || {})
      .flat()
      .filter(event => Number(event.team_id) === Number(selectedTeamId))
      .sort((a, b) => a.appointment_date.localeCompare(b.appointment_date));
  }, [isPastSeason, requestedChangesSeason, selectedTeamId]);

  useEffect(() => {
    if (cachedChanges) return undefined;
    const controller = new AbortController();
    getManagerChanges(requestedChangesSeason, { signal: controller.signal })
      .then(data => {
        if (isPastSeason) {
          setCachedTeamData('manager_changes', 'all', requestedChangesSeason, data, null, 'Geçmiş sezon teknik direktör geçmişi');
        }
        const changes = Object.values(data.events_by_match || {})
          .flat()
          .filter(event => Number(event.team_id) === Number(selectedTeamId))
          .sort((a, b) => a.appointment_date.localeCompare(b.appointment_date));
        setChangesResult({ key: changesKey, data: changes });
      })
      .catch(err => {
        if (err.name !== 'AbortError') {
          console.error('Error fetching team manager change history:', err);
          setChangesResult({ key: changesKey, data: [] });
        }
      });
    return () => controller.abort();
  }, [cachedChanges, requestedChangesSeason, isPastSeason, selectedTeamId, changesKey]);

  const managerChanges = cachedChanges || (changesResult.key === changesKey ? changesResult.data : []);

  const sectionKey = `${selectedTeamId}:${teamSeason}:${refreshKey}`;
  const tacticsSectionKey = `${selectedTeamId}:${teamSeason}:${tacticalVenue}:${refreshKey}`;

  useEffect(() => {
    if (!hasRichData) return undefined;
    const controller = new AbortController();
    getTeamScenarios(selectedTeamId, teamSeason, { signal: controller.signal })
      .then(data => {
        setScenariosResult({ key: sectionKey, data });
      })
      .catch(err => {
        if (err.name !== 'AbortError') {
          console.error('Error fetching team score-state profile:', err);
          setScenariosResult({ key: sectionKey, data: null });
        }
      });
    return () => controller.abort();
  }, [hasRichData, selectedTeamId, teamSeason, sectionKey]);

  const scenarioProfile = hasRichData && scenariosResult.key === sectionKey ? scenariosResult.data : null;
  const scenariosLoading = Boolean(hasRichData && scenariosResult.key !== sectionKey);

  useEffect(() => {
    if (!hasRichData) return undefined;
    const controller = new AbortController();
    getTeamTactics(selectedTeamId, teamSeason, { signal: controller.signal }, tacticalVenue)
      .then(data => {
        setTacticsResult({ key: tacticsSectionKey, data });
      })
      .catch(err => {
        if (err.name !== 'AbortError') {
          console.error('Error fetching team tactical profile:', err);
          setTacticsResult({ key: tacticsSectionKey, data: null });
        }
      });
    return () => controller.abort();
  }, [hasRichData, selectedTeamId, teamSeason, tacticalVenue, tacticsSectionKey]);

  const tacticalProfile = hasRichData && tacticsResult.key === tacticsSectionKey ? tacticsResult.data : null;
  const tacticsLoading = Boolean(hasRichData && tacticsResult.key !== tacticsSectionKey);

  useEffect(() => {
    if (!hasRichData) return undefined;
    const controller = new AbortController();
    getTeamAttackingLeaders(selectedTeamId, teamSeason, { signal: controller.signal })
      .then(data => {
        setAttackersResult({ key: sectionKey, data });
      })
      .catch(err => {
        if (err.name !== 'AbortError') {
          console.error('Error fetching team attacking leaders:', err);
          setAttackersResult({ key: sectionKey, data: null });
        }
      });
    return () => controller.abort();
  }, [hasRichData, selectedTeamId, teamSeason, sectionKey]);

  const attackingLeaders = hasRichData && attackersResult.key === sectionKey ? attackersResult.data : null;
  const attackersLoading = Boolean(hasRichData && attackersResult.key !== sectionKey);

  // Handle manual refresh
  const handleManualRefresh = () => {
    clearTeamCache(selectedTeamId, teamSeason, competitionKey);
    invalidateApiCache('/api/teams/');
    const nextRefresh = refreshKey + 1;
    setManualRefreshKey(`${selectedTeamId}:${teamSeason}:${competitionKey}:${nextRefresh}`);
    setRefreshKey(nextRefresh);
  };

  const isRefreshing = Boolean(
    manualRefreshKey === profileKey && (loading || tacticsLoading || scenariosLoading || attackersLoading),
  );

  const resolvedTeamTab = !hasRichData && activeTeamTab === 'profile' ? 'fixtures' : activeTeamTab;
  const isProfileCached = null;

  const listedTeam = currentLeagueTeams.find(team => Number(team.id) === Number(selectedTeamId));
  const profileTeam = profile?.team && Number(profile.team.id) === Number(selectedTeamId) ? profile.team : null;
  const currentMeta = getTeam(selectedTeamId, profileTeam?.name || listedTeam?.name || 'Takım');
  const teamOfficials = useMemo(() => {
    const uniqueOfficials = new Map();
    (teamStaff?.officials || []).forEach(official => {
      const role = (official.role || '').toLowerCase();
      if (!['manager', 'assistant manager', 'matchday manager'].includes(role)) return;
      const key = `${official.id || official.officialId || official.name?.display}-${role}`;
      if (!uniqueOfficials.has(key)) uniqueOfficials.set(key, official);
    });
    return [...uniqueOfficials.values()].sort((a, b) => {
      const order = role => role === 'Manager' ? 0 : role === 'Assistant Manager' ? 1 : 2;
      return order(a.role) - order(b.role) || (a.name?.display || '').localeCompare(b.name?.display || '', 'tr');
    });
  }, [teamStaff]);
  const teamManager = teamOfficials.find(official => official.role === 'Manager' && official.active)
    || teamOfficials.find(official => official.role === 'Manager');
  // Chelsea's 2026/27 feed lists both its interim and first-team manager as active.
  const displayManager = Number(selectedTeamId) === 4 && teamSeason === '2026_27'
    ? teamOfficials.find(official => (official.name?.display || '').toLowerCase() === 'xabi alonso') || teamManager
    : teamManager;

  const selectedManagerName = selectedManager
    ? (selectedManager.name?.display || [selectedManager.name?.first, selectedManager.name?.last].filter(Boolean).join(' '))
    : '';
  const managerPerfKey = selectedManager ? `${selectedTeamId}:${selectedManagerName}` : '';

  useEffect(() => {
    if (!selectedManager) return undefined;
    const controller = new AbortController();
    getManagerPerformance(selectedTeamId, selectedManagerName, { signal: controller.signal })
      .then(data => setManagerPerfResult({ key: managerPerfKey, data }))
      .catch(err => {
        if (err.name !== 'AbortError') setManagerPerfResult({ key: managerPerfKey, data: null });
      });
    return () => controller.abort();
  }, [selectedManager, selectedTeamId, selectedManagerName, managerPerfKey]);

  const managerPerformanceLoading = Boolean(selectedManager && managerPerfResult.key !== managerPerfKey);
  const managerPerformance = managerPerfResult.key === managerPerfKey ? managerPerfResult.data : null;

  const activeTab = TEAM_TACTICAL_TABS.find(tab => tab.id === activeTacticalTab) || TEAM_TACTICAL_TABS[0];
  const formatNumber = value => Number(value).toLocaleString('tr-TR', { maximumFractionDigits: 1 });

  const profileSquad = profile?.squad;
  const displayedSquad = useMemo(() => {
    if (profileSquad?.length) {
      return profileSquad.map(player => ({
        id: player.id,
        name: player.name,
        position: player.position,
        shirt: player.shirt,
        appearances: player.appearances ?? 0,
        starts: player.starts ?? 0,
        goals: player.goals ?? 0,
        assists: player.assists ?? 0,
        yellow_cards: player.yellow_cards ?? 0,
        red_cards: player.red_cards ?? 0,
        photo_url: player.photo_url || null,
        captain: player.captain || false,
        market_value_eur: player.market_value_eur ?? null,
        market_value_formatted: player.market_value_formatted ?? null,
      }));
    }
    if (!teamStaff?.players?.length) return [];
    return teamStaff.players.map(player => ({
      id: player.id || player.playerId,
      name: player.name?.display || [player.name?.first, player.name?.last].filter(Boolean).join(' '),
      position: player.info?.position || player.latestPosition,
      shirt: player.info?.shirtNum,
      appearances: player.appearances || 0,
      starts: 0,
      goals: player.goals ?? player.goalsScored ?? 0,
      assists: 0,
      yellow_cards: 0,
      red_cards: 0,
      photo_url: null,
      captain: false,
    }));
  }, [profileSquad, teamStaff]);

  const displayedSquadCounts = useMemo(() => {
    const counts = { all: displayedSquad.length, G: 0, D: 0, M: 0, F: 0 };
    displayedSquad.forEach(player => {
      const category = getPlayerCategory(player.position);
      if (counts[category] !== undefined) counts[category]++;
    });
    return counts;
  }, [displayedSquad]);

  const filteredSquad = useMemo(() => {
    if (!displayedSquad.length) return [];
    let list = displayedSquad;
    if (selectedSquadTab !== 'all') {
      list = list.filter(p => getPlayerCategory(p.position) === selectedSquadTab);
    }
    return [...list].sort((a, b) => {
      let comparison = 0;
      if (squadSortField === 'name') {
        comparison = (a.name || '').localeCompare(b.name || '', 'tr');
      } else if (squadSortField === 'shirt') {
        const sA = a.shirt != null && !isNaN(Number(a.shirt)) ? Number(a.shirt) : 999;
        const sB = b.shirt != null && !isNaN(Number(b.shirt)) ? Number(b.shirt) : 999;
        comparison = sA - sB;
      } else if (squadSortField === 'position') {
        const posA = getPositionOrder(getPlayerCategory(a.position));
        const posB = getPositionOrder(getPlayerCategory(b.position));
        if (posA !== posB) {
          comparison = posA - posB;
        } else {
          const appsDiff = (b.appearances || 0) - (a.appearances || 0);
          if (appsDiff !== 0) comparison = appsDiff;
          else {
            const sA = a.shirt != null && !isNaN(Number(a.shirt)) ? Number(a.shirt) : 999;
            const sB = b.shirt != null && !isNaN(Number(b.shirt)) ? Number(b.shirt) : 999;
            comparison = sA - sB;
          }
        }
      } else {
        const valA = Number(a[squadSortField]) || 0;
        const valB = Number(b[squadSortField]) || 0;
        comparison = valA - valB;
      }
      return squadSortDirection === 'asc' ? comparison : -comparison;
    });
  }, [displayedSquad, selectedSquadTab, squadSortField, squadSortDirection]);

  const profileMatches = profile?.matches;
  const last5Matches = useMemo(() => {
    if (!profileMatches?.length) return [];
    const played = profileMatches.filter(m => m.team_score !== null && m.team_score !== undefined && m.result && (!m.competition || m.competition.key === 'premier_league'));
    return played.slice(-5);
  }, [profileMatches]);

  return (
    <div className="space-y-6">

      <TeamProfileHero
        profile={profile}
        currentMeta={currentMeta}
        selectedTeamId={selectedTeamId}
        onSelectTeam={onSelectTeam}
        teamSeason={teamSeason}
        setTeamSeason={setTeamSeason}
        setSelectedSeason={setSelectedSeason}
        standingsMap={standingsMap}
        displayManager={displayManager}
        onSelectManager={setSelectedManager}
        last5Matches={last5Matches}
        isTeamSelectorOpen={isTeamSelectorOpen}
        setIsTeamSelectorOpen={setIsTeamSelectorOpen}
        teamSearchQuery={teamSearchQuery}
        setTeamSearchQuery={setTeamSearchQuery}
        filteredClubs={filteredClubs}
        teamSelectorRef={teamSelectorRef}
        setShowMarketValueModal={setShowMarketValueModal}
      />

      <TeamProfileNavigation
        profile={profile}
        activeTeamTab={resolvedTeamTab}
        setActiveTeamTab={setActiveTeamTab}
        displayedSquad={displayedSquad}
        managerChanges={managerChanges}
        showGameProfile={hasRichData}
      />

      <TeamManagerHistorySection
        activeTeamTab={resolvedTeamTab}
        teamSeason={teamSeason}
        managerChanges={managerChanges}
      />

      {/* TAB: TRANSFERLER & BONSERVİSLER */}
      {resolvedTeamTab === 'transfers' && (
        <TeamTransfersSection
          teamId={selectedTeamId}
          teamName={currentMeta?.name || profile?.team?.name}
          season={teamSeason}
          onSelectPlayer={(p) => setSelectedPlayerForMv(p)}
        />
      )}

      {hasRichData && (
        <TeamGameProfileSection
          activeTeamTab={resolvedTeamTab}
          isProfileCached={isProfileCached}
          handleManualRefresh={handleManualRefresh}
          isRefreshing={isRefreshing}
          tacticalProfile={tacticalProfile}
          activeTacticalTab={activeTacticalTab}
          setActiveTacticalTab={setActiveTacticalTab}
          tacticalVenue={tacticalVenue}
          setTacticalVenue={setTacticalVenue}
          tacticalTabs={TEAM_TACTICAL_TABS}
          activeTab={activeTab}
          scenariosLoading={scenariosLoading}
          scenarioProfile={scenarioProfile}
          formatNumber={formatNumber}
          tacticsLoading={tacticsLoading}
          attackersLoading={attackersLoading}
          attackingLeaders={attackingLeaders}
        />
      )}

      <TeamFixturesSection
        activeTeamTab={resolvedTeamTab}
        profile={profile}
        currentMeta={currentMeta}
        loading={loading}
        selectedTeamId={selectedTeamId}
        onSelectMatch={onSelectMatch}
      />

      <TeamSquadSection
        activeTeamTab={resolvedTeamTab}
        displayedSquad={displayedSquad}
        currentMeta={currentMeta}
        selectedSquadTab={selectedSquadTab}
        setSelectedSquadTab={setSelectedSquadTab}
        teamStaff={teamStaff}
        displayedSquadCounts={displayedSquadCounts}
        filteredSquad={filteredSquad}
        handleSquadSort={handleSquadSort}
        squadSortField={squadSortField}
        squadSortDirection={squadSortDirection}
        setSelectedPlayerForMv={setSelectedPlayerForMv}
      />

      <TeamManagerPerformanceModal
        selectedManager={selectedManager}
        managerPerformanceLoading={managerPerformanceLoading}
        managerPerformance={managerPerformance}
        teamName={currentMeta?.name}
        onClose={() => setSelectedManager(null)}
      />

      <TeamMarketValueDialogs
        profile={profile}
        teamSeason={teamSeason}
        showMarketValueModal={showMarketValueModal}
        onCloseMarketValue={() => setShowMarketValueModal(false)}
        selectedPlayer={selectedPlayerForMv}
        onClosePlayer={() => setSelectedPlayerForMv(null)}
      />

    </div>
  );
}
