import React, { useEffect, useMemo, useState } from 'react';
import { UserSearch } from 'lucide-react';
import { useCompetition } from '../context/competitionState';
import { getTeam } from '../data/teams';
import { getPlayerProfile, getPlayersCompareData, searchPlayers } from '../services/playerService';
import { kickoffSortKey } from '../utils/dateFormatters';
import { updateUrlRoute } from '../utils/router';
import MatchDetailModal from './MatchDetailModal';
import PlayerMarketValueHistoryModal from './PlayerMarketValueHistoryModal';
import EmptyState from './common/EmptyState';
import InlineError from './common/InlineError';
import Skeleton from './common/Skeleton';
import PlayerDiscoveryGrid from './player-profile/PlayerDiscoveryGrid';
import PlayerFormTrend from './player-profile/PlayerFormTrend';
import PlayerMatchHistory from './player-profile/PlayerMatchHistory';
import PlayerProfileHeader from './player-profile/PlayerProfileHeader';
import PlayerSearchPanel from './player-profile/PlayerSearchPanel';

function getPositionMeta(position) {
  const neutralClass = 'bg-background-tertiary text-text-primary border-border';
  const labels = {
    F: 'Forvet',
    FWD: 'Forvet',
    M: 'Orta Saha',
    MID: 'Orta Saha',
    D: 'Defans',
    DEF: 'Defans',
    G: 'Kaleci',
    GK: 'Kaleci',
  };
  return { label: labels[position] || 'Oyuncu', class: neutralClass };
}

function ProfileSkeleton() {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="Oyuncu profili yükleniyor">
      <Skeleton className="h-56 w-full" />
      <Skeleton className="h-52 w-full" />
      <Skeleton className="h-72 w-full" />
    </div>
  );
}

export default function PlayerProfilesTab({
  selectedSeason,
  setSelectedSeason,
  onSelectMatch,
  initialPlayerId = null,
  onSelectPlayer,
  onBackToDiscovery,
  onComparePlayer,
}) {
  const { competitionKey } = useCompetition();
  const [searchByComp, setSearchByComp] = useState({ competition: competitionKey, value: '' });
  const [searchResult, setSearchResult] = useState({ key: '', players: [] });
  const [compareState, setCompareState] = useState({ competition: '', data: null, error: false, seq: 0 });
  const [playerOverride, setPlayerOverride] = useState({
    competition: competitionKey,
    id: initialPlayerId ? String(initialPlayerId) : null,
  });
  const [profileResult, setProfileResult] = useState({ key: '', data: null, error: false, seq: 0 });
  const [seasonOverride, setSeasonOverride] = useState({ prop: selectedSeason, value: selectedSeason });
  const [gwFilter, setGwFilter] = useState({ scope: '', value: 'all' });
  const [compFilter, setCompFilter] = useState({ scope: '', value: 'all' });
  const [activeModalMatch, setActiveModalMatch] = useState(null);
  const [showMarketValueModal, setShowMarketValueModal] = useState(false);

  const searchTerm = searchByComp.competition === competitionKey ? searchByComp.value : '';
  const setSearchTerm = (value) => setSearchByComp({ competition: competitionKey, value });

  const playerSeason = seasonOverride.prop === selectedSeason
    ? (seasonOverride.value || '2026_27')
    : (selectedSeason || '2026_27');

  const selectedPlayerId = playerOverride.competition === competitionKey
    ? playerOverride.id
    : (initialPlayerId ? String(initialPlayerId) : null);

  const selectPlayer = (id) => {
    if (id == null) {
      setPlayerOverride({ competition: competitionKey, id: null });
      onBackToDiscovery?.();
      if (!onBackToDiscovery) updateUrlRoute({ tab: 'players', playerId: null }, false);
      return;
    }
    const sid = String(id);
    setPlayerOverride({ competition: competitionKey, id: sid });
    onSelectPlayer?.(sid);
    if (!onSelectPlayer) updateUrlRoute({ tab: 'players', playerId: sid }, false);
  };

  const compareKey = `${competitionKey}:${compareState.seq}`;

  // Load lightweight directory + leaderboard data once per competition
  useEffect(() => {
    let cancelled = false;
    getPlayersCompareData(competitionKey)
      .then((data) => {
        if (!cancelled) {
          setCompareState((prev) => ({ ...prev, key: compareKey, competition: competitionKey, data, error: false }));
        }
      })
      .catch((error) => {
        console.error('Error fetching player directory:', error);
        if (!cancelled) {
          setCompareState((prev) => ({ ...prev, key: compareKey, competition: competitionKey, data: null, error: true }));
        }
      });
    return () => {
      cancelled = true;
    };
  }, [competitionKey, compareKey]);

  const trimmedSearch = searchTerm.trim();
  const searchKey = `${trimmedSearch}:${playerSeason}:${competitionKey}`;
  const playerList = trimmedSearch && searchResult.key === searchKey ? searchResult.players : [];

  useEffect(() => {
    if (!trimmedSearch) return undefined;
    let cancelled = false;
    searchPlayers({
      search: trimmedSearch,
      season: playerSeason && playerSeason !== 'all' ? playerSeason : undefined,
      competition: competitionKey,
      limit: 15,
    })
      .then((data) => {
        if (!cancelled) setSearchResult({ key: searchKey, players: data.players || [] });
      })
      .catch((error) => console.error('Error searching players:', error));
    return () => {
      cancelled = true;
    };
  }, [trimmedSearch, playerSeason, competitionKey, searchKey]);

  const profileKey = `${selectedPlayerId}:${playerSeason}:${competitionKey}:${profileResult.seq}`;
  const loadingProfile = Boolean(selectedPlayerId && profileResult.key !== profileKey);
  const profileError = Boolean(selectedPlayerId && profileResult.key === profileKey && profileResult.error);
  const playerProfile = profileResult.key === profileKey && !profileResult.error ? profileResult.data : null;

  useEffect(() => {
    if (!selectedPlayerId) return undefined;
    let cancelled = false;
    getPlayerProfile(selectedPlayerId, playerSeason, competitionKey)
      .then((data) => {
        if (!cancelled) setProfileResult((prev) => ({ ...prev, key: profileKey, data, error: false }));
      })
      .catch((error) => {
        console.error('Error fetching player profile:', error);
        if (!cancelled) setProfileResult((prev) => ({ ...prev, key: profileKey, data: null, error: true }));
      });
    return () => {
      cancelled = true;
    };
  }, [selectedPlayerId, playerSeason, competitionKey, profileKey]);

  const compareLoading = compareState.key !== compareKey;
  const compareError = compareState.key === compareKey && compareState.error;
  const compareData = compareState.key === compareKey && !compareState.error ? compareState.data : null;

  const player = playerProfile?.player;
  const stats = playerProfile?.season_stats || {};
  const leagueMatches = useMemo(
    () => (playerProfile?.matches || []).filter((match) => Number(match.minutes_played) > 0),
    [playerProfile?.matches],
  );
  const europeanMatches = useMemo(
    () => (playerProfile?.european?.matches || []).filter((match) => Number(match.minutes_played) > 0),
    [playerProfile?.european?.matches],
  );
  const playedMatches = useMemo(
    () => (europeanMatches.length
      ? [...leagueMatches, ...europeanMatches].sort((a, b) => kickoffSortKey(a.kickoff) - kickoffSortKey(b.kickoff))
      : leagueMatches),
    [leagueMatches, europeanMatches],
  );

  const lastPlayedMatch = leagueMatches[leagueMatches.length - 1];
  const teamId = lastPlayedMatch?.team_id ?? player?.teamId;
  const teamName = lastPlayedMatch?.team_name ?? player?.teamName;
  const team = teamId ? getTeam(teamId, teamName) : (player ? getTeam(player.teamId, player.teamName) : null);

  const playedGameweeks = useMemo(() => {
    const weeks = new Set();
    leagueMatches.forEach((match) => {
      const week = Math.round(Number(match.gameweek));
      if (!Number.isNaN(week) && week > 0) weeks.add(week);
    });
    return [...weeks].sort((a, b) => a - b);
  }, [leagueMatches]);

  const filterScope = `${selectedPlayerId}:${playerSeason}`;
  const selectedMatchGameweek = gwFilter.scope === filterScope ? gwFilter.value : 'all';
  const setSelectedMatchGameweek = (value) => setGwFilter({ scope: filterScope, value });
  const selectedCompetition = compFilter.scope === filterScope ? compFilter.value : 'all';
  const setSelectedCompetition = (value) => setCompFilter({ scope: filterScope, value });

  const filteredMatches = useMemo(() => {
    let list = playedMatches;
    if (selectedCompetition !== 'all') {
      list = list.filter((match) => (match.competition?.key || competitionKey) === selectedCompetition);
    }
    if (selectedMatchGameweek !== 'all') {
      list = list.filter(
        (match) => (match.competition?.key || competitionKey) === competitionKey
          && Math.round(Number(match.gameweek)) === Number(selectedMatchGameweek),
      );
    }
    return list;
  }, [playedMatches, selectedMatchGameweek, selectedCompetition, competitionKey]);

  const handleSeasonChange = (season) => {
    setSeasonOverride({ prop: selectedSeason, value: season });
    setSelectedSeason?.(season);
  };

  const handleSelectMatch = (match) => {
    if (onSelectMatch) onSelectMatch(match);
    else setActiveModalMatch(match);
  };

  const position = player ? getPositionMeta(player.position) : null;

  return (
    <div className="space-y-6 pb-12">
      <PlayerSearchPanel
        searchTerm={searchTerm}
        onSearchChange={setSearchTerm}
        players={playerList}
        directoryPlayers={compareData?.profiles || []}
        selectedPlayerId={selectedPlayerId}
        onSelectPlayer={selectPlayer}
        onBackToDiscovery={() => selectPlayer(null)}
      />

      {!selectedPlayerId ? (
        <PlayerDiscoveryGrid
          compareData={compareData}
          loading={compareLoading}
          error={compareError}
          onRetry={() => setCompareState((prev) => ({ ...prev, seq: prev.seq + 1, error: false }))}
          season={playerSeason}
          onSeasonChange={handleSeasonChange}
          onSelectPlayer={selectPlayer}
        />
      ) : loadingProfile ? (
        <ProfileSkeleton />
      ) : profileError ? (
        <InlineError
          message="Oyuncu profili yüklenemedi. Bağlantıyı kontrol edip tekrar deneyin."
          onRetry={() => setProfileResult((prev) => ({ ...prev, seq: prev.seq + 1 }))}
        />
      ) : !player ? (
        <EmptyState icon={UserSearch}>
          Seçilen oyuncu profili bulunamadı.
        </EmptyState>
      ) : (
        <>
          <PlayerProfileHeader
            player={player}
            stats={stats}
            matches={leagueMatches}
            europeanStats={playerProfile?.european?.stats}
            team={team}
            position={position}
            season={playerSeason}
            onSeasonChange={handleSeasonChange}
            onOpenMarketValue={() => setShowMarketValueModal(true)}
            onCompare={onComparePlayer}
          />

          <PlayerFormTrend matches={playedMatches} />

          <PlayerMatchHistory
            matches={filteredMatches}
            playedMatchCount={playedMatches.length}
            weeks={playedGameweeks}
            selectedWeek={selectedMatchGameweek}
            onWeekChange={setSelectedMatchGameweek}
            hasEuropean={europeanMatches.length > 0}
            europeanStats={playerProfile?.european?.stats}
            selectedCompetition={selectedCompetition}
            onCompetitionChange={setSelectedCompetition}
            loading={false}
            season={playerSeason}
            onSelectMatch={handleSelectMatch}
          />
        </>
      )}

      {activeModalMatch && (
        <MatchDetailModal match={activeModalMatch} onClose={() => setActiveModalMatch(null)} />
      )}

      {showMarketValueModal && player && (
        <PlayerMarketValueHistoryModal
          isOpen={showMarketValueModal}
          onClose={() => setShowMarketValueModal(false)}
          player={player}
          playerId={player.market_value?.tm_id || player.id}
          playerName={player.name}
          playerPhoto={player.photo_url}
          teamBadge={team?.badge}
          teamName={team?.name}
          position={position?.label}
        />
      )}
    </div>
  );
}
