import PlayerAvatar from '../PlayerAvatar';

export default function MatchModalLineupsTab({ homeLineup, awayLineup, homeTeam, awayTeam, formatPosition, getPositionBadgeClass }) {
  return (
    <div className="space-y-6">
                  {!homeLineup && !awayLineup ? (
                    <div className="py-12 text-center text-xs text-slate-500 font-medium">
                      Bu maç için henüz resmi kadro verisi yayınlanmamış.
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      
                      {/* Home Team Lineup */}
                      <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 space-y-3">
                        <div className="flex items-center justify-between pb-2 border-b border-slate-200">
                          <div className="flex items-center gap-2">
                            <img src={homeTeam.badge} alt="" className="w-5 h-5 object-contain" />
                            <h4 className="font-bold text-xs text-slate-900">{homeTeam.name}</h4>
                          </div>
                          {homeLineup?.formation && (
                            <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-purple-100 text-[#38003c]">
                              Diziliş: {homeLineup.formation}
                            </span>
                          )}
                        </div>

                        <div className="space-y-1.5">
                          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
                            Başlangıç 11'i ({homeLineup?.starters?.length || 0}) • Pozisyon Sıralı
                          </span>
                          {homeLineup?.starters?.map((p, idx) => (
                            <div 
                              key={p.id || idx}
                              className="flex items-center justify-between p-2 rounded-xl bg-white border border-slate-200/80 hover:border-purple-200 transition-colors text-xs"
                            >
                              <div className="flex items-center gap-2.5 min-w-0">
                                <PlayerAvatar 
                                  photoUrl={p.photo_url} 
                                  name={p.name} 
                                  shirt={p.shirt || idx + 1} 
                                  fallback="initials" 
                                  size="w-7 h-7 text-[10px]" 
                                  className="shrink-0" 
                                />
                                <span className="w-5 h-5 rounded-full bg-slate-100 border border-slate-300 flex items-center justify-center font-mono font-bold text-[10px] text-slate-800 shrink-0">
                                  {p.shirt || idx + 1}
                                </span>
                                <span className="font-bold text-slate-900 truncate">{p.name}</span>
                                {p.captain && (
                                  <span className="text-[9px] font-black px-1 rounded bg-amber-200 text-amber-900 shrink-0">
                                    C
                                  </span>
                                )}
                              </div>
                              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md border shrink-0 ${getPositionBadgeClass(p.position)}`}>
                                {formatPosition(p.position)}
                              </span>
                            </div>
                          ))}
                        </div>

                        {homeLineup?.substitutes?.length > 0 && (
                          <div className="pt-2 border-t border-slate-200 space-y-1.5">
                            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
                              Yedekler ({homeLineup.substitutes.length})
                            </span>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                              {homeLineup.substitutes.map((sub, idx) => (
                                <div 
                                  key={sub.id || idx}
                                  className="flex items-center justify-between p-1.5 rounded-xl bg-white border border-slate-200 text-xs"
                                >
                                  <div className="flex items-center gap-2 min-w-0">
                                    <PlayerAvatar 
                                      photoUrl={sub.photo_url} 
                                      name={sub.name} 
                                      shirt={sub.shirt} 
                                      fallback="initials" 
                                      size="w-6 h-6 text-[9px]" 
                                      className="shrink-0" 
                                    />
                                    <span className="font-mono text-[10px] font-bold text-slate-500">#{sub.shirt}</span>
                                    <span className="font-medium text-slate-800 truncate">{sub.name}</span>
                                  </div>
                                  <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border shrink-0 ${getPositionBadgeClass(sub.position)}`}>
                                    {formatPosition(sub.position)}
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Away Team Lineup */}
                      <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 space-y-3">
                        <div className="flex items-center justify-between pb-2 border-b border-slate-200">
                          <div className="flex items-center gap-2">
                            <img src={awayTeam.badge} alt="" className="w-5 h-5 object-contain" />
                            <h4 className="font-bold text-xs text-slate-900">{awayTeam.name}</h4>
                          </div>
                          {awayLineup?.formation && (
                            <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-purple-100 text-[#38003c]">
                              Diziliş: {awayLineup.formation}
                            </span>
                          )}
                        </div>

                        <div className="space-y-1.5">
                          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
                            Başlangıç 11'i ({awayLineup?.starters?.length || 0}) • Pozisyon Sıralı
                          </span>
                          {awayLineup?.starters?.map((p, idx) => (
                            <div 
                              key={p.id || idx}
                              className="flex items-center justify-between p-2 rounded-xl bg-white border border-slate-200/80 hover:border-purple-200 transition-colors text-xs"
                            >
                              <div className="flex items-center gap-2.5 min-w-0">
                                <PlayerAvatar 
                                  photoUrl={p.photo_url} 
                                  name={p.name} 
                                  shirt={p.shirt || idx + 1} 
                                  fallback="initials" 
                                  size="w-7 h-7 text-[10px]" 
                                  className="shrink-0" 
                                />
                                <span className="w-5 h-5 rounded-full bg-slate-100 border border-slate-300 flex items-center justify-center font-mono font-bold text-[10px] text-slate-800 shrink-0">
                                  {p.shirt || idx + 1}
                                </span>
                                <span className="font-bold text-slate-900 truncate">{p.name}</span>
                                {p.captain && (
                                  <span className="text-[9px] font-black px-1 rounded bg-amber-200 text-amber-900 shrink-0">
                                    C
                                  </span>
                                )}
                              </div>
                              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md border shrink-0 ${getPositionBadgeClass(p.position)}`}>
                                {formatPosition(p.position)}
                              </span>
                            </div>
                          ))}
                        </div>

                        {awayLineup?.substitutes?.length > 0 && (
                          <div className="pt-2 border-t border-slate-200 space-y-1.5">
                            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
                              Yedekler ({awayLineup.substitutes.length})
                            </span>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                              {awayLineup.substitutes.map((sub, idx) => (
                                <div 
                                  key={sub.id || idx}
                                  className="flex items-center justify-between p-1.5 rounded-xl bg-white border border-slate-200 text-xs"
                                >
                                  <div className="flex items-center gap-2 min-w-0">
                                    <PlayerAvatar 
                                      photoUrl={sub.photo_url} 
                                      name={sub.name} 
                                      shirt={sub.shirt} 
                                      fallback="initials" 
                                      size="w-6 h-6 text-[9px]" 
                                      className="shrink-0" 
                                    />
                                    <span className="font-mono text-[10px] font-bold text-slate-500">#{sub.shirt}</span>
                                    <span className="font-medium text-slate-800 truncate">{sub.name}</span>
                                  </div>
                                  <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border shrink-0 ${getPositionBadgeClass(sub.position)}`}>
                                    {formatPosition(sub.position)}
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>

                    </div>
                  )}
                </div>
  );
}
