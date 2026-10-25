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
import { getStandings, getTeams } from '../services/competitionService';
import { useCompetition } from '../context/CompetitionContext';
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
  const { competitionKey } = useCompetition();
  const [currentLeagueTeams, setCurrentLeagueTeams] = useState(null);
  const [teamSeason, setTeamSeason] = useState(selectedSeason || '2026_27');
  const [activeTeamTab, setActiveTeamTab] = useState('fixtures'); // 'fixtures' | 'profile' | 'squad' | 'managers'
  const [profile, setProfile] = useState(null);
  const [tacticalProfile, setTacticalProfile] = useState(null);
  const [attackingLeaders, setAttackingLeaders] = useState(null);
  const [scenarioProfile, setScenarioProfile] = useState(null);
  const [activeTacticalTab, setActiveTacticalTab] = useState('general');
  const [selectedSquadTab, setSelectedSquadTab] = useState('all');
  const [tacticsLoading, setTacticsLoading] = useState(false);
  const [attackersLoading, setAttackersLoading] = useState(false);
  const [scenariosLoading, setScenariosLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [teamStaff, setTeamStaff] = useState(null);
  const [managerChanges, setManagerChanges] = useState([]);
  const [selectedManager, setSelectedManager] = useState(null);
  const [managerPerformance, setManagerPerformance] = useState(null);
  const [managerPerformanceLoading, setManagerPerformanceLoading] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [squadSortField, setSquadSortField] = useState('position');
  const [squadSortDirection, setSquadSortDirection] = useState('asc');
  const [showMarketValueModal, setShowMarketValueModal] = useState(false);
  const [selectedPlayerForMv, setSelectedPlayerForMv] = useState(null);

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
  const [standings, setStandings] = useState([]);
  const [isTeamSelectorOpen, setIsTeamSelectorOpen] = useState(false);
  const [teamSearchQuery, setTeamSearchQuery] = useState('');
  const teamSelectorRef = React.useRef(null);

  useEffect(() => {
    if (teamSeason === 'all') {
      setStandings([]);
      return;
    }
    getStandings(teamSeason, competitionKey)
      .then(data => setStandings(data.standings || []))
      .catch(err => {
        console.error('Error fetching standings for team profile:', err);
        setStandings([]);
      });
  }, [teamSeason, competitionKey]);

  const standingsMap = useMemo(() => {
    const map = {};
    (standings || []).forEach((s, idx) => {
      map[s.id] = { rank: idx + 1, points: s.points, played: s.played };
    });
    return map;
  }, [standings]);

  useEffect(() => {
    if (!isTeamSelectorOpen) return;
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

  useEffect(() => {
    const s = teamSeason === 'all' ? '2026_27' : teamSeason;
    getTeams(s, competitionKey)
      .then(data => setCurrentLeagueTeams(data.teams || []))
      .catch(err => {
        console.error('Error fetching current season teams:', err);
        setCurrentLeagueTeams([]);
      });
  }, [teamSeason, competitionKey]);

  const currentSeasonTeams = (currentLeagueTeams || []).map(team =>
    getTeam(team.id, team.name)
  );

  const filteredClubs = useMemo(() => {
    if (!teamSearchQuery.trim()) return currentSeasonTeams;
    const q = teamSearchQuery.toLowerCase().trim();
    return currentSeasonTeams.filter(t => 
      t.name.toLowerCase().includes(q) || 
      (t.short && t.short.toLowerCase().includes(q)) ||
      (t.abbr && t.abbr.toLowerCase().includes(q))
    );
  }, [currentSeasonTeams, teamSearchQuery]);

  useEffect(() => {
    if (currentSeasonTeams.length && !currentSeasonTeams.some(team => team.id === selectedTeamId)) {
      onSelectTeam?.(currentSeasonTeams[0].id);
    }
  }, [currentLeagueTeams, selectedTeamId, onSelectTeam]);

  useEffect(() => {
    if (selectedSeason) {
      setTeamSeason(selectedSeason);
    }
  }, [selectedSeason]);

  // UEFA competitions have no "all seasons" view (and nothing before 2022/23).
  useEffect(() => {
    if (!seasonsFor(competitionKey).includes(teamSeason)) {
      const fallback = seasonsFor(competitionKey).includes(selectedSeason) ? selectedSeason : '2026_27';
      setTeamSeason(fallback);
      setSelectedSeason?.(fallback);
    }
  }, [competitionKey, teamSeason, selectedSeason, setSelectedSeason]);

  useEffect(() => {
    const cacheKey = `${selectedTeamId}_${competitionKey}`;
    const cached = getCachedTeamData('profile', cacheKey, teamSeason);
    if (cached) {
      setProfile(cached.data);
      setLoading(false);
      return;
    }

    setLoading(true);
    getTeamProfile(selectedTeamId, teamSeason, undefined, competitionKey)
      .then(data => {
        setProfile(data);
        const { expiresAt, label } = calculateTeamExpiry(data?.next_match, teamSeason);
        setCachedTeamData('profile', cacheKey, teamSeason, data, expiresAt, label);
        setLoading(false);
      })
      .catch(err => {
        console.error('Error fetching team profile:', err);
        setProfile(null);
        setLoading(false);
      });
  }, [selectedTeamId, teamSeason, competitionKey, refreshKey]);

  useEffect(() => {
    const staffSeason = teamSeason === 'all' ? '2026_27' : teamSeason;
    const controller = new AbortController();
    setTeamStaff(null);
    getTeamStaff(staffSeason, selectedTeamId, { signal: controller.signal }, competitionKey)
      .then(data => setTeamStaff(data?.staff || null))
      .catch(err => {
        if (err.name !== 'AbortError') {
          console.error('Error fetching team staff:', err);
          setTeamStaff(null);
        }
      });
    return () => controller.abort();
  }, [selectedTeamId, teamSeason, competitionKey]);

  useEffect(() => {
    const requestedSeason = teamSeason === 'all' ? 'all' : teamSeason;
    const isPastSeason = requestedSeason !== '2026_27' && requestedSeason !== 'all';

    // Past seasons are static, so cache them permanently. Current season is kept live.
    if (isPastSeason) {
      const cached = getCachedTeamData('manager_changes', 'all', requestedSeason);
      if (cached?.data) {
        const changes = Object.values(cached.data.events_by_match || {}).flat()
          .filter(event => Number(event.team_id) === Number(selectedTeamId));
        setManagerChanges(changes.sort((a, b) => a.appointment_date.localeCompare(b.appointment_date)));
        return;
      }
    }

    const controller = new AbortController();
    getManagerChanges(requestedSeason, { signal: controller.signal })
      .then(data => {
        if (isPastSeason) {
          setCachedTeamData('manager_changes', 'all', requestedSeason, data, null, 'Geçmiş sezon teknik direktör geçmişi');
        }
        const changes = Object.values(data.events_by_match || {}).flat()
          .filter(event => Number(event.team_id) === Number(selectedTeamId));
        setManagerChanges(changes.sort((a, b) => a.appointment_date.localeCompare(b.appointment_date)));
      })
      .catch(err => {
        if (err.name !== 'AbortError') {
          console.error('Error fetching team manager change history:', err);
          setManagerChanges([]);
        }
      });
    return () => controller.abort();
  }, [selectedTeamId, teamSeason, refreshKey]);

  useEffect(() => {
    const cached = getCachedTeamData('scenarios', selectedTeamId, teamSeason);
    if (cached) {
      setScenarioProfile(cached.data);
      setScenariosLoading(false);
      return;
    }

    const controller = new AbortController();
    setScenariosLoading(true);
    getTeamScenarios(selectedTeamId, teamSeason, { signal: controller.signal })
      .then(data => {
        setScenarioProfile(data);
        const { expiresAt, label } = calculateTeamExpiry(profile?.next_match, teamSeason);
        setCachedTeamData('scenarios', selectedTeamId, teamSeason, data, expiresAt, label);
      })
      .catch(err => {
        if (err.name !== 'AbortError') {
          console.error('Error fetching team score-state profile:', err);
          setScenarioProfile(null);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setScenariosLoading(false);
      });
    return () => controller.abort();
  }, [selectedTeamId, teamSeason, refreshKey]);

  useEffect(() => {
    const cached = getCachedTeamData('tactics', selectedTeamId, teamSeason);
    if (cached) {
      setTacticalProfile(cached.data);
      setTacticsLoading(false);
      return;
    }

    const controller = new AbortController();
    setTacticsLoading(true);
    getTeamTactics(selectedTeamId, teamSeason, { signal: controller.signal })
      .then(data => {
        setTacticalProfile(data);
        const { expiresAt, label } = calculateTeamExpiry(profile?.next_match, teamSeason);
        setCachedTeamData('tactics', selectedTeamId, teamSeason, data, expiresAt, label);
      })
      .catch(err => {
        if (err.name !== 'AbortError') {
          console.error('Error fetching team tactical profile:', err);
          setTacticalProfile(null);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setTacticsLoading(false);
      });
    return () => controller.abort();
  }, [selectedTeamId, teamSeason, refreshKey]);

  useEffect(() => {
    const cached = getCachedTeamData('attackers', selectedTeamId, teamSeason);
    if (cached) {
      setAttackingLeaders(cached.data);
      setAttackersLoading(false);
      return;
    }

    const controller = new AbortController();
    setAttackersLoading(true);
    getTeamAttackingLeaders(selectedTeamId, teamSeason, { signal: controller.signal })
      .then(data => {
        setAttackingLeaders(data);
        const { expiresAt, label } = calculateTeamExpiry(profile?.next_match, teamSeason);
        setCachedTeamData('attackers', selectedTeamId, teamSeason, data, expiresAt, label);
      })
      .catch(err => {
        if (err.name !== 'AbortError') {
          console.error('Error fetching team attacking leaders:', err);
          setAttackingLeaders(null);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setAttackersLoading(false);
      });
    return () => controller.abort();
  }, [selectedTeamId, teamSeason, refreshKey]);

  // When profile updates with next_match, align the TTL for all cached endpoints
  useEffect(() => {
    if (profile?.next_match) {
      const { expiresAt, label } = calculateTeamExpiry(profile.next_match, teamSeason);
      ['tactics', 'scenarios', 'attackers'].forEach(cat => {
        const item = getCachedTeamData(cat, selectedTeamId, teamSeason);
        if (item?.data && item.expiresAt !== expiresAt) {
          setCachedTeamData(cat, selectedTeamId, teamSeason, item.data, expiresAt, label);
        }
      });
    }
  }, [profile, selectedTeamId, teamSeason]);

  // Handle manual refresh
  const handleManualRefresh = () => {
    setIsRefreshing(true);
    clearTeamCache(selectedTeamId, teamSeason);
    setRefreshKey(prev => prev + 1);
  };

  useEffect(() => {
    if (isRefreshing && !loading && !tacticsLoading && !scenariosLoading && !attackersLoading) {
      setIsRefreshing(false);
    }
  }, [isRefreshing, loading, tacticsLoading, scenariosLoading, attackersLoading]);

  const isProfileCached = useMemo(() => {
    const item = getCachedTeamData('tactics', selectedTeamId, teamSeason);
    return item ? { nextMatchLabel: item.nextMatchLabel, isPermanent: item.isPermanent } : null;
  }, [selectedTeamId, teamSeason, tacticalProfile, refreshKey]);

  const listedTeam = (currentLeagueTeams || []).find(team => Number(team.id) === Number(selectedTeamId));
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

  useEffect(() => {
    if (!selectedManager) return;
    const controller = new AbortController();
    setManagerPerformanceLoading(true);
    setManagerPerformance(null);
    const managerName = selectedManager.name?.display || [selectedManager.name?.first, selectedManager.name?.last].filter(Boolean).join(' ');
    getManagerPerformance(selectedTeamId, managerName, { signal: controller.signal })
      .then(setManagerPerformance)
      .catch(err => { if (err.name !== 'AbortError') setManagerPerformance(null); })
      .finally(() => { if (!controller.signal.aborted) setManagerPerformanceLoading(false); });
    return () => controller.abort();
  }, [selectedManager, selectedTeamId]);
  const activeTab = TEAM_TACTICAL_TABS.find(tab => tab.id === activeTacticalTab) || TEAM_TACTICAL_TABS[0];
  const formatNumber = value => Number(value).toLocaleString('tr-TR', { maximumFractionDigits: 1 });

  const displayedSquad = useMemo(() => {
    // Prefer profile.squad which has accurate season statistics
    if (profile?.squad?.length) {
      return profile.squad.map(player => ({
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
  }, [profile?.squad, teamStaff]);

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

  const last5Matches = useMemo(() => {
    if (!profile?.matches?.length) return [];
    const played = profile.matches.filter(m => m.team_score !== null && m.team_score !== undefined && m.result && (!m.competition || m.competition.key === 'premier_league'));
    return played.slice(-5);
  }, [profile?.matches]);

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
        activeTeamTab={activeTeamTab}
        setActiveTeamTab={setActiveTeamTab}
        displayedSquad={displayedSquad}
        managerChanges={managerChanges}
      />

      <TeamManagerHistorySection
        activeTeamTab={activeTeamTab}
        teamSeason={teamSeason}
        managerChanges={managerChanges}
      />

      {/* TAB: TRANSFERLER & BONSERVİSLER */}
      {activeTeamTab === 'transfers' && (
        <TeamTransfersSection
          teamId={selectedTeamId}
          teamName={currentMeta?.name || profile?.team?.name}
          season={teamSeason}
          onSelectPlayer={(p) => setSelectedPlayerForMv(p)}
        />
      )}

      <TeamGameProfileSection
        activeTeamTab={activeTeamTab}
        isProfileCached={isProfileCached}
        handleManualRefresh={handleManualRefresh}
        isRefreshing={isRefreshing}
        tacticalProfile={tacticalProfile}
        activeTacticalTab={activeTacticalTab}
        setActiveTacticalTab={setActiveTacticalTab}
        tacticalTabs={TEAM_TACTICAL_TABS}
        activeTab={activeTab}
        scenariosLoading={scenariosLoading}
        scenarioProfile={scenarioProfile}
        formatNumber={formatNumber}
        tacticsLoading={tacticsLoading}
        attackersLoading={attackersLoading}
        attackingLeaders={attackingLeaders}
      />

      <TeamFixturesSection
        activeTeamTab={activeTeamTab}
        profile={profile}
        currentMeta={currentMeta}
        loading={loading}
        selectedTeamId={selectedTeamId}
        onSelectMatch={onSelectMatch}
      />

      <TeamSquadSection
        activeTeamTab={activeTeamTab}
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
