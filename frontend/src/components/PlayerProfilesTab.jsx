import React, { useEffect, useMemo, useState } from 'react';
import { getTeam } from '../data/teams';
import MatchDetailModal from './MatchDetailModal';
import PlayerMarketValueHistoryModal from './PlayerMarketValueHistoryModal';
import PlayerSearchPanel from './player-profile/PlayerSearchPanel';
import PlayerProfileHeader from './player-profile/PlayerProfileHeader';
import PlayerMatchHistory from './player-profile/PlayerMatchHistory';
import { getPlayerProfile, searchPlayers } from '../services/playerService';

function getPositionMeta(position) {
  const neutralClass = 'bg-slate-100 text-slate-700 border-slate-200';
  const labels = { F: 'Forvet', M: 'Orta Saha', D: 'Defans', G: 'Kaleci' };
  return { label: labels[position] || 'Oyuncu', class: neutralClass };
}

export default function PlayerProfilesTab({ selectedSeason, setSelectedSeason, onSelectMatch }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [playerList, setPlayerList] = useState([]);
  const [selectedPlayerId, setSelectedPlayerId] = useState(65970);
  const [playerProfile, setPlayerProfile] = useState(null);
  const [playerSeason, setPlayerSeason] = useState(selectedSeason || '2026_27');
  const [selectedMatchGameweek, setSelectedMatchGameweek] = useState('all');
  const [loadingProfile, setLoadingProfile] = useState(true);
  const [activeModalMatch, setActiveModalMatch] = useState(null);
  const [showMarketValueModal, setShowMarketValueModal] = useState(false);

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
      limit: 20,
    })
      .then(data => setPlayerList(data.players || []))
      .catch(error => console.error('Error fetching player directory:', error));
  }, [searchTerm, playerSeason]);

  useEffect(() => {
    if (!selectedPlayerId) return;
    setLoadingProfile(true);
    getPlayerProfile(selectedPlayerId, playerSeason)
      .then(data => {
        setPlayerProfile(data);
        setLoadingProfile(false);
      })
      .catch(error => {
        console.error('Error fetching player profile:', error);
        setLoadingProfile(false);
      });
  }, [selectedPlayerId, playerSeason]);

  const player = playerProfile?.player;
  const stats = playerProfile?.season_stats || {};
  const playedMatches = useMemo(
    () => (playerProfile?.matches || []).filter(match => Number(match.minutes_played) > 0),
    [playerProfile?.matches],
  );
  const lastPlayedMatch = playedMatches[playedMatches.length - 1];
  const teamId = lastPlayedMatch?.team_id ?? player?.teamId;
  const teamName = lastPlayedMatch?.team_name ?? player?.teamName;
  const team = teamId ? getTeam(teamId, teamName) : (player ? getTeam(player.teamId, player.teamName) : null);

  const playedGameweeks = useMemo(() => {
    const weeks = new Set();
    playedMatches.forEach(match => {
      const week = Math.round(Number(match.gameweek));
      if (!Number.isNaN(week) && week > 0) weeks.add(week);
    });
    return [...weeks].sort((a, b) => a - b);
  }, [playedMatches]);

  useEffect(() => setSelectedMatchGameweek('all'), [selectedPlayerId, playerSeason]);

  const filteredMatches = useMemo(() => {
    if (selectedMatchGameweek === 'all') return playedMatches;
    return playedMatches.filter(match => Math.round(Number(match.gameweek)) === Number(selectedMatchGameweek));
  }, [playedMatches, selectedMatchGameweek]);

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
