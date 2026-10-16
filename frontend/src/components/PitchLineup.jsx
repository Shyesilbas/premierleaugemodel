import React, { useMemo } from 'react';
import PlayerAvatar from './PlayerAvatar';
import { ExternalLink, Shield } from 'lucide-react';

/**
 * FotMob / SofaScore Style Interactive Tactical Pitch Lineups
 */
export default function PitchLineup({
  homeLineup,
  awayLineup,
  homeTeam,
  awayTeam,
  playerStats = { home: [], away: [] },
  onPlayerClick,
}) {
  // Helper to get match stats (goals, cards) for a player
  const getPlayerMatchStats = (pid, side) => {
    const list = playerStats[side] || [];
    return list.find(p => p.id === pid) || {};
  };

  // Helper to resolve player rows from formation_matrix or fallback formation parser
  const getTeamRows = (lineup, side) => {
    if (!lineup || !lineup.starters || lineup.starters.length === 0) return [];

    const startersMap = new Map();
    lineup.starters.forEach(p => startersMap.set(p.id, p));

    // 1. Try exact formation_matrix if provided by backend
    if (lineup.formation_matrix && Array.isArray(lineup.formation_matrix) && lineup.formation_matrix.length > 0) {
      const rows = [];
      lineup.formation_matrix.forEach(rowIds => {
        const rowPlayers = [];
        rowIds.forEach(id => {
          const p = startersMap.get(id);
          if (p) rowPlayers.push(p);
        });
        if (rowPlayers.length > 0) rows.push(rowPlayers);
      });

      // If all or most starters were mapped
      const totalMapped = rows.reduce((acc, r) => acc + r.length, 0);
      if (totalMapped >= 10) {
        return rows;
      }
    }

    // 2. Fallback: Parse formation label (e.g. "4-2-3-1" or "4-3-3" or "3-5-2")
    const formStr = String(lineup.formation || '4-3-3').trim();
    const parts = formStr.split('-').map(n => parseInt(n, 10)).filter(n => !isNaN(n));
    const counts = [1, ...parts]; // prepend 1 for Goalkeeper

    // Sort starters: GK -> DEF -> MID -> FWD
    const positionOrder = { 'G': 0, 'GK': 0, 'D': 1, 'DEF': 1, 'M': 2, 'MID': 2, 'F': 3, 'FWD': 3 };
    const sorted = [...lineup.starters].sort((a, b) => {
      const orderA = positionOrder[a.position] !== undefined ? positionOrder[a.position] : 2;
      const orderB = positionOrder[b.position] !== undefined ? positionOrder[b.position] : 2;
      if (orderA !== orderB) return orderA - orderB;
      return (a.shirt || 99) - (b.shirt || 99);
    });

    const rows = [];
    let curIdx = 0;
    for (const count of counts) {
      if (curIdx >= sorted.length) break;
      rows.push(sorted.slice(curIdx, curIdx + count));
      curIdx += count;
    }
    // Any remaining players added to last row
    if (curIdx < sorted.length) {
      if (rows.length > 0) {
        rows[rows.length - 1] = rows[rows.length - 1].concat(sorted.slice(curIdx));
      } else {
        rows.push(sorted.slice(curIdx));
      }
    }
    return rows;
  };

  const awayRows = useMemo(() => getTeamRows(awayLineup, 'away'), [awayLineup]);
  const homeRows = useMemo(() => getTeamRows(homeLineup, 'home'), [homeLineup]);

  // Position badge class
  const getPosBadgeColor = (pos) => {
    const p = String(pos || '').toUpperCase();
    if (['G', 'GK'].includes(p)) return 'bg-amber-500 text-slate-950';
    if (['D', 'DEF'].includes(p)) return 'bg-sky-500 text-white';
    if (['M', 'MID'].includes(p)) return 'bg-emerald-500 text-white';
    if (['F', 'FWD'].includes(p)) return 'bg-rose-500 text-white';
    return 'bg-slate-500 text-white';
  };

  const renderPlayerNode = (player, side) => {
    const stats = getPlayerMatchStats(player.id, side);
    const goals = stats.goals || 0;
    const assists = stats.assists || 0;
    const yellowCards = stats.yellow_cards || 0;
    const redCards = stats.red_cards || 0;

    // Short display name: usually last name or single display name
    const nameParts = (player.name || '').trim().split(/\s+/);
    const shortName = nameParts.length > 1 ? nameParts[nameParts.length - 1] : player.name;

    return (
      <div
        key={player.id || player.shirt}
        onClick={() => onPlayerClick && onPlayerClick(player, side)}
        title={`${player.name} (#${player.shirt}) · Detaylar için tıklayın`}
        className="group flex flex-col items-center cursor-pointer transition-all duration-200 hover:scale-110 active:scale-95 select-none relative z-10"
      >
        {/* Avatar with Badges */}
        <div className="relative">
          <PlayerAvatar
            photoUrl={player.photo_url}
            name={player.name}
            shirt={player.shirt}
            fallback="initials"
            size="w-9 h-9 sm:w-11 sm:h-11"
            className="rounded-full border-2 border-white/90 shadow-md group-hover:border-[#00ff87] group-hover:shadow-[0_0_12px_rgba(0,255,135,0.6)] transition-all bg-slate-900"
          />

          {/* Captain Armband Badge */}
          {player.captain && (
            <span className="absolute -bottom-1 -left-1 w-4 h-4 rounded-full bg-amber-400 text-slate-950 font-black text-[9px] flex items-center justify-center border border-white shadow-xs">
              C
            </span>
          )}

          {/* Card Badge */}
          {redCards > 0 ? (
            <span className="absolute -top-1 -left-1 w-3.5 h-4.5 rounded-xs bg-rose-600 border border-white shadow-xs" title="Kırmızı Kart" />
          ) : yellowCards > 0 ? (
            <span className="absolute -top-1 -left-1 w-3 h-4 rounded-xs bg-amber-400 border border-white shadow-xs" title="Sarı Kart" />
          ) : null}

          {/* Goal & Assist Badges */}
          {(goals > 0 || assists > 0) && (
            <div className="absolute -top-1.5 -right-1.5 flex items-center gap-0.5 z-20">
              {goals > 0 && (
                <span className="bg-emerald-500 text-white text-[9px] font-black rounded-full px-1 py-0.2 border border-white shadow-xs flex items-center leading-tight" title={`${goals} Gol`}>
                  ⚽{goals > 1 ? goals : ''}
                </span>
              )}
              {assists > 0 && (
                <span className="bg-purple-600 text-white text-[9px] font-black rounded-full px-1 py-0.2 border border-white shadow-xs flex items-center leading-tight" title={`${assists} Asist`}>
                  🎯{assists > 1 ? assists : ''}
                </span>
              )}
            </div>
          )}

          {/* Shirt Number Badge (subtle) */}
          <span className={`absolute -bottom-1 -right-1 px-1 rounded text-[9px] font-mono font-black border border-white/80 shadow-2xs ${getPosBadgeColor(player.position)}`}>
            {player.shirt || '-'}
          </span>
        </div>

        {/* Player Name Pill */}
        <div className="mt-1 px-2 py-0.5 rounded-full bg-slate-950/85 backdrop-blur-xs border border-white/20 text-white font-bold text-[10px] sm:text-[11px] shadow-sm truncate max-w-[75px] sm:max-w-[95px] text-center group-hover:bg-slate-900 group-hover:border-[#00ff87]/80 group-hover:text-[#00ff87] transition-all">
          {shortName}
        </div>

        {/* Dynamic Player Rating & Cards Risk Pill */}
        {(stats.rating != null || player.rating != null) && (
          <div className="mt-0.5 flex items-center justify-center gap-1">
            {(() => {
              const displayRating = stats.rating != null ? stats.rating : player.rating;
              const isMatch = stats.rating != null || player.is_match_rating;
              return (
                <span
                  className={`px-1.5 py-0.2 rounded-full font-mono font-bold text-[9px] shadow-xs border ${
                    displayRating >= 7.5
                      ? 'bg-emerald-500 text-slate-950 border-emerald-300'
                      : displayRating >= 6.5
                      ? 'bg-sky-500 text-white border-sky-300'
                      : displayRating >= 5.5
                      ? 'bg-slate-700 text-slate-200 border-slate-600'
                      : 'bg-rose-500 text-white border-rose-300'
                  }`}
                  title={
                    isMatch
                      ? `Maç Performans Notu: ${Number(displayRating).toFixed(1)}/10`
                      : `5 Maçlık Form Puanı: ${Number(displayRating).toFixed(1)}/10 · Durum: ${player.form_label || 'Normal'} · Kart Riski: ${player.cards_risk || 3.0}/10`
                  }
                >
                  {Number(displayRating).toFixed(1)}
                </span>
              );
            })()}
            {player.cards_risk >= 7.0 && (
              <span
                className="w-2.5 h-3.5 bg-amber-400 rounded-2xs border border-amber-600 shadow-2xs shrink-0"
                title={`Yüksek Kart Riski: ${player.cards_risk}/10`}
              />
            )}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      
      {/* ================= TACTICAL PITCH CONTAINER ================= */}
      <div className="relative w-full max-w-3xl mx-auto rounded-3xl overflow-hidden shadow-2xl border-4 border-slate-900/10 bg-[#165b33] select-none">
        
        {/* Grass Turf Stripes Effect */}
        <div className="absolute inset-0 pointer-events-none flex flex-col">
          {[...Array(12)].map((_, i) => (
            <div
              key={i}
              className={`flex-1 ${i % 2 === 0 ? 'bg-emerald-800/40' : 'bg-emerald-700/25'}`}
            />
          ))}
        </div>

        {/* Subtle Pitch Vignette */}
        <div className="absolute inset-0 pointer-events-none bg-radial from-transparent via-black/10 to-black/35" />

        {/* ================= PITCH MARKINGS ================= */}
        <div className="absolute inset-3 sm:inset-4 border-2 border-white/40 rounded-2xl pointer-events-none">
          
          {/* Halfway Line */}
          <div className="absolute top-1/2 left-0 right-0 h-0.5 bg-white/40 -translate-y-1/2" />
          
          {/* Center Circle */}
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-28 h-28 sm:w-36 sm:h-36 rounded-full border-2 border-white/40 flex items-center justify-center">
            <div className="w-2.5 h-2.5 rounded-full bg-white/70" />
          </div>

          {/* TOP GOAL AREA (Away Goal) */}
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-44 sm:w-64 h-24 sm:h-32 border-x-2 border-b-2 border-white/40">
            {/* 6-Yard Box */}
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-24 sm:w-32 h-10 sm:h-14 border-x-2 border-b-2 border-white/40" />
            {/* Penalty Spot */}
            <div className="absolute top-16 sm:top-22 left-1/2 -translate-x-1/2 w-2 h-2 rounded-full bg-white/70" />
          </div>
          {/* Top Penalty Arc */}
          <div className="absolute top-24 sm:top-32 left-1/2 -translate-x-1/2 w-24 h-12 border-b-2 border-white/40 rounded-b-full" />

          {/* BOTTOM GOAL AREA (Home Goal) */}
          <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-44 sm:w-64 h-24 sm:h-32 border-x-2 border-t-2 border-white/40">
            {/* 6-Yard Box */}
            <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-24 sm:w-32 h-10 sm:h-14 border-x-2 border-t-2 border-white/40" />
            {/* Penalty Spot */}
            <div className="absolute bottom-16 sm:bottom-22 left-1/2 -translate-x-1/2 w-2 h-2 rounded-full bg-white/70" />
          </div>
          {/* Bottom Penalty Arc */}
          <div className="absolute bottom-24 sm:bottom-32 left-1/2 -translate-x-1/2 w-24 h-12 border-t-2 border-white/40 rounded-t-full" />

          {/* Corner Arcs */}
          <div className="absolute top-0 left-0 w-4 h-4 border-r-2 border-b-2 border-white/40 rounded-br-full" />
          <div className="absolute top-0 right-0 w-4 h-4 border-l-2 border-b-2 border-white/40 rounded-bl-full" />
          <div className="absolute bottom-0 left-0 w-4 h-4 border-r-2 border-t-2 border-white/40 rounded-tr-full" />
          <div className="absolute bottom-0 right-0 w-4 h-4 border-l-2 border-t-2 border-white/40 rounded-tl-full" />
        </div>

        {/* ================= PITCH CONTENT ================= */}
        <div className="relative py-4 px-3 sm:px-6 flex flex-col justify-between min-h-[640px] sm:min-h-[780px]">
          
          {/* TOP TEAM BANNER (Away Team Header) */}
          <div className="relative z-10 flex items-center justify-between bg-slate-950/70 backdrop-blur-md rounded-2xl px-4 py-2 border border-white/10 text-white mb-2 shadow-lg">
            <div className="flex items-center gap-2.5">
              <img src={awayTeam?.badge} alt="" className="w-6 h-6 object-contain" />
              <div>
                <span className="text-xs font-black tracking-wide block leading-tight">{awayTeam?.name}</span>
                <span className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider">Deplasman</span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {awayLineup?.team_ratings?.overall != null && (
                <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-lg bg-white/10 border border-white/15 text-[11px] font-bold" title={awayLineup.starters?.[0]?.is_match_rating ? '11 Oyuncu Maç Performansı Ortalaması' : '11 Ortalama Form Puanı'}>
                  <span className="text-slate-300 font-medium">
                    {awayLineup.starters?.[0]?.is_match_rating ? 'Maç Notu:' : '11 Form:'}
                  </span>
                  <span className="text-[#00ff87] font-mono font-black">{Number(awayLineup.team_ratings.overall).toFixed(1)}</span>
                </div>
              )}
              {awayLineup?.formation && (
                <span className="text-xs font-mono font-black px-2.5 py-0.5 rounded-lg bg-white/10 text-[#00ff87] border border-[#00ff87]/30">
                  {awayLineup.formation}
                </span>
              )}
            </div>
          </div>

          {/* AWAY TEAM HALF (Top Half: GK at top, down to Attackers) */}
          <div className="flex-1 flex flex-col justify-around py-3">
            {awayRows.map((row, rowIdx) => (
              <div key={`away-row-${rowIdx}`} className="flex items-center justify-around w-full px-2 sm:px-6">
                {row.map(player => renderPlayerNode(player, 'away'))}
              </div>
            ))}
          </div>

          {/* CENTER LINE TACTICAL DIVIDER */}
          <div className="relative z-10 my-1 py-1 flex items-center justify-center">
            <span className="px-3 py-0.5 rounded-full bg-black/60 border border-white/15 text-[10px] font-mono font-bold text-white/70 uppercase tracking-widest shadow-xs">
              Saha Merkezi
            </span>
          </div>

          {/* HOME TEAM HALF (Bottom Half: Attackers near center, down to GK at bottom) */}
          <div className="flex-1 flex flex-col justify-around py-3">
            {/* Reverse home rows so row 0 (GK) is at the very bottom! */}
            {[...homeRows].reverse().map((row, rowIdx) => (
              <div key={`home-row-${rowIdx}`} className="flex items-center justify-around w-full px-2 sm:px-6">
                {row.map(player => renderPlayerNode(player, 'home'))}
              </div>
            ))}
          </div>

          {/* BOTTOM TEAM BANNER (Home Team Header) */}
          <div className="relative z-10 flex items-center justify-between bg-slate-950/70 backdrop-blur-md rounded-2xl px-4 py-2 border border-white/10 text-white mt-2 shadow-lg">
            <div className="flex items-center gap-2.5">
              <img src={homeTeam?.badge} alt="" className="w-6 h-6 object-contain" />
              <div>
                <span className="text-xs font-black tracking-wide block leading-tight">{homeTeam?.name}</span>
                <span className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider">Ev Sahibi</span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {homeLineup?.team_ratings?.overall != null && (
                <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-lg bg-white/10 border border-white/15 text-[11px] font-bold" title={homeLineup.starters?.[0]?.is_match_rating ? '11 Oyuncu Maç Performansı Ortalaması' : '11 Ortalama Form Puanı'}>
                  <span className="text-slate-300 font-medium">
                    {homeLineup.starters?.[0]?.is_match_rating ? 'Maç Notu:' : '11 Form:'}
                  </span>
                  <span className="text-[#00ff87] font-mono font-black">{Number(homeLineup.team_ratings.overall).toFixed(1)}</span>
                </div>
              )}
              {homeLineup?.formation && (
                <span className="text-xs font-mono font-black px-2.5 py-0.5 rounded-lg bg-white/10 text-[#00ff87] border border-[#00ff87]/30">
                  {homeLineup.formation}
                </span>
              )}
            </div>
          </div>

        </div>
      </div>

      {/* ================= SUBSTITUTES BENCH SECTION ================= */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
        
        {/* Home Substitutes */}
        <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <img src={homeTeam?.badge} alt="" className="w-5 h-5 object-contain" />
              <span className="text-xs font-black text-slate-900">
                {homeTeam?.name} Yedekleri ({homeLineup?.substitutes?.length || 0})
              </span>
            </div>
            <span className="text-[10px] text-slate-400 font-medium">Detay için tıklayın</span>
          </div>

          {(!homeLineup?.substitutes || homeLineup.substitutes.length === 0) ? (
            <p className="text-xs text-slate-400 text-center py-4">Kayıtlı yedek oyuncu yok.</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {homeLineup.substitutes.map((sub, idx) => {
                const stats = getPlayerMatchStats(sub.id, 'home');
                return (
                  <div
                    key={sub.id || idx}
                    onClick={() => onPlayerClick && onPlayerClick(sub, 'home')}
                    className="flex items-center justify-between p-2 rounded-xl bg-slate-50 border border-slate-200/80 hover:bg-white hover:border-[#38003c]/40 hover:shadow-xs transition-all cursor-pointer group text-xs"
                    title={`${sub.name} maç performansını görüntüle`}
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <PlayerAvatar
                        photoUrl={sub.photo_url}
                        name={sub.name}
                        shirt={sub.shirt}
                        fallback="initials"
                        size="w-7 h-7 text-[10px]"
                        className="shrink-0"
                      />
                      <span className="font-mono text-xs font-bold text-slate-500">#{sub.shirt || '-'}</span>
                      <span className="font-bold text-slate-800 truncate group-hover:text-[#38003c] transition-colors">{sub.name}</span>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      {sub.rating != null && (
                        <span
                          className={`text-[9px] font-bold px-1.5 py-0.2 rounded font-mono ${
                            sub.rating >= 7.5
                              ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                              : sub.rating >= 6.5
                              ? 'bg-sky-100 text-sky-800 border border-sky-300'
                              : 'bg-slate-100 text-slate-700 border border-slate-300'
                          }`}
                          title={`Form Puanı: ${sub.rating}/10`}
                        >
                          {Number(sub.rating).toFixed(1)}
                        </span>
                      )}
                      {stats.goals > 0 && <span className="text-[10px]">⚽{stats.goals > 1 ? stats.goals : ''}</span>}
                      {stats.yellow_cards > 0 && <span className="w-2.5 h-3.5 bg-amber-400 rounded-2xs inline-block" />}
                      {stats.red_cards > 0 && <span className="w-2.5 h-3.5 bg-rose-600 rounded-2xs inline-block" />}
                      <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded border ${getPosBadgeColor(sub.position)}`}>
                        {sub.position || 'M'}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Away Substitutes */}
        <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <img src={awayTeam?.badge} alt="" className="w-5 h-5 object-contain" />
              <span className="text-xs font-black text-slate-900">
                {awayTeam?.name} Yedekleri ({awayLineup?.substitutes?.length || 0})
              </span>
            </div>
            <span className="text-[10px] text-slate-400 font-medium">Detay için tıklayın</span>
          </div>

          {(!awayLineup?.substitutes || awayLineup.substitutes.length === 0) ? (
            <p className="text-xs text-slate-400 text-center py-4">Kayıtlı yedek oyuncu yok.</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {awayLineup.substitutes.map((sub, idx) => {
                const stats = getPlayerMatchStats(sub.id, 'away');
                return (
                  <div
                    key={sub.id || idx}
                    onClick={() => onPlayerClick && onPlayerClick(sub, 'away')}
                    className="flex items-center justify-between p-2 rounded-xl bg-slate-50 border border-slate-200/80 hover:bg-white hover:border-[#38003c]/40 hover:shadow-xs transition-all cursor-pointer group text-xs"
                    title={`${sub.name} maç performansını görüntüle`}
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <PlayerAvatar
                        photoUrl={sub.photo_url}
                        name={sub.name}
                        shirt={sub.shirt}
                        fallback="initials"
                        size="w-7 h-7 text-[10px]"
                        className="shrink-0"
                      />
                      <span className="font-mono text-xs font-bold text-slate-500">#{sub.shirt || '-'}</span>
                      <span className="font-bold text-slate-800 truncate group-hover:text-[#38003c] transition-colors">{sub.name}</span>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      {sub.rating != null && (
                        <span
                          className={`text-[9px] font-bold px-1.5 py-0.2 rounded font-mono ${
                            sub.rating >= 7.5
                              ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                              : sub.rating >= 6.5
                              ? 'bg-sky-100 text-sky-800 border border-sky-300'
                              : 'bg-slate-100 text-slate-700 border border-slate-300'
                          }`}
                          title={`Form Puanı: ${sub.rating}/10`}
                        >
                          {Number(sub.rating).toFixed(1)}
                        </span>
                      )}
                      {stats.goals > 0 && <span className="text-[10px]">⚽{stats.goals > 1 ? stats.goals : ''}</span>}
                      {stats.yellow_cards > 0 && <span className="w-2.5 h-3.5 bg-amber-400 rounded-2xs inline-block" />}
                      {stats.red_cards > 0 && <span className="w-2.5 h-3.5 bg-rose-600 rounded-2xs inline-block" />}
                      <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded border ${getPosBadgeColor(sub.position)}`}>
                        {sub.position || 'M'}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

      </div>

    </div>
  );
}
