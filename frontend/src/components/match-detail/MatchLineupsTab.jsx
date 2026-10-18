import { ExternalLink, Users } from 'lucide-react';
import PitchLineup from '../PitchLineup';
import PlayerAvatar from '../PlayerAvatar';
import { RedCardIcon, YellowCardIcon } from './eventIcons';

export default function MatchLineupsTab({
  homeLineup,
  awayLineup,
  homeTeam,
  awayTeam,
  playerStats,
  lineupViewMode,
  setLineupViewMode,
  isCompleted,
  prediction,
  handlePlayerClick,
  groupPlayersByPosition,
  formatPosition,
  getPositionBadgeClass
}) {
  return (

          <div className="space-y-6">
            {!homeLineup && !awayLineup ? (
              <div className="py-16 text-center text-sm text-slate-500 font-medium">
                Bu maç için henüz resmi kadro veya ilk 11 verisi açıklanmamış.
              </div>
            ) : (
              <>
                {/* View Switcher Header: Taktik Saha vs Detaylı Liste */}
                <div className="flex items-center justify-between flex-wrap gap-3 pb-3 border-b border-slate-200">
                  <div className="flex items-center gap-2">
                    <Users className="w-5 h-5 text-[#38003c]" />
                    <h3 className="text-sm font-black text-slate-900">
                      İlk 11 & Kadrolar
                    </h3>
                    <span className="text-xs text-slate-500 font-medium hidden sm:inline">
                      · Taktik diziliş ve yedek kulübesi
                    </span>
                  </div>

                  {/* Segmented Control */}
                  <div className="flex items-center bg-slate-100 p-1 rounded-xl border border-slate-200 gap-1">
                    <button
                      type="button"
                      onClick={() => setLineupViewMode('pitch')}
                      className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                        lineupViewMode === 'pitch'
                          ? 'bg-[#38003c] text-white shadow-xs'
                          : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
                      }`}
                    >
                      Taktik Saha
                    </button>
                    <button
                      type="button"
                      onClick={() => setLineupViewMode('list')}
                      className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                        lineupViewMode === 'list'
                          ? 'bg-[#38003c] text-white shadow-xs'
                          : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
                      }`}
                    >
                      Detaylı Liste
                    </button>
                  </div>
                </div>

                {/* Starting XI Form & Model Impact Banner (Clean, Minimalist Design) */}
                {(homeLineup?.team_ratings || prediction?.lineup_analysis) && (
                  <div className="bg-slate-900 text-white rounded-2xl p-4 sm:p-5 border border-slate-800 shadow-sm space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-2 pb-2.5 border-b border-slate-800/80">
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-[#00ff87] animate-pulse" />
                        <h4 className="text-xs sm:text-sm font-black tracking-wide text-slate-100">
                          {isCompleted ? 'Maç Performansı & Oyuncu Reytingleri' : 'İlk 11 Kadro Formu & Dinamik Model Etkisi'}
                        </h4>
                      </div>
                      <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full border ${
                        (prediction?.lineup_analysis?.is_official || isCompleted)
                          ? 'bg-emerald-950 text-emerald-400 border-emerald-800/60'
                          : 'bg-slate-800 text-slate-300 border-slate-700'
                      }`}>
                        {prediction?.lineup_analysis?.status_label || (isCompleted ? 'Resmi Kadrolar Açıklandı' : "Muhtemel 11'ler Baz Alındı")}
                      </span>
                    </div>

                    {/* Team Ratings Comparison Grid */}
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 items-center text-center">
                      {/* Home Team 11 */}
                      <div className="bg-slate-800/60 rounded-xl p-2.5 border border-slate-700/50 flex flex-col items-center">
                        <span className="text-[11px] font-bold text-slate-400 truncate max-w-[140px]">{homeTeam?.name}</span>
                        <div className="flex items-baseline gap-1 mt-0.5">
                          <span className="text-xl font-black font-mono text-[#00ff87]">
                            {Number(homeLineup?.team_ratings?.overall || prediction?.lineup_analysis?.home_xi?.team_overall || 6.0).toFixed(1)}
                          </span>
                          <span className="text-[10px] text-slate-500 font-bold">/ 10</span>
                        </div>
                        <div className="flex items-center gap-2 mt-1 text-[10px] text-slate-400">
                          <span>Hücum: <strong className="text-slate-200">{Number(homeLineup?.team_ratings?.attack || prediction?.lineup_analysis?.home_xi?.team_attack || 6.0).toFixed(1)}</strong></span>
                          <span>·</span>
                          <span>Savunma: <strong className="text-slate-200">{Number(homeLineup?.team_ratings?.defense || prediction?.lineup_analysis?.home_xi?.team_defense || 6.0).toFixed(1)}</strong></span>
                        </div>
                      </div>

                      {/* Center Model Impact Delta */}
                      <div className="bg-slate-800/30 rounded-xl p-2 border border-slate-700/30 space-y-1">
                        <span className="text-[10px] uppercase tracking-wider text-slate-400 font-bold block">
                          Lineup Modülatörleri
                        </span>
                        {prediction?.lineup_analysis?.lineup_impact ? (
                          <div className="space-y-0.5 text-xs font-mono">
                            <div className="flex justify-between px-2 text-[11px]">
                              <span className="text-slate-400">Gol Etkisi:</span>
                              <span className="font-bold text-slate-200">
                                {prediction.lineup_analysis.lineup_impact.delta_home_goals > 0 ? `+${prediction.lineup_analysis.lineup_impact.delta_home_goals}` : prediction.lineup_analysis.lineup_impact.delta_home_goals} / {prediction.lineup_analysis.lineup_impact.delta_away_goals > 0 ? `+${prediction.lineup_analysis.lineup_impact.delta_away_goals}` : prediction.lineup_analysis.lineup_impact.delta_away_goals}
                              </span>
                            </div>
                            <div className="flex justify-between px-2 text-[11px]">
                              <span className="text-slate-400">Kart Beklentisi:</span>
                              <span className={`font-bold ${prediction.lineup_analysis.lineup_impact.delta_cards > 0 ? 'text-amber-400' : 'text-slate-200'}`}>
                                {prediction.lineup_analysis.lineup_impact.delta_cards > 0 ? `+${prediction.lineup_analysis.lineup_impact.delta_cards}` : prediction.lineup_analysis.lineup_impact.delta_cards} Kart
                              </span>
                            </div>
                          </div>
                        ) : (
                          <p className="text-[10px] text-slate-400">Model çarpanları 11 açıklandığında güncellenir.</p>
                        )}
                      </div>

                      {/* Away Team 11 */}
                      <div className="bg-slate-800/60 rounded-xl p-2.5 border border-slate-700/50 flex flex-col items-center">
                        <span className="text-[11px] font-bold text-slate-400 truncate max-w-[140px]">{awayTeam?.name}</span>
                        <div className="flex items-baseline gap-1 mt-0.5">
                          <span className="text-xl font-black font-mono text-[#00ff87]">
                            {Number(awayLineup?.team_ratings?.overall || prediction?.lineup_analysis?.away_xi?.team_overall || 6.0).toFixed(1)}
                          </span>
                          <span className="text-[10px] text-slate-500 font-bold">/ 10</span>
                        </div>
                        <div className="flex items-center gap-2 mt-1 text-[10px] text-slate-400">
                          <span>Hücum: <strong className="text-slate-200">{Number(awayLineup?.team_ratings?.attack || prediction?.lineup_analysis?.away_xi?.team_attack || 6.0).toFixed(1)}</strong></span>
                          <span>·</span>
                          <span>Savunma: <strong className="text-slate-200">{Number(awayLineup?.team_ratings?.defense || prediction?.lineup_analysis?.away_xi?.team_defense || 6.0).toFixed(1)}</strong></span>
                        </div>
                      </div>
                    </div>

                    {/* Summary text */}
                    {prediction?.lineup_analysis?.lineup_impact?.summary_text && (
                      <p className="text-[11px] text-slate-400 text-center pt-1 border-t border-slate-800/60">
                        {prediction.lineup_analysis.lineup_impact.summary_text}
                      </p>
                    )}
                  </div>
                )}

                {/* Conditional Rendering: Pitch View vs List View */}
                {lineupViewMode === 'pitch' ? (
                  <PitchLineup
                    homeLineup={homeLineup}
                    awayLineup={awayLineup}
                    homeTeam={homeTeam}
                    awayTeam={awayTeam}
                    playerStats={playerStats}
                    onPlayerClick={handlePlayerClick}
                  />
                ) : (
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                
                {/* Home Team Column */}
                <div className="space-y-6">
                  {/* Team Card Header */}
                  <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <img src={homeTeam.badge} alt="" className="w-8 h-8 object-contain shrink-0" />
                      <div>
                        <h4 className="font-black text-sm text-slate-900 leading-tight">{homeTeam.name}</h4>
                        <span className="text-[11px] font-bold text-slate-500">Ev Sahibi</span>
                      </div>
                    </div>
                    {homeLineup?.formation && (
                      <span className="text-xs font-mono font-black px-3 py-1 rounded-xl bg-purple-100 text-[#38003c] border border-purple-200">
                        {homeLineup.formation}
                      </span>
                    )}
                  </div>

                  {/* Starting XI Grouped By Position Lines */}
                  <div className="space-y-4">
                    <div className="flex items-center justify-between pb-1.5 border-b border-slate-200">
                      <span className="text-xs font-black uppercase tracking-wider text-slate-800">
                        Başlangıç 11'i ({homeLineup?.starters?.length || 0})
                      </span>
                      <span className="text-[10px] text-slate-500 font-medium">
                        İstatistik için oyuncuya tıklayın
                      </span>
                    </div>

                    {groupPlayersByPosition(homeLineup?.starters).map((group) => (
                      <div key={group.key} className="space-y-2">
                        <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-500 block px-1">
                          {group.label} ({group.list.length})
                        </span>
                        <div className="space-y-1.5">
                          {group.list.map((p, idx) => {
                            const pStat = (playerStats?.home || []).find(ps => String(ps.id) === String(p.id));
                            const effectiveRating = (isCompleted && pStat?.rating != null) ? pStat.rating : (pStat?.rating != null ? pStat.rating : p.rating);

                            return (
                              <div 
                                key={p.id || idx}
                                onClick={(e) => handlePlayerClick(p, 'home', e)}
                                className="flex items-center justify-between p-2.5 rounded-xl bg-white border border-slate-200/90 hover:border-[#38003c]/40 hover:bg-slate-50/80 transition-all cursor-pointer group shadow-2xs"
                                title={`${p.name} maç performansını görüntüle`}
                              >
                                <div className="flex items-center gap-3 min-w-0">
                                  <PlayerAvatar 
                                    photoUrl={p.photo_url}
                                    name={p.name}
                                    shirt={p.shirt || idx + 1}
                                    fallback="initials"
                                    size="w-8 h-8 text-xs"
                                    className="shrink-0 group-hover:scale-105 transition-transform"
                                  />
                                  <span className="w-6 h-6 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center font-mono font-bold text-xs text-slate-800 shrink-0">
                                    {p.shirt || idx + 1}
                                  </span>
                                  <div className="min-w-0">
                                    <div className="flex items-center gap-1.5 flex-wrap">
                                      <span className="font-bold text-slate-900 group-hover:text-[#38003c] transition-colors truncate text-xs sm:text-sm">
                                        {p.name}
                                      </span>
                                      {p.captain && (
                                        <span className="text-[9px] font-black px-1.5 py-0.2 rounded bg-amber-200 text-amber-900 shrink-0">
                                          KAPTAN
                                        </span>
                                      )}
                                      {pStat?.goals > 0 && (
                                        <span className="text-[9px] bg-emerald-100 text-emerald-800 font-bold px-1 rounded border border-emerald-300 shrink-0">
                                          ⚽ {pStat.goals}
                                        </span>
                                      )}
                                      {pStat?.assists > 0 && (
                                        <span className="text-[9px] bg-purple-100 text-purple-800 font-bold px-1 rounded border border-purple-300 shrink-0">
                                          🎯 {pStat.assists}
                                        </span>
                                      )}
                                      {pStat?.red_cards > 0 ? (
                                        <RedCardIcon />
                                      ) : pStat?.yellow_cards > 0 ? (
                                        <YellowCardIcon />
                                      ) : null}
                                    </div>
                                  </div>
                                </div>
                                <div className="flex items-center gap-2 shrink-0">
                                  {effectiveRating != null ? (
                                    <span
                                      className={`text-[10px] font-mono font-black px-1.5 py-0.5 rounded border ${
                                        effectiveRating >= 7.5
                                          ? 'bg-emerald-50 text-emerald-800 border-emerald-300'
                                          : effectiveRating >= 6.5
                                          ? 'bg-sky-50 text-sky-800 border-sky-300'
                                          : effectiveRating >= 5.5
                                          ? 'bg-slate-50 text-slate-700 border-slate-300'
                                          : 'bg-rose-50 text-rose-800 border-rose-300'
                                      }`}
                                      title={isCompleted ? `Maç Performans Reytingi: ${Number(effectiveRating).toFixed(1)}/10` : `Form Puanı: ${Number(effectiveRating).toFixed(1)}/10`}
                                    >
                                      {Number(effectiveRating).toFixed(1)}
                                    </span>
                                  ) : isCompleted ? (
                                    <span className="text-[10px] font-mono text-slate-400 px-1" title="Değerlendirilmedi">
                                      —
                                    </span>
                                  ) : null}
                                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md border ${getPositionBadgeClass(p.position)}`}>
                                    {formatPosition(p.position)}
                                  </span>
                                  <ExternalLink className="w-3.5 h-3.5 text-slate-300 group-hover:text-slate-600 transition-colors" />
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Substitutes Bench */}
                  {homeLineup?.substitutes?.length > 0 && (
                    <div className="pt-4 border-t border-slate-200 space-y-2.5">
                      <span className="text-xs font-black uppercase tracking-wider text-slate-800 block">
                        Yedek Kulübesi ({homeLineup.substitutes.length})
                      </span>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {homeLineup.substitutes.map((sub, idx) => {
                          const pStat = (playerStats?.home || []).find(ps => String(ps.id) === String(sub.id));
                          const effectiveRating = (isCompleted && pStat?.rating != null) ? pStat.rating : (pStat?.rating != null ? pStat.rating : sub.rating);

                          return (
                            <div 
                              key={sub.id || idx}
                              onClick={(e) => handlePlayerClick(sub, 'home', e)}
                              className="flex items-center justify-between p-2 rounded-xl bg-white border border-slate-200 hover:border-slate-300 hover:bg-slate-50 transition-all cursor-pointer group text-xs shadow-2xs"
                              title={`${sub.name} maç performansını görüntüle`}
                            >
                              <div className="flex items-center gap-2 min-w-0">
                                <PlayerAvatar 
                                  photoUrl={sub.photo_url}
                                  name={sub.name}
                                  shirt={sub.shirt}
                                  fallback="initials"
                                  size="w-6 h-6 text-[10px]"
                                  className="shrink-0"
                                />
                                <span className="font-mono text-xs font-bold text-slate-500">#{sub.shirt}</span>
                                <span className="font-medium text-slate-800 truncate">{sub.name}</span>
                                {pStat?.goals > 0 && <span className="text-[9px] bg-emerald-100 text-emerald-800 font-bold px-1 rounded border border-emerald-300">⚽ {pStat.goals}</span>}
                                {pStat?.assists > 0 && <span className="text-[9px] bg-purple-100 text-purple-800 font-bold px-1 rounded border border-purple-300">🎯 {pStat.assists}</span>}
                                {pStat?.red_cards > 0 ? <RedCardIcon /> : pStat?.yellow_cards > 0 ? <YellowCardIcon /> : null}
                              </div>
                              <div className="flex items-center gap-1.5 shrink-0">
                                {effectiveRating != null && (
                                  <span className={`text-[10px] font-mono font-black px-1.5 py-0.2 rounded border ${
                                    effectiveRating >= 7.5 ? 'bg-emerald-50 text-emerald-800 border-emerald-300' :
                                    effectiveRating >= 6.5 ? 'bg-sky-50 text-sky-800 border-sky-300' :
                                    effectiveRating >= 5.5 ? 'bg-slate-50 text-slate-700 border-slate-300' :
                                    'bg-rose-50 text-rose-800 border-rose-300'
                                  }`}>
                                    {Number(effectiveRating).toFixed(1)}
                                  </span>
                                )}
                                <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded border shrink-0 ${getPositionBadgeClass(sub.position)}`}>
                                  {formatPosition(sub.position)}
                                </span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>

                {/* Away Team Column */}
                <div className="space-y-6">
                  {/* Team Card Header */}
                  <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <img src={awayTeam.badge} alt="" className="w-8 h-8 object-contain shrink-0" />
                      <div>
                        <h4 className="font-black text-sm text-slate-900 leading-tight">{awayTeam.name}</h4>
                        <span className="text-[11px] font-bold text-slate-500">Deplasman</span>
                      </div>
                    </div>
                    {awayLineup?.formation && (
                      <span className="text-xs font-mono font-black px-3 py-1 rounded-xl bg-purple-100 text-[#38003c] border border-purple-200">
                        {awayLineup.formation}
                      </span>
                    )}
                  </div>

                  {/* Starting XI Grouped By Position Lines */}
                  <div className="space-y-4">
                    <div className="flex items-center justify-between pb-1.5 border-b border-slate-200">
                      <span className="text-xs font-black uppercase tracking-wider text-slate-800">
                        Başlangıç 11'i ({awayLineup?.starters?.length || 0})
                      </span>
                      <span className="text-[10px] text-slate-500 font-medium">
                        İstatistik için oyuncuya tıklayın
                      </span>
                    </div>

                    {groupPlayersByPosition(awayLineup?.starters).map((group) => (
                      <div key={group.key} className="space-y-2">
                        <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-500 block px-1">
                          {group.label} ({group.list.length})
                        </span>
                        <div className="space-y-1.5">
                          {group.list.map((p, idx) => {
                            const pStat = (playerStats?.away || []).find(ps => String(ps.id) === String(p.id));
                            const effectiveRating = (isCompleted && pStat?.rating != null) ? pStat.rating : (pStat?.rating != null ? pStat.rating : p.rating);

                            return (
                              <div 
                                key={p.id || idx}
                                onClick={(e) => handlePlayerClick(p, 'away', e)}
                                className="flex items-center justify-between p-2.5 rounded-xl bg-white border border-slate-200/90 hover:border-[#38003c]/40 hover:bg-slate-50/80 transition-all cursor-pointer group shadow-2xs"
                                title={`${p.name} maç performansını görüntüle`}
                              >
                                <div className="flex items-center gap-3 min-w-0">
                                  <PlayerAvatar 
                                    photoUrl={p.photo_url}
                                    name={p.name}
                                    shirt={p.shirt || idx + 1}
                                    fallback="initials"
                                    size="w-8 h-8 text-xs"
                                    className="shrink-0 group-hover:scale-105 transition-transform"
                                  />
                                  <span className="w-6 h-6 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center font-mono font-bold text-xs text-slate-800 shrink-0">
                                    {p.shirt || idx + 1}
                                  </span>
                                  <div className="min-w-0">
                                    <div className="flex items-center gap-1.5 flex-wrap">
                                      <span className="font-bold text-slate-900 group-hover:text-[#38003c] transition-colors truncate text-xs sm:text-sm">
                                        {p.name}
                                      </span>
                                      {p.captain && (
                                        <span className="text-[9px] font-black px-1.5 py-0.2 rounded bg-amber-200 text-amber-900 shrink-0">
                                          KAPTAN
                                        </span>
                                      )}
                                      {pStat?.goals > 0 && (
                                        <span className="text-[9px] bg-emerald-100 text-emerald-800 font-bold px-1 rounded border border-emerald-300 shrink-0">
                                          ⚽ {pStat.goals}
                                        </span>
                                      )}
                                      {pStat?.assists > 0 && (
                                        <span className="text-[9px] bg-purple-100 text-purple-800 font-bold px-1 rounded border border-purple-300 shrink-0">
                                          🎯 {pStat.assists}
                                        </span>
                                      )}
                                      {pStat?.red_cards > 0 ? (
                                        <RedCardIcon />
                                      ) : pStat?.yellow_cards > 0 ? (
                                        <YellowCardIcon />
                                      ) : null}
                                    </div>
                                  </div>
                                </div>
                                <div className="flex items-center gap-2 shrink-0">
                                  {effectiveRating != null ? (
                                    <span
                                      className={`text-[10px] font-mono font-black px-1.5 py-0.5 rounded border ${
                                        effectiveRating >= 7.5
                                          ? 'bg-emerald-50 text-emerald-800 border-emerald-300'
                                          : effectiveRating >= 6.5
                                          ? 'bg-sky-50 text-sky-800 border-sky-300'
                                          : effectiveRating >= 5.5
                                          ? 'bg-slate-50 text-slate-700 border-slate-300'
                                          : 'bg-rose-50 text-rose-800 border-rose-300'
                                      }`}
                                      title={isCompleted ? `Maç Performans Reytingi: ${Number(effectiveRating).toFixed(1)}/10` : `Form Puanı: ${Number(effectiveRating).toFixed(1)}/10`}
                                    >
                                      {Number(effectiveRating).toFixed(1)}
                                    </span>
                                  ) : isCompleted ? (
                                    <span className="text-[10px] font-mono text-slate-400 px-1" title="Değerlendirilmedi">
                                      —
                                    </span>
                                  ) : null}
                                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md border ${getPositionBadgeClass(p.position)}`}>
                                    {formatPosition(p.position)}
                                  </span>
                                  <ExternalLink className="w-3.5 h-3.5 text-slate-300 group-hover:text-slate-600 transition-colors" />
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Substitutes Bench */}
                  {awayLineup?.substitutes?.length > 0 && (
                    <div className="pt-4 border-t border-slate-200 space-y-2.5">
                      <span className="text-xs font-black uppercase tracking-wider text-slate-800 block">
                        Yedek Kulübesi ({awayLineup.substitutes.length})
                      </span>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {awayLineup.substitutes.map((sub, idx) => {
                          const pStat = (playerStats?.away || []).find(ps => String(ps.id) === String(sub.id));
                          const effectiveRating = (isCompleted && pStat?.rating != null) ? pStat.rating : (pStat?.rating != null ? pStat.rating : sub.rating);

                          return (
                            <div 
                              key={sub.id || idx}
                              onClick={(e) => handlePlayerClick(sub, 'away', e)}
                              className="flex items-center justify-between p-2 rounded-xl bg-white border border-slate-200 hover:border-slate-300 hover:bg-slate-50 transition-all cursor-pointer group text-xs shadow-2xs"
                              title={`${sub.name} maç performansını görüntüle`}
                            >
                              <div className="flex items-center gap-2 min-w-0">
                                <PlayerAvatar 
                                  photoUrl={sub.photo_url}
                                  name={sub.name}
                                  shirt={sub.shirt}
                                  fallback="initials"
                                  size="w-6 h-6 text-[10px]"
                                  className="shrink-0"
                                />
                                <span className="font-mono text-xs font-bold text-slate-500">#{sub.shirt}</span>
                                <span className="font-medium text-slate-800 truncate">{sub.name}</span>
                                {pStat?.goals > 0 && <span className="text-[9px] bg-emerald-100 text-emerald-800 font-bold px-1 rounded border border-emerald-300">⚽ {pStat.goals}</span>}
                                {pStat?.assists > 0 && <span className="text-[9px] bg-purple-100 text-purple-800 font-bold px-1 rounded border border-purple-300">🎯 {pStat.assists}</span>}
                                {pStat?.red_cards > 0 ? <RedCardIcon /> : pStat?.yellow_cards > 0 ? <YellowCardIcon /> : null}
                              </div>
                              <div className="flex items-center gap-1.5 shrink-0">
                                {effectiveRating != null && (
                                  <span className={`text-[10px] font-mono font-black px-1.5 py-0.2 rounded border ${
                                    effectiveRating >= 7.5 ? 'bg-emerald-50 text-emerald-800 border-emerald-300' :
                                    effectiveRating >= 6.5 ? 'bg-sky-50 text-sky-800 border-sky-300' :
                                    effectiveRating >= 5.5 ? 'bg-slate-50 text-slate-700 border-slate-300' :
                                    'bg-rose-50 text-rose-800 border-rose-300'
                                  }`}>
                                    {Number(effectiveRating).toFixed(1)}
                                  </span>
                                )}
                                <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded border shrink-0 ${getPositionBadgeClass(sub.position)}`}>
                                  {formatPosition(sub.position)}
                                </span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>

                  </div>
                )}
              </>
            )}
          </div>

        
  );
}
