import { BarChart3, Users } from 'lucide-react';
import PlayerAvatar from '../PlayerAvatar';

export default function MatchModalStatsTab({ teamStats, homeTeam, awayTeam, calcBarWidths, playerStats, playerTabSide, setPlayerTabSide, formatPosition, getPositionBadgeClass }) {
  return (
    <div className="space-y-8">
                  
                  {/* 1. SECTION: Detailed Team Match Statistics (Sofascore Style) */}
                  <div className="space-y-4">
                    <div className="flex items-center justify-between pb-2 border-b border-border">
                      <div className="flex items-center gap-2">
                        <BarChart3 className="w-4 h-4 text-primary" />
                        <h4 className="text-xs font-semibold uppercase tracking-wider text-text-primary">
                          Takım Karşılaştırmalı İstatistikleri & Mikro-Metrikler
                        </h4>
                      </div>
                      <span className="text-xs font-mono font-semibold text-text-secondary">
                        Premier League Maç Verisi
                      </span>
                    </div>

                    {teamStats.length === 0 ? (
                      <div className="py-8 text-center text-xs text-text-secondary">
                        Bu karşılaşma henüz oynanmadığı için takım istatistikleri bulunmamaktadır.
                      </div>
                    ) : (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {teamStats.map((cat, catIdx) => (
                          <div 
                            key={catIdx} 
                            className="bg-background-tertiary border border-border rounded p-4 space-y-3"
                          >
                            <h5 className="text-xs font-semibold uppercase tracking-wider text-text-primary pb-1.5 border-b border-border flex items-center justify-between">
                              <span>{cat.category}</span>
                              <span className="text-xs font-mono px-1.5 py-0.5 rounded bg-background-tertiary text-text-primary">
                                {cat.items.length} Metrik
                              </span>
                            </h5>

                            <div className="space-y-2.5">
                              {cat.items.map((item, itemIdx) => {
                                const { homePct, awayPct } = calcBarWidths(item);
                                const hVal = item.home !== undefined ? item.home : '-';
                                const aVal = item.away !== undefined ? item.away : '-';
                                const suffix = item.suffix || '';
                                const isNotFound = (hVal === 'Not Found' && aVal === 'Not Found') || Boolean(item.notFound);
                                const isXg = Boolean(item.isXg || item.label?.includes('xG'));

                                return (
                                  <div key={itemIdx} className={`space-y-1 text-xs ${isXg ? 'bg-background-tertiary p-2 rounded border border-status-error' : ''}`}>
                                    <div className="flex items-center justify-between text-xs font-semibold text-text-primary">
                                      <span className={`font-mono min-w-[36px] ${isXg ? 'text-status-error font-semibold' : 'font-semibold text-text-primary'}`}>
                                        {hVal === 'Not Found' ? (
                                          <span className="text-text-tertiary font-normal italic text-xs">Not Found</span>
                                        ) : (
                                          `${hVal}${suffix}`
                                        )}
                                      </span>
                                      <span className={`font-medium text-center truncate px-2 ${isXg ? 'text-status-error font-semibold' : 'text-text-secondary'}`}>
                                        {item.label}
                                      </span>
                                      <span className={`font-mono min-w-[36px] text-right ${isXg ? 'text-status-error font-semibold' : 'font-semibold text-text-primary'}`}>
                                        {aVal === 'Not Found' ? (
                                          <span className="text-text-tertiary font-normal italic text-xs">Not Found</span>
                                        ) : (
                                          `${aVal}${suffix}`
                                        )}
                                      </span>
                                    </div>

                                    {/* Comparison Dual Bar */}
                                    {isNotFound ? (
                                      <div className="h-1.5 rounded-full overflow-hidden bg-background-tertiary border border-dashed border-border" title="Veri Bulunamadı" />
                                    ) : (
                                      <div className="h-1.5 rounded-full overflow-hidden flex bg-background-tertiary gap-0.5">
                                        <div 
                                          style={{ width: `${homePct}%` }}
                                          className={`h-full transition-all duration-500 rounded-l-full bg-primary`}
                                        />
                                        <div 
                                          style={{ width: `${awayPct}%` }}
                                          className={`h-full transition-all duration-500 rounded-r-full bg-text-tertiary`}
                                        />
                                      </div>
                                    )}
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* 2. SECTION: Player Match Scorecard Table */}
                  <div className="space-y-4 pt-4 border-t border-border">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-border">
                      <div className="flex items-center gap-2">
                        <Users className="w-4 h-4 text-primary" />
                        <h4 className="text-xs font-semibold uppercase tracking-wider text-text-primary">
                          Oyuncu Maç Performans Karnesi (Dakika, Şut, Faul, Ofsayt)
                        </h4>
                      </div>

                      {/* Home vs Away Player Selector */}
                      <div className="flex items-center bg-background-tertiary p-1 rounded border border-border gap-1">
                        <button
                          onClick={() => setPlayerTabSide('home')}
                          className={`flex items-center gap-1.5 px-3 py-1 rounded text-xs font-semibold transition-all ${
                            playerTabSide === 'home'
                              ? 'bg-primary text-white shadow-sm'
                              : 'text-text-secondary hover:text-text-primary'
                          }`}
                        >
                          <img src={homeTeam.badge} alt="" className="w-3.5 h-3.5 object-contain" />
                          <span>{homeTeam.short || homeTeam.name}</span>
                        </button>
                        <button
                          onClick={() => setPlayerTabSide('away')}
                          className={`flex items-center gap-1.5 px-3 py-1 rounded text-xs font-semibold transition-all ${
                            playerTabSide === 'away'
                              ? 'bg-primary text-white shadow-sm'
                              : 'text-text-secondary hover:text-text-primary'
                          }`}
                        >
                          <img src={awayTeam.badge} alt="" className="w-3.5 h-3.5 object-contain" />
                          <span>{awayTeam.short || awayTeam.name}</span>
                        </button>
                      </div>
                    </div>

                    {/* Player Table */}
                    {(!playerStats[playerTabSide] || playerStats[playerTabSide].length === 0) ? (
                      <div className="py-8 text-center text-xs text-text-secondary">
                        Bu takım için oyuncu maç istatistiği bulunamadı.
                      </div>
                    ) : (
                      <div className="overflow-x-auto rounded border border-border shadow-sm">
                        <table className="w-full text-left text-xs font-medium border-collapse min-w-[700px]">
                          <thead>
                            <tr className="bg-background-tertiary text-text-primary text-xs font-semibold border-b border-border">
                              <th className="py-2.5 px-3 text-center">#</th>
                              <th className="py-2.5 px-3">Oyuncu</th>
                              <th className="py-2.5 px-2 text-center">Mevki</th>
                              <th className="py-2.5 px-2 text-center">Süre</th>
                              <th className="py-2.5 px-2 text-center">Gol</th>
                              <th className="py-2.5 px-2 text-center">Asist</th>
                              <th className="py-2.5 px-2 text-center">Şut (İsb)</th>
                              <th className="py-2.5 px-2 text-center">Faul Yaptı</th>
                              <th className="py-2.5 px-2 text-center">Faul Aldı</th>
                              <th className="py-2.5 px-2 text-center">Ofsayt</th>
                              <th className="py-2.5 px-2 text-center">Kart</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-border-light bg-background-primary">
                            {playerStats[playerTabSide].map((p, idx) => (
                              <tr key={p.id || idx} className="hover:bg-background-tertiary transition-colors">
                                <td className="py-2.5 px-3 text-center font-mono font-semibold text-text-secondary">
                                  {p.shirt || '-'}
                                </td>
                                <td className="py-2.5 px-3 font-semibold text-text-primary">
                                  <div className="flex items-center gap-2.5">
                                    <PlayerAvatar 
                                      photoUrl={p.photo_url} 
                                      name={p.name} 
                                      shirt={p.shirt} 
                                      fallback="initials" 
                                      size="w-7 h-7 text-xs" 
                                      className="shrink-0" 
                                    />
                                    <div className="min-w-0">
                                      <div className="flex items-center gap-1">
                                        <span className="truncate">{p.name}</span>
                                        {p.captain && (
                                          <span className="text-xs font-semibold px-1 rounded bg-background-tertiary text-status-warning shrink-0">
                                            C
                                          </span>
                                        )}
                                      </div>
                                      {!p.is_starter && (
                                        <span className="text-xs text-primary font-mono block">
                                          Yedek (Sonradan Girdi)
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                </td>
                                <td className="py-2.5 px-2 text-center">
                                  <span className={`text-xs font-semibold px-2 py-0.5 rounded-md border ${getPositionBadgeClass(p.position)}`}>
                                    {formatPosition(p.position)}
                                  </span>
                                </td>
                                <td className="py-2.5 px-2 text-center font-mono font-semibold text-text-primary">
                                  {p.minutes}'
                                </td>
                                <td className="py-2.5 px-2 text-center font-mono font-semibold">
                                  {p.goals > 0 ? (
                                    <span className="text-status-success bg-background-tertiary px-1.5 py-0.5 rounded border border-status-success">
                                      {p.goals}
                                    </span>
                                  ) : (
                                    <span className="text-text-tertiary">0</span>
                                  )}
                                </td>
                                <td className="py-2.5 px-2 text-center font-mono font-semibold">
                                  {p.assists > 0 ? (
                                    <span className="text-primary bg-background-tertiary px-1.5 py-0.5 rounded border border-primary">
                                      {p.assists}
                                    </span>
                                  ) : (
                                    <span className="text-text-tertiary">0</span>
                                  )}
                                </td>
                                <td className="py-2.5 px-2 text-center font-mono font-semibold text-text-primary">
                                  {p.shots > 0 ? `${p.shots} (${p.shots_ontarget})` : <span className="text-text-tertiary">0</span>}
                                </td>
                                <td className="py-2.5 px-2 text-center font-mono font-semibold">
                                  {p.fouls_committed > 0 ? (
                                    <span className="text-status-error">{p.fouls_committed}</span>
                                  ) : (
                                    <span className="text-text-tertiary">0</span>
                                  )}
                                </td>
                                <td className="py-2.5 px-2 text-center font-mono font-semibold">
                                  {p.fouls_won > 0 ? (
                                    <span className="text-status-success">{p.fouls_won}</span>
                                  ) : (
                                    <span className="text-text-tertiary">0</span>
                                  )}
                                </td>
                                <td className="py-2.5 px-2 text-center font-mono font-semibold">
                                  {p.offsides > 0 ? (
                                    <span className="text-status-warning font-semibold">{p.offsides}</span>
                                  ) : (
                                    <span className="text-text-tertiary">0</span>
                                  )}
                                </td>
                                <td className="py-2.5 px-2 text-center">
                                  {p.yellow_cards > 0 && (
                                    <span className="inline-block w-2.5 h-3.5 bg-background-tertiary rounded  mr-1 align-middle" title="Sarı Kart" />
                                  )}
                                  {p.red_cards > 0 && (
                                    <span className="inline-block w-2.5 h-3.5 bg-background-tertiary rounded  mr-1 align-middle" title="Kırmızı Kart" />
                                  )}
                                  {p.yellow_cards === 0 && p.red_cards === 0 && <span className="text-text-tertiary">—</span>}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>

                </div>
  );
}
