import { handleTeamBadgeError } from '../../utils/imageFallbacks';
import { useState } from 'react';
import { Calendar, ChevronRight } from 'lucide-react';
import { getTeam } from '../../data/teams';
import MatchDetailModal from '../MatchDetailModal';
import { getCachedTeamData } from '../../utils/teamProfileCache';
import { parseKickoff } from '../../utils/dateFormatters';

export default function TeamFixturesSection({
  activeTeamTab,
  profile,
  currentMeta,
  loading,
  selectedTeamId,
  onSelectMatch
}) {
  const [activeModalMatch, setActiveModalMatch] = useState(null);
  return (
    <>
      {/* TAB: FİKSTÜR & SONUÇLAR (DEFAULT) */}
      {activeTeamTab === 'fixtures' && (
        <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
          <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-100 bg-slate-50/60">
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4 text-[#38003c]" />
              <h3 className="text-xs sm:text-sm font-black text-slate-900">
                {currentMeta.name} — Sezon Lig Maçları ve Skor Önizlemeleri
              </h3>
            </div>
            <span className="text-xs font-mono font-bold text-slate-600 bg-white px-2.5 py-0.5 rounded-full border border-slate-200 shadow-2xs">
              {profile?.matches?.length || 0} Maç
            </span>
          </div>

          {loading ? (
            <div className="py-16 text-center">
              <div className="w-7 h-7 border-3 border-[#38003c] border-t-transparent rounded-full animate-spin mx-auto mb-2" />
              <p className="text-xs font-bold text-slate-600">Takım maçları yükleniyor...</p>
            </div>
          ) : !profile?.matches?.length ? (
            <div className="py-12 text-center text-xs text-slate-500 font-medium">
              Bu sezon için kayıtlı maç bulunamadı.
            </div>
          ) : (
            <div className="max-h-[580px] overflow-y-auto divide-y divide-slate-100 scrollbar-thin">
              {profile.matches.map(m => {
                const opp = getTeam(m.opponent_id, m.opponent_name);
                const isPlayed = (m.team_score !== null && m.team_score !== undefined);
                const isWin = m.result === 'W';
                const isDraw = m.result === 'D';

                const resBadgeClass = isWin 
                  ? 'bg-emerald-100 text-emerald-800 border-emerald-300' 
                  : isDraw 
                  ? 'bg-slate-100 text-slate-700 border-slate-300' 
                  : 'bg-rose-100 text-rose-800 border-rose-300';

                const resLabel = isWin ? 'G' : isDraw ? 'B' : 'M';
                const kickoff = parseKickoff(m.kickoff_label);

                const homeTeam = m.is_home ? currentMeta : opp;
                const awayTeam = m.is_home ? opp : currentMeta;
                const homeScore = m.is_home ? m.team_score : m.opp_score;
                const awayScore = m.is_home ? m.opp_score : m.team_score;
                const matchDetails = getCachedTeamData('match_detail', m.match_id, 'all')?.data;
                const redCardsForSide = (side, team) => {
                  const redCardStat = (matchDetails?.team_stats || [])
                    .flatMap(category => category.items || [])
                    .find(item => item.label === 'Kırmızı Kart');
                  const statCount = Number(side === 'home' ? redCardStat?.home : redCardStat?.away);
                  if (Number.isFinite(statCount) && statCount > 0) return statCount;
                  return (matchDetails?.timeline || []).filter(event =>
                    event.type === 'red_card' && (
                      Number(event.team_id) === Number(team.id) ||
                      (event.team_name && event.team_name.toLowerCase() === team.name.toLowerCase())
                    )
                  ).length;
                };
                const homeRedCards = redCardsForSide('home', homeTeam);
                const awayRedCards = redCardsForSide('away', awayTeam);

                // Synthetic match object for MatchDetailModal
                const modalMatchObj = {
                  match_id: m.match_id,
                  status: isPlayed ? 'COMPLETED' : (m.status || 'UNPLAYED'),
                  gameweek: m.gameweek,
                  kickoff_label: m.kickoff_label,
                  home_id: homeTeam.id,
                  home_name: homeTeam.name,
                  home_score: homeScore,
                  away_id: awayTeam.id,
                  away_name: awayTeam.name,
                  away_score: awayScore,
                  ground_name: m.is_home ? currentMeta.stadium : opp.stadium,
                };

                return (
                  <div
                    key={m.match_id}
                    onClick={() => {
                      if (onSelectMatch) {
                        onSelectMatch(modalMatchObj);
                      } else {
                        setActiveModalMatch(modalMatchObj);
                      }
                    }}
                    className="px-4 py-2.5 sm:px-6 sm:py-3 hover:bg-slate-50/90 transition-colors cursor-pointer group flex items-center justify-between gap-3 sm:gap-6 text-xs"
                  >
                    {/* 1. Hafta Sayısı */}
                    <div className="w-10 sm:w-12 text-left shrink-0">
                      <span className="font-mono font-bold text-slate-700 bg-slate-100 group-hover:bg-purple-100 group-hover:text-purple-900 group-hover:border-purple-200 px-2 py-0.5 rounded text-[11px] border border-slate-200 transition-colors">
                        H{Math.round(Number(m.gameweek) || 1)}
                      </span>
                    </div>

                    {/* 2. Tarih & Saat */}
                    <div className="min-w-[85px] sm:min-w-[115px] shrink-0 text-left">
                      <span className="font-semibold text-slate-800 text-[11px] sm:text-xs block whitespace-nowrap">
                        {kickoff.date}
                      </span>
                      {kickoff.time && (
                        <span className="font-mono text-slate-400 text-[10px] block whitespace-nowrap">
                          {kickoff.time}
                        </span>
                      )}
                    </div>

                    {/* 3. Karşılaşma ve Skor (Ortada Dengeli) */}
                    <div className="flex items-center justify-center gap-2 sm:gap-4 flex-1 min-w-0">
                      {/* Ev Sahibi */}
                      <div className="flex items-center gap-2 justify-end flex-1 min-w-0 text-right">
                        <span className={`truncate text-xs sm:text-sm ${homeTeam.id === selectedTeamId ? 'font-black text-slate-900' : 'font-medium text-slate-600'}`}>
                          {homeTeam.short || homeTeam.name}
                        </span>
                        {homeRedCards > 0 && (
                          <span className="inline-flex shrink-0 items-center gap-1" title={`${homeRedCards} kırmızı kart`} aria-label={`${homeRedCards} kırmızı kart`}>
                            <span className="inline-block h-3.5 w-2.5 rounded-[2px] border border-rose-700 bg-rose-600 shadow-sm" />
                            {homeRedCards > 1 && <span className="text-[10px] font-black text-rose-700">x{homeRedCards}</span>}
                          </span>
                        )}
                        <img 
                          src={homeTeam.badge} 
                          alt={homeTeam.name} 
                          className="w-5 h-5 sm:w-6 sm:h-6 object-contain shrink-0"
                          onError={handleTeamBadgeError}
                        />
                      </div>

                      {/* Skor / Durum */}
                      <div className="shrink-0 flex items-center justify-center min-w-[55px] sm:min-w-[65px]">
                        {isPlayed ? (
                          <span className="px-2.5 py-1 rounded-lg bg-slate-900 text-white font-mono font-black text-xs sm:text-sm tracking-wider shadow-2xs">
                            {homeScore} - {awayScore}
                          </span>
                        ) : (
                          <span className="px-2.5 py-1 rounded-lg bg-slate-100 text-slate-600 font-mono text-xs font-bold border border-slate-200">
                            {kickoff.time || 'vs'}
                          </span>
                        )}
                      </div>

                      {/* Deplasman */}
                      <div className="flex items-center gap-2 justify-start flex-1 min-w-0 text-left">
                        <img 
                          src={awayTeam.badge} 
                          alt={awayTeam.name} 
                          className="w-5 h-5 sm:w-6 sm:h-6 object-contain shrink-0"
                          onError={handleTeamBadgeError}
                        />
                        <span className={`truncate text-xs sm:text-sm ${awayTeam.id === selectedTeamId ? 'font-black text-slate-900' : 'font-medium text-slate-600'}`}>
                          {awayTeam.short || awayTeam.name}
                        </span>
                        {awayRedCards > 0 && (
                          <span className="inline-flex shrink-0 items-center gap-1" title={`${awayRedCards} kırmızı kart`} aria-label={`${awayRedCards} kırmızı kart`}>
                            <span className="inline-block h-3.5 w-2.5 rounded-[2px] border border-rose-700 bg-rose-600 shadow-sm" />
                            {awayRedCards > 1 && <span className="text-[10px] font-black text-rose-700">x{awayRedCards}</span>}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* 4. Sonuç Rozeti (G/B/M) & Ok */}
                    <div className="flex items-center gap-2 shrink-0 min-w-[45px] justify-end">
                      {isPlayed && (
                        <span className={`w-6 h-6 flex items-center justify-center text-[10px] font-mono font-black rounded-lg border shadow-2xs ${resBadgeClass}`}>
                          {resLabel}
                        </span>
                      )}
                      <ChevronRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-[#38003c] group-hover:translate-x-0.5 transition-all" />
                    </div>

                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {activeModalMatch && (
        <MatchDetailModal match={activeModalMatch} onClose={() => setActiveModalMatch(null)} />
      )}
    </>
  );
}
