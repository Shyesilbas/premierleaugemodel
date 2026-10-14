import React, { useState, useEffect, useMemo } from 'react';
import { TEAMS, getTeam } from '../data/teams';
import { 
  Search, 
  User, 
  Clock, 
  ChevronRight, 
  Calendar, 
  Shield, 
  X
} from 'lucide-react';
import MatchDetailModal from './MatchDetailModal';

function parseKickoff(label) {
  if (!label) return { date: '-', time: '' };
  const parts = String(label).split(',');
  if (parts.length < 2) return { date: parts[0].trim(), time: '' };
  return {
    date: parts[0].trim(),
    time: parts[1].trim().replace(/\s+(BST|GMT)/gi, ''),
  };
}

// Reusable Player Avatar with fallback to jersey number and initials
function PlayerAvatar({ player, size = 'md', className = '' }) {
  const [imgError, setImgError] = useState(false);
  
  const sizeClasses = {
    sm: 'w-10 h-10',
    md: 'w-14 h-14',
    lg: 'w-20 h-20',
  };

  const hasPhoto = player?.photo_url && !imgError;

  return (
    <div className={`relative rounded-2xl bg-slate-100 border border-slate-200 flex items-center justify-center shrink-0 overflow-hidden ${sizeClasses[size] || sizeClasses.md} ${className}`}>
      {hasPhoto ? (
        <img
          src={player.photo_url}
          alt={player.name}
          className="w-full h-full object-contain filter drop-shadow-sm transition-transform duration-200 hover:scale-105"
          onError={() => setImgError(true)}
          loading="lazy"
        />
      ) : (
        <div className="flex flex-col items-center justify-center text-slate-700 font-mono font-black">
          {player?.shirt ? (
            <span className={size === 'lg' ? 'text-2xl font-black' : 'text-xs font-bold'}>#{player.shirt}</span>
          ) : (
            <User className={size === 'lg' ? 'w-10 h-10 text-slate-400' : 'w-5 h-5 text-slate-400'} />
          )}
        </div>
      )}
    </div>
  );
}

export default function PlayerProfilesTab({ selectedSeason }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedTeamFilter, setSelectedTeamFilter] = useState('');
  const [selectedPositionFilter, setSelectedPositionFilter] = useState(''); // '', 'F', 'M', 'D', 'G'
  const [playerList, setPlayerList] = useState([]);
  const [selectedPlayerId, setSelectedPlayerId] = useState(65970); // Default Erling Haaland
  const [playerProfile, setPlayerProfile] = useState(null);
  const [playerSeason, setPlayerSeason] = useState(selectedSeason || '2026_27');
  const [selectedMatchGameweek, setSelectedMatchGameweek] = useState('all');
  const [loadingList, setLoadingList] = useState(false);
  const [loadingProfile, setLoadingProfile] = useState(true);
  const [activeModalMatch, setActiveModalMatch] = useState(null);

  // Sync incoming season
  useEffect(() => {
    if (selectedSeason) {
      setPlayerSeason(selectedSeason);
    }
  }, [selectedSeason]);

  // Fetch player search directory
  useEffect(() => {
    const hasDirectoryFilter = searchTerm.trim() || selectedTeamFilter || selectedPositionFilter;
    if (!hasDirectoryFilter) {
      setPlayerList([]);
      setLoadingList(false);
      return;
    }

    setLoadingList(true);
    const query = new URLSearchParams();
    if (searchTerm.trim()) query.append('search', searchTerm.trim());
    if (selectedTeamFilter) query.append('team_id', selectedTeamFilter);
    query.append('limit', '20');

    fetch(`/api/players?${query.toString()}`)
      .then(res => res.json())
      .then(data => {
        let list = data.players || [];
        if (selectedPositionFilter) {
          list = list.filter(p => p.position === selectedPositionFilter);
        }
        setPlayerList(list);
        setLoadingList(false);
      })
      .catch(err => {
        console.error('Error fetching player directory:', err);
        setLoadingList(false);
      });
  }, [searchTerm, selectedTeamFilter, selectedPositionFilter]);

  // Fetch detailed player profile & match logs
  useEffect(() => {
    if (!selectedPlayerId) return;
    setLoadingProfile(true);
    fetch(`/api/players/profile?player_id=${selectedPlayerId}&season=${playerSeason}`)
      .then(res => res.json())
      .then(data => {
        setPlayerProfile(data);
        setLoadingProfile(false);
      })
      .catch(err => {
        console.error('Error fetching player profile:', err);
        setLoadingProfile(false);
      });
  }, [selectedPlayerId, playerSeason]);

  const pData = playerProfile?.player;
  const pStats = playerProfile?.season_stats || {};

  // Only include appearances that were actually played; omit unplayed fixtures.
  const playedMatches = useMemo(() => (playerProfile?.matches || []).filter(
    match => Number(match.minutes_played) > 0
  ), [playerProfile?.matches]);

  // Dynamically resolve the player's active team for the chosen season
  const activeTeamId = useMemo(() => {
    if (playedMatches.length) {
      return playedMatches[playedMatches.length - 1].team_id;
    }
    return pData?.teamId;
  }, [playedMatches, pData?.teamId]);

  const activeTeamName = useMemo(() => {
    if (playedMatches.length) {
      return playedMatches[playedMatches.length - 1].team_name;
    }
    return pData?.teamName;
  }, [playedMatches, pData?.teamName]);

  const teamMeta = activeTeamId ? getTeam(activeTeamId, activeTeamName) : (pData ? getTeam(pData.teamId, pData.teamName) : null);

  // Unique gameweeks in the player's played matches
  const playedGameweeks = useMemo(() => {
    if (!playedMatches.length) return [];
    const set = new Set();
    playedMatches.forEach(m => {
      const gwNum = Math.round(Number(m.gameweek));
      if (!isNaN(gwNum) && gwNum > 0) set.add(gwNum);
    });
    return Array.from(set).sort((a, b) => a - b);
  }, [playedMatches]);

  // Reset the optional week filter when changing player or season.
  useEffect(() => {
    setSelectedMatchGameweek('all');
  }, [selectedPlayerId, playerSeason]);

  // Filtered match records for currently selected week
  const filteredMatches = useMemo(() => {
    if (!playedMatches.length) return [];
    if (selectedMatchGameweek === 'all') {
      return playedMatches;
    }
    return playedMatches.filter(m => Math.round(Number(m.gameweek)) === Number(selectedMatchGameweek));
  }, [playedMatches, selectedMatchGameweek]);

  // Position label and semantic badge styling
  const getPosMeta = (pos) => {
    const neutralClass = 'bg-slate-100 text-slate-700 border-slate-200';
    switch (pos) {
      case 'F':
        return { label: 'Forvet', class: neutralClass };
      case 'M':
        return { label: 'Orta Saha', class: neutralClass };
      case 'D':
        return { label: 'Defans', class: neutralClass };
      case 'G':
        return { label: 'Kaleci', class: neutralClass };
      default:
        return { label: 'Oyuncu', class: neutralClass };
    }
  };

  const posMeta = pData ? getPosMeta(pData.position) : null;

  return (
    <div className="space-y-6">

      {/* Filter and Search Control Bar */}
      <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm space-y-3">
        <div className="flex flex-col md:flex-row items-center gap-3">
          
          {/* Search Input */}
          <div className="relative flex-1 w-full">
            <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Oyuncu veya kulüp ara"
              className="w-full bg-white border border-slate-200 rounded-xl pl-10 pr-9 py-2.5 text-sm font-medium text-slate-900 placeholder-slate-400 outline-none focus:border-slate-400 transition-all"
            />
            {searchTerm && (
              <button
                onClick={() => setSearchTerm('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-200 transition-colors"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Team filter dropdown */}
          <div className="w-full md:w-56 shrink-0">
            <select
              value={selectedTeamFilter}
              onChange={(e) => setSelectedTeamFilter(e.target.value)}
              className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2.5 text-sm font-semibold text-slate-800 outline-none focus:border-slate-400 transition-all cursor-pointer"
            >
              <option value="">Tüm Kulüpler (20 Takım)</option>
              {TEAMS.map(t => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
          </div>

        </div>

        {/* Position Filter Pills */}
        <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-100">
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-thin">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mr-1">
              Mevki:
            </span>
            {[
              { id: '', label: 'Tümü' },
              { id: 'F', label: 'Forvetler' },
              { id: 'M', label: 'Orta Sahalar' },
              { id: 'D', label: 'Defanslar' },
              { id: 'G', label: 'Kaleciler' },
            ].map(p => (
              <button
                key={p.id}
                onClick={() => setSelectedPositionFilter(p.id)}
                className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all whitespace-nowrap ${
                  selectedPositionFilter === p.id
                    ? 'bg-slate-900 text-white'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>

          <span className="text-[11px] text-slate-500 font-mono font-medium">
            {loadingList
              ? 'Oyuncular aranıyor…'
              : searchTerm.trim() || selectedTeamFilter || selectedPositionFilter
              ? `${playerList.length} sonuç`
              : 'Oyuncu değiştirmek için arayın'}
          </span>
        </div>

      </div>

      {/* Search results appear only after the user applies a filter. */}
      {playerList.length > 0 && (searchTerm.trim() || selectedTeamFilter || selectedPositionFilter) && (
        <div className="bg-white border border-slate-200 rounded-2xl p-3 shadow-sm">
          <div className="flex items-center gap-2 overflow-x-auto pb-1.5 scrollbar-thin">
            {playerList.slice(0, 24).map(pl => {
              const isSelected = pl.id === selectedPlayerId;
              const plTeam = getTeam(pl.teamId, pl.teamName);
              return (
                <button
                  key={pl.id}
                  onClick={() => setSelectedPlayerId(pl.id)}
                  className={`flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-bold transition-all shrink-0 border ${
                    isSelected
                      ? 'bg-slate-100 text-slate-950 border-slate-400'
                      : 'bg-slate-50 hover:bg-slate-100 text-slate-700 border-slate-200'
                  }`}
                >
                  {/* Photo thumbnail */}
                  <PlayerAvatar player={pl} size="sm" className="w-7 h-7 rounded-lg" />

                  <div className="text-left min-w-0">
                    <div className="flex items-center gap-1.5 leading-tight">
                      <span className="truncate max-w-[120px]">{pl.name}</span>
                      {pl.shirt ? (
                        <span className="rounded bg-slate-200 px-1 font-mono text-[10px] font-bold text-slate-700">
                          #{pl.shirt}
                        </span>
                      ) : null}
                    </div>
                    <span className="block max-w-[110px] truncate text-[10px] font-medium text-slate-500">
                      {plTeam.short || pl.teamName}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Player identity and season summary */}
      {pData && (
        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="flex flex-col gap-5 p-4 sm:flex-row sm:items-center sm:p-6">
            <PlayerAvatar player={pData} size="lg" className="h-20 w-20 rounded-2xl" />
            <div className="min-w-0 flex-1 text-center sm:text-left">
              <div className="flex flex-wrap items-center justify-center gap-2 sm:justify-start">
                <h2 className="text-2xl font-black tracking-tight text-slate-950">{pData.name}</h2>
                {posMeta && <span className={`rounded-md border px-2 py-0.5 text-[11px] font-semibold ${posMeta.class}`}>{posMeta.label}</span>}
              </div>
              <div className="mt-1.5 flex flex-wrap items-center justify-center gap-x-3 gap-y-1 text-sm text-slate-600 sm:justify-start">
                {teamMeta && <span className="inline-flex items-center gap-1.5 font-semibold text-slate-800"><img src={teamMeta.badge} alt="" className="h-4 w-4 object-contain" onError={(e) => { e.target.src = '/badges/1.svg'; }} />{teamMeta.name}</span>}
                {pData.country && <span>{pData.country}</span>}
                {pData.shirt && <span>Forma no: {pData.shirt}</span>}
              </div>
              <p className="mt-2 text-xs text-slate-500">
                Premier League kariyeri <span className="mx-1">·</span>{pData.total_appearances || 0} maç <span className="mx-1">·</span>{pData.total_goals || 0} gol <span className="mx-1">·</span>{pData.total_assists || 0} asist
              </p>
            </div>
            <label className="flex shrink-0 items-center gap-2 self-center text-xs font-semibold text-slate-500 sm:self-start">
              Sezon
              <select value={playerSeason} onChange={(e) => setPlayerSeason(e.target.value)} className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-800 outline-none focus:border-slate-400">
                <option value="2026_27">2026-27</option>
                <option value="2025_26">2025-26</option>
                <option value="2024_25">2024-25</option>
                <option value="2023_24">2023-24</option>
                <option value="2022_23">2022-23</option>
                <option value="all">Tüm sezonlar</option>
              </select>
            </label>
          </div>

          <div className="grid grid-cols-2 divide-x divide-y divide-slate-200 border-t border-slate-200 sm:grid-cols-4 sm:divide-y-0">
            <div className="px-4 py-3 text-center sm:text-left sm:px-6"><span className="block text-[10px] font-semibold uppercase tracking-wide text-slate-500">Maç</span><strong className="text-lg font-bold tabular-nums text-slate-900">{pStats.appearances || 0}</strong></div>
            <div className="px-4 py-3 text-center sm:text-left sm:px-6"><span className="block text-[10px] font-semibold uppercase tracking-wide text-slate-500">Dakika</span><strong className="text-lg font-bold tabular-nums text-slate-900">{pStats.minutes || 0}</strong></div>
            <div className="px-4 py-3 text-center sm:text-left sm:px-6"><span className="block text-[10px] font-semibold uppercase tracking-wide text-slate-500">Gol</span><strong className="text-lg font-bold tabular-nums text-slate-900">{pStats.goals || 0}</strong></div>
            <div className="px-4 py-3 text-center sm:text-left sm:px-6"><span className="block text-[10px] font-semibold uppercase tracking-wide text-slate-500">Asist</span><strong className="text-lg font-bold tabular-nums text-slate-900">{pStats.assists || 0}</strong></div>
          </div>
        </section>
      )}

      {/* Match history in the same compact row layout as Team Profiles */}
      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="flex flex-col gap-3 border-b border-slate-100 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-5">
          <div className="flex items-center gap-2">
            <Calendar className="h-4 w-4 text-slate-500" />
            <div>
              <h3 className="text-sm font-bold text-slate-900">Maç geçmişi</h3>
              <p className="text-xs text-slate-500">{playedMatches.length} oynanmış maç · {playerSeason === 'all' ? 'Tüm sezonlar' : playerSeason.replace('_', '-')}</p>
            </div>
          </div>
          {playedGameweeks.length > 0 && (
            <label className="flex items-center gap-2 text-xs font-medium text-slate-500">
              Hafta
              <select value={selectedMatchGameweek} onChange={(e) => setSelectedMatchGameweek(e.target.value)} className="min-w-36 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-800 outline-none focus:border-slate-400">
                <option value="all">Tüm haftalar</option>
                {playedGameweeks.map((gw) => <option key={gw} value={gw}>Hafta {gw}</option>)}
              </select>
            </label>
          )}
        </div>

        {loadingProfile ? (
          <div className="py-16 text-center">
            <div className="w-7 h-7 border-3 border-[#38003c] border-t-transparent rounded-full animate-spin mx-auto mb-2" />
            <p className="text-xs font-bold text-slate-600">Oyuncu maç kayıtları yükleniyor...</p>
          </div>
        ) : !playedMatches.length ? (
          <div className="py-12 text-center text-xs text-slate-500 font-medium">
            Seçilen sezonda oyuncunun süre aldığı maç bulunamadı.
          </div>
        ) : filteredMatches.length === 0 ? (
          <div className="py-12 text-center text-xs text-slate-500 font-medium bg-slate-50 border border-slate-200 rounded-xl">
            Bu haftada ({selectedMatchGameweek}. Hafta) oyuncunun süre aldığı karşılaşma kaydı bulunmuyor.
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {filteredMatches.map(m => {
              const opp = getTeam(m.opponent_id, m.opponent_name);
              const matchTeam = getTeam(m.team_id, m.team_name);
              const goalsCount = m.goals || 0;
              const assistsCount = m.assists || 0;
              const isPlayed = m.team_score !== null && m.team_score !== undefined;
              const kickoff = parseKickoff(m.kickoff);
              const homeTeam = m.is_home ? matchTeam : opp;
              const awayTeam = m.is_home ? opp : matchTeam;
              const homeScore = m.is_home ? m.team_score : m.opp_score;
              const awayScore = m.is_home ? m.opp_score : m.team_score;

              // Synthetic match object for MatchDetailModal (marked as COMPLETED for played match stats)
              const modalMatchObj = {
                match_id: m.match_id,
                status: isPlayed ? 'COMPLETED' : 'UNPLAYED',
                gameweek: m.gameweek,
                kickoff_label: m.kickoff,
                home_id: homeTeam.id,
                home_name: homeTeam.name,
                home_score: homeScore,
                away_id: awayTeam.id,
                away_name: awayTeam.name,
                away_score: awayScore,
                ground_name: 'Premier League',
              };

              return (
                <button
                  key={m.match_id}
                  onClick={() => setActiveModalMatch(modalMatchObj)}
                  className="group flex w-full flex-col gap-2.5 px-4 py-3 text-left transition-colors hover:bg-slate-50 sm:flex-row sm:items-center sm:gap-3 sm:px-5"
                >
                  <div className="flex items-center justify-between gap-2 text-[11px] text-slate-500 sm:w-40 sm:shrink-0 sm:flex-col sm:items-start sm:gap-1">
                    <span className="inline-flex items-center gap-1.5 font-semibold text-slate-700"><Clock className="hidden h-3.5 w-3.5 text-slate-400 sm:block" />{kickoff.date}</span>
                    <span className="flex items-center gap-2">
                      {playerSeason === 'all' && <span>{m.season?.replace('_', '-')}</span>}
                      <span className="font-mono">H{Math.round(Number(m.gameweek) || 1)}</span>
                      <span>{m.is_home ? 'İç saha' : 'Deplasman'}</span>
                    </span>
                  </div>

                  <div className="flex min-w-0 flex-1 items-center justify-center gap-1.5 sm:gap-3">
                    <div className="flex min-w-0 flex-1 items-center justify-end gap-1.5 text-right">
                      <span className={`truncate text-xs ${m.is_home ? 'font-bold text-slate-950' : 'font-medium text-slate-600'}`}>{homeTeam.short || homeTeam.name}</span>
                      <img src={homeTeam.badge} alt={homeTeam.name} className="h-5 w-5 shrink-0 object-contain" onError={(e) => { e.target.src = '/badges/1.svg'; }} />
                    </div>
                    <span className="min-w-[58px] shrink-0 text-center font-mono text-xs font-black text-slate-900">
                      {isPlayed ? `${homeScore} - ${awayScore}` : kickoff.time || 'vs'}
                    </span>
                    <div className="flex min-w-0 flex-1 items-center gap-1.5">
                      <img src={awayTeam.badge} alt={awayTeam.name} className="h-5 w-5 shrink-0 object-contain" onError={(e) => { e.target.src = '/badges/1.svg'; }} />
                      <span className={`truncate text-xs ${!m.is_home ? 'font-bold text-slate-950' : 'font-medium text-slate-600'}`}>{awayTeam.short || awayTeam.name}</span>
                    </div>
                  </div>

                  <div className="flex items-center justify-between gap-3 border-t border-slate-100 pt-2 text-[11px] text-slate-600 sm:w-56 sm:shrink-0 sm:justify-end sm:border-0 sm:pt-0">
                    <span className="whitespace-nowrap"><strong className="font-semibold text-slate-800">{m.minutes_played || 0}'</strong> · {m.started ? 'İlk 11' : 'Yedek'}</span>
                    <span className="whitespace-nowrap">Gol <strong className="text-slate-900">{goalsCount}</strong><span className="mx-1.5 text-slate-300">|</span>Asist <strong className="text-slate-900">{assistsCount}</strong></span>
                    <ChevronRight className="hidden h-3.5 w-3.5 text-slate-300 transition group-hover:translate-x-0.5 group-hover:text-slate-600 sm:block" />
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </section>

      {/* Match Detail Modal */}
      {activeModalMatch && (
        <MatchDetailModal
          match={activeModalMatch}
          onClose={() => setActiveModalMatch(null)}
        />
      )}

    </div>
  );
}
