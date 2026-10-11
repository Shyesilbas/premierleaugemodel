import React, { useState, useEffect, useMemo } from 'react';
import { TEAMS, getTeam } from '../data/teams';
import { 
  Search, 
  User, 
  Clock, 
  ChevronRight, 
  ChevronLeft,
  Activity, 
  Award, 
  Calendar, 
  Shield, 
  Target, 
  Filter, 
  X,
  MapPin,
  Trophy,
  Zap
} from 'lucide-react';
import MatchDetailModal from './MatchDetailModal';

// Reusable Player Avatar with fallback to jersey number and initials
function PlayerAvatar({ player, size = 'md', className = '' }) {
  const [imgError, setImgError] = useState(false);
  
  const sizeClasses = {
    sm: 'w-10 h-10',
    md: 'w-14 h-14',
    lg: 'w-24 h-24 sm:w-28 sm:h-28',
  };

  const hasPhoto = player?.photo_url && !imgError;

  return (
    <div className={`relative rounded-2xl bg-gradient-to-b from-slate-100 to-slate-200 border border-slate-300 flex items-center justify-center shrink-0 overflow-hidden shadow-inner ${sizeClasses[size] || sizeClasses.md} ${className}`}>
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
    setLoadingList(true);
    const query = new URLSearchParams();
    if (searchTerm) query.append('search', searchTerm);
    if (selectedTeamFilter) query.append('team_id', selectedTeamFilter);
    query.append('limit', '50');

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
  const teamMeta = pData ? getTeam(pData.teamId, pData.teamName) : null;

  // Unique played gameweeks sorted
  const playedGameweeks = useMemo(() => {
    if (!playerProfile?.matches?.length) return [];
    const set = new Set();
    playerProfile.matches.forEach(m => {
      const gwNum = Math.round(Number(m.gameweek));
      if (!isNaN(gwNum) && gwNum > 0) set.add(gwNum);
    });
    return Array.from(set).sort((a, b) => a - b);
  }, [playerProfile?.matches]);

  // When playerProfile or playedGameweeks changes, default to latest played gameweek
  useEffect(() => {
    if (playedGameweeks.length > 0) {
      setSelectedMatchGameweek(String(playedGameweeks[playedGameweeks.length - 1]));
    } else {
      setSelectedMatchGameweek('all');
    }
  }, [playedGameweeks]);

  // Filtered match records for currently selected week
  const filteredMatches = useMemo(() => {
    if (!playerProfile?.matches) return [];
    if (selectedMatchGameweek === 'all') {
      return playerProfile.matches;
    }
    return playerProfile.matches.filter(m => Math.round(Number(m.gameweek)) === Number(selectedMatchGameweek));
  }, [playerProfile?.matches, selectedMatchGameweek]);

  // Position label and semantic badge styling
  const getPosMeta = (pos) => {
    switch (pos) {
      case 'F':
        return { label: 'Forvet', class: 'bg-rose-50 text-rose-800 border-rose-200' };
      case 'M':
        return { label: 'Orta Saha', class: 'bg-emerald-50 text-emerald-800 border-emerald-200' };
      case 'D':
        return { label: 'Defans', class: 'bg-sky-50 text-sky-800 border-sky-200' };
      case 'G':
        return { label: 'Kaleci', class: 'bg-amber-50 text-amber-800 border-amber-200' };
      default:
        return { label: 'Oyuncu', class: 'bg-slate-100 text-slate-700 border-slate-200' };
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
              placeholder="Oyuncu veya kulüp ara (örn: Haaland, Salah, Saka, Palmer, Son, Arsenal)..."
              className="w-full bg-slate-50 border border-slate-200 rounded-xl pl-10 pr-9 py-2.5 text-xs font-medium text-slate-900 placeholder-slate-400 outline-none focus:border-[#38003c] focus:bg-white transition-all"
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
              className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2.5 text-xs font-bold text-slate-800 outline-none focus:border-[#38003c] transition-all cursor-pointer"
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
                    ? 'bg-[#38003c] text-white shadow-xs'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>

          <span className="text-[11px] text-slate-500 font-mono font-medium">
            {playerList.length} Oyuncu Listelendi
          </span>
        </div>

      </div>

      {/* Fast Player Selector Carousel */}
      {playerList.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-2xl p-3 shadow-sm">
          <div className="flex items-center gap-2 overflow-x-auto pb-1.5 scrollbar-thin">
            {playerList.slice(0, 24).map(pl => {
              const isSelected = pl.id === selectedPlayerId;
              const plTeam = getTeam(pl.teamId, pl.teamName);
              const plPos = getPosMeta(pl.position);

              return (
                <button
                  key={pl.id}
                  onClick={() => setSelectedPlayerId(pl.id)}
                  className={`flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-bold transition-all shrink-0 border ${
                    isSelected
                      ? 'bg-[#38003c] text-white border-[#38003c] shadow-sm'
                      : 'bg-slate-50 hover:bg-slate-100 text-slate-700 border-slate-200'
                  }`}
                >
                  {/* Photo thumbnail */}
                  <PlayerAvatar player={pl} size="sm" className="w-7 h-7 rounded-lg" />

                  <div className="text-left min-w-0">
                    <div className="flex items-center gap-1.5 leading-tight">
                      <span className="truncate max-w-[120px]">{pl.name}</span>
                      {pl.shirt ? (
                        <span className={`font-mono text-[10px] px-1 py-0.2 rounded font-black ${
                          isSelected ? 'bg-white/20 text-white' : 'bg-slate-200 text-slate-800'
                        }`}>
                          #{pl.shirt}
                        </span>
                      ) : null}
                    </div>
                    <span className={`text-[10px] block truncate max-w-[110px] font-medium ${
                      isSelected ? 'text-white/80' : 'text-slate-500'
                    }`}>
                      {plTeam.short || pl.teamName}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Modern Player Hero Card */}
      {pData && (
        <div className="bg-white border border-slate-200 rounded-3xl p-6 md:p-8 shadow-sm flex flex-col lg:flex-row items-center justify-between gap-6 relative overflow-hidden">
          
          {/* Left: Player Photo, Jersey Number & Core Identity */}
          <div className="flex flex-col sm:flex-row items-center sm:items-start text-center sm:text-left gap-5 w-full lg:w-auto">
            
            {/* Player Headshot Photo Card */}
            <div className="relative group shrink-0">
              <PlayerAvatar 
                player={pData} 
                size="lg" 
                className="w-28 h-28 sm:w-32 sm:h-32 rounded-3xl bg-gradient-to-b from-slate-50 via-slate-100 to-slate-200 border-2 border-slate-200 shadow-md p-1"
              />
              
              {/* Bold Jersey Number Corner Ribbon */}
              {pData.shirt && (
                <div className="absolute -top-2 -left-2 bg-[#38003c] text-white px-2.5 py-1 rounded-xl font-mono font-black text-sm shadow-md border-2 border-white flex items-center justify-center">
                  #{pData.shirt}
                </div>
              )}

              {/* Club Badge Overlay */}
              {teamMeta && (
                <div className="absolute -bottom-2 -right-2 bg-white p-1.5 rounded-xl border border-slate-200 shadow-md w-9 h-9 flex items-center justify-center">
                  <img 
                    src={teamMeta.badge} 
                    alt={teamMeta.name} 
                    className="w-6 h-6 object-contain"
                    onError={(e) => { e.target.src = '/badges/1.svg'; }}
                  />
                </div>
              )}
            </div>

            {/* Identity Texts */}
            <div className="space-y-1.5 min-w-0">
              <div className="flex flex-wrap items-center justify-center sm:justify-start gap-2">
                <h2 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
                  {pData.name}
                </h2>
                
                {/* Position Badge */}
                {posMeta && (
                  <span className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full border ${posMeta.class}`}>
                    {posMeta.label}
                  </span>
                )}
              </div>

              {/* Club & Country Details */}
              <div className="flex flex-wrap items-center justify-center sm:justify-start gap-3 text-xs text-slate-600 font-medium">
                {teamMeta && (
                  <div className="flex items-center gap-1.5 font-bold text-slate-900">
                    <Shield className="w-3.5 h-3.5 text-[#38003c]" />
                    <span>{teamMeta.name}</span>
                  </div>
                )}
                {pData.country && (
                  <div className="flex items-center gap-1 text-slate-500 font-medium">
                    <span>•</span>
                    <span>{pData.country}</span>
                  </div>
                )}
                {pData.shirt && (
                  <div className="flex items-center gap-1 font-mono text-slate-500">
                    <span>•</span>
                    <span>Forma No: <strong>{pData.shirt}</strong></span>
                  </div>
                )}
              </div>

              {/* Career totals summary line */}
              <p className="text-[11px] text-slate-500 font-medium pt-1">
                Kayıtlı Premier League İstatistiği: <strong className="text-slate-800 font-mono">{pData.total_appearances} Maç</strong> • <strong className="text-emerald-700 font-mono">{pData.total_goals} Gol</strong> • <strong className="text-purple-700 font-mono">{pData.total_assists} Asist</strong>
              </p>
            </div>

          </div>

          {/* Right: Season Filter Switcher & Big Stat Cards */}
          <div className="flex flex-col items-center lg:items-end gap-4 w-full lg:w-auto">
            
            {/* Season Switcher Pills */}
            <div className="flex items-center bg-slate-100 p-1 rounded-xl border border-slate-200 gap-1">
              <button
                onClick={() => setPlayerSeason('2026_27')}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  playerSeason === '2026_27'
                    ? 'bg-[#38003c] text-white shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                2026-27
              </button>
              <button
                onClick={() => setPlayerSeason('2025_26')}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  playerSeason === '2025_26'
                    ? 'bg-[#38003c] text-white shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                2025-26
              </button>
              <button
                onClick={() => setPlayerSeason('2024_25')}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  playerSeason === '2024_25'
                    ? 'bg-[#38003c] text-white shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                2024-25
              </button>
              <button
                onClick={() => setPlayerSeason('all')}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  playerSeason === 'all'
                    ? 'bg-[#38003c] text-white shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Tüm Sezonlar
              </button>
            </div>

            {/* 4 Large Clean Statistic Cards */}
            <div className="grid grid-cols-4 gap-2.5 w-full sm:w-auto font-mono">
              <div className="bg-slate-50 border border-slate-200 rounded-2xl p-3 text-center min-w-[70px] sm:min-w-[85px] shadow-xs">
                <span className="text-[10px] text-slate-500 font-sans font-bold block uppercase tracking-wider">MAÇ</span>
                <strong className="text-slate-900 text-base sm:text-lg font-black">{pStats.appearances || 0}</strong>
              </div>
              <div className="bg-sky-50 border border-sky-200 rounded-2xl p-3 text-center min-w-[70px] sm:min-w-[85px] shadow-xs">
                <span className="text-[10px] text-sky-700 font-sans font-bold block uppercase tracking-wider">DAKİKA</span>
                <strong className="text-sky-900 text-base sm:text-lg font-black">{pStats.minutes || 0}'</strong>
              </div>
              <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-3 text-center min-w-[70px] sm:min-w-[85px] shadow-xs">
                <span className="text-[10px] text-emerald-700 font-sans font-bold block uppercase tracking-wider">GOL</span>
                <strong className="text-emerald-800 text-base sm:text-lg font-black">{pStats.goals || 0}</strong>
              </div>
              <div className="bg-purple-50 border border-purple-200 rounded-2xl p-3 text-center min-w-[70px] sm:min-w-[85px] shadow-xs">
                <span className="text-[10px] text-purple-700 font-sans font-bold block uppercase tracking-wider">ASİST</span>
                <strong className="text-purple-900 text-base sm:text-lg font-black">{pStats.assists || 0}</strong>
              </div>
            </div>

          </div>

        </div>
      )}

      {/* Match-by-Match Preview Log */}
      <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-[#38003c]" />
            <h3 className="text-sm font-black text-slate-900">
              {pData?.name} — Maç Performans Günlüğü & Skor Önizlemeleri
            </h3>
          </div>
          <span className="text-xs font-mono font-bold text-slate-500">
            {playerProfile?.matches?.length || 0} Maç Kaydı
          </span>
        </div>

        {/* Week-by-Week Navigation Toolbar */}
        {playedGameweeks.length > 0 && (
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-slate-50 border border-slate-200/90 p-3 rounded-xl">
            
            {/* Step Controls: Önceki Hafta & Sonraki Hafta */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => {
                  if (selectedMatchGameweek === 'all') {
                    setSelectedMatchGameweek(String(playedGameweeks[0]));
                    return;
                  }
                  const currentIdx = playedGameweeks.indexOf(Number(selectedMatchGameweek));
                  if (currentIdx > 0) {
                    setSelectedMatchGameweek(String(playedGameweeks[currentIdx - 1]));
                  }
                }}
                disabled={selectedMatchGameweek !== 'all' && playedGameweeks.indexOf(Number(selectedMatchGameweek)) <= 0}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold bg-white border border-slate-200 text-slate-700 hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed shadow-xs transition-all"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                <span>Önceki Hafta</span>
              </button>

              <div className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-xs font-mono font-black text-[#38003c] shadow-xs">
                {selectedMatchGameweek === 'all' ? (
                  <span>Tüm Haftalar ({playedGameweeks.length} Hafta)</span>
                ) : (
                  <span>Hafta {selectedMatchGameweek}</span>
                )}
              </div>

              <button
                onClick={() => {
                  if (selectedMatchGameweek === 'all') {
                    setSelectedMatchGameweek(String(playedGameweeks[playedGameweeks.length - 1]));
                    return;
                  }
                  const currentIdx = playedGameweeks.indexOf(Number(selectedMatchGameweek));
                  if (currentIdx >= 0 && currentIdx < playedGameweeks.length - 1) {
                    setSelectedMatchGameweek(String(playedGameweeks[currentIdx + 1]));
                  }
                }}
                disabled={selectedMatchGameweek !== 'all' && playedGameweeks.indexOf(Number(selectedMatchGameweek)) >= playedGameweeks.length - 1}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold bg-white border border-slate-200 text-slate-700 hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed shadow-xs transition-all"
              >
                <span>Sonraki Hafta</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Quick Week Pill List + All Button */}
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 pt-1 scrollbar-thin">
              <button
                onClick={() => setSelectedMatchGameweek('all')}
                className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all whitespace-nowrap ${
                  selectedMatchGameweek === 'all'
                    ? 'bg-[#38003c] text-white shadow-xs'
                    : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-100'
                }`}
              >
                Tümü ({playerProfile?.matches?.length})
              </button>
              {playedGameweeks.map(gw => {
                const isSelected = String(selectedMatchGameweek) === String(gw);
                return (
                  <button
                    key={gw}
                    onClick={() => setSelectedMatchGameweek(String(gw))}
                    className={`px-2.5 py-1 rounded-lg text-xs font-mono font-bold transition-all whitespace-nowrap ${
                      isSelected
                        ? 'bg-[#38003c] text-white shadow-xs'
                        : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-100'
                    }`}
                  >
                    Hafta {gw}
                  </button>
                );
              })}
            </div>

          </div>
        )}

        {loadingProfile ? (
          <div className="py-16 text-center">
            <div className="w-7 h-7 border-3 border-[#38003c] border-t-transparent rounded-full animate-spin mx-auto mb-2" />
            <p className="text-xs font-bold text-slate-600">Oyuncu maç kayıtları yükleniyor...</p>
          </div>
        ) : !playerProfile?.matches?.length ? (
          <div className="py-12 text-center text-xs text-slate-500 font-medium">
            Seçilen sezonda oyuncunun maç kaydı bulunamadı.
          </div>
        ) : filteredMatches.length === 0 ? (
          <div className="py-12 text-center text-xs text-slate-500 font-medium bg-slate-50 border border-slate-200 rounded-xl">
            Bu haftada ({selectedMatchGameweek}. Hafta) oyuncunun süre aldığı karşılaşma kaydı bulunmuyor.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
            {filteredMatches.map(m => {
              const opp = getTeam(m.opponent_id, m.opponent_name);
              const goalsCount = m.goals || 0;
              const assistsCount = m.assists || 0;
              const hasContribution = goalsCount > 0 || assistsCount > 0;

              // Synthetic match object for MatchDetailModal (marked as COMPLETED for played match stats)
              const modalMatchObj = {
                match_id: m.match_id,
                status: (m.team_score !== null && m.team_score !== undefined) ? 'COMPLETED' : 'UNPLAYED',
                gameweek: m.gameweek,
                kickoff_label: m.kickoff,
                home_id: m.is_home ? m.team_id : m.opponent_id,
                home_name: m.is_home ? m.team_name : m.opponent_name,
                home_score: m.is_home ? m.team_score : m.opp_score,
                away_id: m.is_home ? m.opponent_id : m.team_id,
                away_name: m.is_home ? m.opponent_name : m.team_name,
                away_score: m.is_home ? m.opp_score : m.team_score,
                ground_name: 'Premier League',
              };

              return (
                <div
                  key={m.match_id}
                  onClick={() => setActiveModalMatch(modalMatchObj)}
                  className="p-3.5 rounded-xl border border-slate-200 hover:border-slate-400 hover:shadow-md transition-all cursor-pointer group bg-slate-50/50 hover:bg-white flex flex-col justify-between gap-3"
                >
                  
                  {/* Top info bar */}
                  <div className="flex items-center justify-between text-[11px] text-slate-500 pb-2 border-b border-slate-200/60">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-slate-700">Hafta {m.gameweek}</span>
                      <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-200 text-slate-700 font-medium">
                        {m.is_home ? 'İç Saha' : 'Deplasman'}
                      </span>
                    </div>
                    <span className="text-[11px] font-bold text-[#38003c] group-hover:translate-x-0.5 transition-transform flex items-center gap-0.5">
                      Detay & İstatistikler <ChevronRight className="w-3.5 h-3.5" />
                    </span>
                  </div>

                  {/* Match Preview & Score */}
                  <div className="flex items-center justify-between py-1">
                    {/* Club */}
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      {teamMeta && (
                        <img 
                          src={teamMeta.badge} 
                          alt={teamMeta.name} 
                          className="w-6 h-6 object-contain shrink-0" 
                          onError={(e) => { e.target.src = '/badges/1.svg'; }}
                        />
                      )}
                      <span className="font-bold text-xs text-slate-900 truncate">
                        {m.team_name}
                      </span>
                    </div>

                    {/* Score */}
                    <div className="px-3 py-1 rounded-lg bg-white border border-slate-300 font-mono font-black text-sm text-slate-900 shrink-0 mx-2">
                      {m.team_score} - {m.opp_score}
                    </div>

                    {/* Opponent */}
                    <div className="flex items-center gap-2 flex-1 min-w-0 justify-end text-right">
                      <span className="font-bold text-xs text-slate-800 truncate">
                        {opp.short || opp.name}
                      </span>
                      <img 
                        src={opp.badge} 
                        alt={opp.name} 
                        className="w-6 h-6 object-contain shrink-0"
                        onError={(e) => { e.target.src = '/badges/1.svg'; }}
                      />
                    </div>
                  </div>

                  {/* Specific User Requirement: minutes played and goal/assist status */}
                  <div className="flex items-center justify-between pt-2 border-t border-slate-200/60 text-xs">
                    
                    {/* Minutes played pill */}
                    <div className="flex items-center gap-1.5 bg-sky-50 border border-sky-200 px-2.5 py-1 rounded-lg text-sky-900 font-semibold text-[11px]">
                      <Clock className="w-3.5 h-3.5 text-sky-600" />
                      <span>
                        <strong>{m.minutes_played || 0} Dk</strong> {m.started ? '(İlk 11)' : '(Sonradan Girdi)'}
                      </span>
                    </div>

                    {/* Goal or Assist status badges */}
                    <div className="flex items-center gap-1.5 font-bold text-[11px]">
                      {goalsCount > 0 && (
                        <span className="px-2 py-0.5 rounded-lg bg-emerald-100 text-emerald-800 border border-emerald-300 flex items-center gap-1 font-bold">
                          <Target className="w-3 h-3 text-emerald-700" /> {goalsCount} Gol
                        </span>
                      )}
                      {assistsCount > 0 && (
                        <span className="px-2 py-0.5 rounded-lg bg-purple-100 text-purple-800 border border-purple-300 flex items-center gap-1 font-bold">
                          <Award className="w-3 h-3 text-purple-700" /> {assistsCount} Asist
                        </span>
                      )}
                      {!hasContribution && (
                        <span className="px-2 py-0.5 rounded-lg bg-slate-100 text-slate-500 border border-slate-200 font-medium text-[10px]">
                          Gol/Asist Yok
                        </span>
                      )}
                    </div>

                  </div>

                </div>
              );
            })}
          </div>
        )}
      </div>

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
