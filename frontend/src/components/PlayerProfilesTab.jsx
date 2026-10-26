import React, { useEffect, useMemo, useState } from 'react';
import { getTeam } from '../data/teams';
import MatchDetailModal from './MatchDetailModal';
import PlayerMarketValueHistoryModal from './PlayerMarketValueHistoryModal';
import PlayerSearchPanel from './player-profile/PlayerSearchPanel';
import PlayerProfileHeader from './player-profile/PlayerProfileHeader';
import PlayerMatchHistory from './player-profile/PlayerMatchHistory';
import { kickoffSortKey } from '../utils/dateFormatters';
import { getPlayerProfile, searchPlayers } from '../services/playerService';
import { useCompetition } from '../context/CompetitionContext';

function getPositionMeta(position) {
  const neutralClass = 'bg-background-tertiary text-text-primary border-border';
  const labels = { F: 'Forvet', M: 'Orta Saha', D: 'Defans', G: 'Kaleci' };
  return { label: labels[position] || 'Oyuncu', class: neutralClass };
}

export default function PlayerProfilesTab({ selectedSeason, setSelectedSeason, onSelectMatch }) {
  const { competitionKey, hasRichData } = useCompetition();
  const [searchTerm, setSearchTerm] = useState('');
  const [playerList, setPlayerList] = useState([]);
  const [selectedPlayerId, setSelectedPlayerId] = useState(65970);
  const [playerProfile, setPlayerProfile] = useState(null);
  const [playerSeason, setPlayerSeason] = useState(selectedSeason || '2026_27');
  const [selectedMatchGameweek, setSelectedMatchGameweek] = useState('all');
  const [selectedCompetition, setSelectedCompetition] = useState('all');
  const [loadingProfile, setLoadingProfile] = useState(true);
  const [activeModalMatch, setActiveModalMatch] = useState(null);
  const [showMarketValueModal, setShowMarketValueModal] = useState(false);

  // A player id only exists inside one competition, so reset the selection when it changes.
  useEffect(() => {
    setPlayerProfile(null);
    setSearchTerm('');
    setPlayerList([]);
    if (hasRichData) {
      setSelectedPlayerId(65970);
      return undefined;
    }
    // Start on the competition's most valuable player instead of an empty page.
    setSelectedPlayerId(null);
    let cancelled = false;
    searchPlayers({ season: '2026_27', competition: competitionKey, limit: 1 })
      .then(data => {
        if (!cancelled && data.players?.[0]) setSelectedPlayerId(data.players[0].id);
      })
      .catch(error => console.error('Error fetching default player:', error));
    return () => { cancelled = true; };
  }, [competitionKey]);

  useEffect(() => {
    if (selectedSeason) setPlayerSeason(selectedSeason);
  }, [selectedSeason]);

  useEffect(() => {
    if (!searchTerm.trim()) {
      setPlayerList([]);
      return;
    }

    searchPlayers({
      search: searchTerm.trim(),
      season: playerSeason && playerSeason !== 'all' ? playerSeason : undefined,
      competition: competitionKey,
      limit: 20,
    })
      .then(data => setPlayerList(data.players || []))
      .catch(error => console.error('Error fetching player directory:', error));
  }, [searchTerm, playerSeason, competitionKey]);

  useEffect(() => {
    if (!selectedPlayerId) {
      setLoadingProfile(false);
      return;
    }
    setLoadingProfile(true);
    getPlayerProfile(selectedPlayerId, playerSeason, competitionKey)
      .then(data => {
        setPlayerProfile(data);
        setLoadingProfile(false);
      })
      .catch(error => {
        console.error('Error fetching player profile:', error);
        setPlayerProfile(null);
        setLoadingProfile(false);
      });
  }, [selectedPlayerId, playerSeason, competitionKey]);

  const player = playerProfile?.player;
  const stats = playerProfile?.season_stats || {};
  const leagueMatches = useMemo(
    () => (playerProfile?.matches || []).filter(match => Number(match.minutes_played) > 0),
    [playerProfile?.matches],
  );
  // Champions League / Europa League appearances join the same history, ordered by kick-off.
  const europeanMatches = useMemo(
    () => (playerProfile?.european?.matches || []).filter(match => Number(match.minutes_played) > 0),
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
    leagueMatches.forEach(match => {
      const week = Math.round(Number(match.gameweek));
      if (!Number.isNaN(week) && week > 0) weeks.add(week);
    });
    return [...weeks].sort((a, b) => a - b);
  }, [leagueMatches]);

  useEffect(() => { setSelectedMatchGameweek('all'); setSelectedCompetition('all'); }, [selectedPlayerId, playerSeason]);

  const filteredMatches = useMemo(() => {
    let list = playedMatches;
    if (selectedCompetition !== 'all') list = list.filter(match => (match.competition?.key || competitionKey) === selectedCompetition);
    // gameweeks are a league concept: a chosen week narrows the list to that league round
    if (selectedMatchGameweek !== 'all') {
      list = list.filter(match => (match.competition?.key || competitionKey) === competitionKey && Math.round(Number(match.gameweek)) === Number(selectedMatchGameweek));
    }
    return list;
  }, [playedMatches, selectedMatchGameweek, selectedCompetition, competitionKey]);

  const handleSeasonChange = (season) => {
    setPlayerSeason(season);
    setSelectedSeason?.(season);
  };

  const handleSelectMatch = (match) => {
    if (onSelectMatch) onSelectMatch(match);
    else setActiveModalMatch(match);
  };

  const position = player ? getPositionMeta(player.position) : null;

  return (
    <div className="space-y-6">
      <PlayerSearchPanel
        searchTerm={searchTerm}
        onSearchChange={setSearchTerm}
        players={playerList}
        selectedPlayerId={selectedPlayerId}
        onSelectPlayer={setSelectedPlayerId}
      />

      {player && (
        <PlayerProfileHeader
          player={player}
          stats={stats}
          team={team}
          position={position}
          season={playerSeason}
          onSeasonChange={handleSeasonChange}
          onOpenMarketValue={() => setShowMarketValueModal(true)}
        />
      )}

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
        loading={loadingProfile}
        season={playerSeason}
        onSelectMatch={handleSelectMatch}
      />

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
