import PlayerAvatar from '../PlayerAvatar';

export default function MatchModalLineupsTab({ homeLineup, awayLineup, homeTeam, awayTeam, formatPosition, getPositionBadgeClass }) {
  return (
    <div className="space-y-6">
                  {!homeLineup && !awayLineup ? (
                    <div className="py-12 text-center text-xs text-text-secondary font-medium">
                      Bu maç için henüz resmi kadro verisi yayınlanmamış.
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      
                      {/* Home Team Lineup */}
                      <div className="bg-background-tertiary border border-border rounded p-4 space-y-3">
                        <div className="flex items-center justify-between pb-2 border-b border-border">
                          <div className="flex items-center gap-2">
                            <img src={homeTeam.badge} alt="" className="w-5 h-5 object-contain" />
                            <h4 className="font-semibold text-xs text-text-primary">{homeTeam.name}</h4>
                          </div>
                          {homeLineup?.formation && (
                            <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded bg-background-tertiary text-primary">
                              Diziliş: {homeLineup.formation}
                            </span>
                          )}
                        </div>

                        <div className="space-y-1.5">
                          <span className="text-xs font-semibold uppercase tracking-wider text-text-secondary block">
                            Başlangıç 11'i ({homeLineup?.starters?.length || 0}) • Pozisyon Sıralı
                          </span>
                          {homeLineup?.starters?.map((p, idx) => (
                            <div 
                              key={p.id || idx}
                              className="flex items-center justify-between p-2 rounded bg-background-primary border border-border hover:border-primary transition-colors text-xs"
                            >
                              <div className="flex items-center gap-2.5 min-w-0">
                                <PlayerAvatar 
                                  photoUrl={p.photo_url} 
                                  name={p.name} 
                                  shirt={p.shirt || idx + 1} 
                                  fallback="initials" 
                                  size="w-7 h-7 text-xs" 
                                  className="shrink-0" 
                                />
                                <span className="w-5 h-5 rounded-full bg-background-tertiary border border-border flex items-center justify-center font-mono font-semibold text-xs text-text-primary shrink-0">
                                  {p.shirt || idx + 1}
                                </span>
                                <span className="font-semibold text-text-primary truncate">{p.name}</span>
                                {p.captain && (
                                  <span className="text-xs font-semibold px-1 rounded bg-background-tertiary text-status-warning shrink-0">
                                    C
                                  </span>
                                )}
                              </div>
                              <span className={`text-xs font-semibold px-2 py-0.5 rounded-md border shrink-0 ${getPositionBadgeClass(p.position)}`}>
                                {formatPosition(p.position)}
                              </span>
                            </div>
                          ))}
                        </div>

                        {homeLineup?.substitutes?.length > 0 && (
                          <div className="pt-2 border-t border-border space-y-1.5">
                            <span className="text-xs font-semibold uppercase tracking-wider text-text-secondary block">
                              Yedekler ({homeLineup.substitutes.length})
                            </span>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                              {homeLineup.substitutes.map((sub, idx) => (
                                <div 
                                  key={sub.id || idx}
                                  className="flex items-center justify-between p-1.5 rounded bg-background-primary border border-border text-xs"
                                >
                                  <div className="flex items-center gap-2 min-w-0">
                                    <PlayerAvatar 
                                      photoUrl={sub.photo_url} 
                                      name={sub.name} 
                                      shirt={sub.shirt} 
                                      fallback="initials" 
                                      size="w-6 h-6 text-xs" 
                                      className="shrink-0" 
                                    />
                                    <span className="font-mono text-xs font-semibold text-text-secondary">#{sub.shirt}</span>
                                    <span className="font-medium text-text-primary truncate">{sub.name}</span>
                                  </div>
                                  <span className={`text-xs font-semibold px-1.5 py-0.5 rounded border shrink-0 ${getPositionBadgeClass(sub.position)}`}>
                                    {formatPosition(sub.position)}
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Away Team Lineup */}
                      <div className="bg-background-tertiary border border-border rounded p-4 space-y-3">
                        <div className="flex items-center justify-between pb-2 border-b border-border">
                          <div className="flex items-center gap-2">
                            <img src={awayTeam.badge} alt="" className="w-5 h-5 object-contain" />
                            <h4 className="font-semibold text-xs text-text-primary">{awayTeam.name}</h4>
                          </div>
                          {awayLineup?.formation && (
                            <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded bg-background-tertiary text-primary">
                              Diziliş: {awayLineup.formation}
                            </span>
                          )}
                        </div>

                        <div className="space-y-1.5">
                          <span className="text-xs font-semibold uppercase tracking-wider text-text-secondary block">
                            Başlangıç 11'i ({awayLineup?.starters?.length || 0}) • Pozisyon Sıralı
                          </span>
                          {awayLineup?.starters?.map((p, idx) => (
                            <div 
                              key={p.id || idx}
                              className="flex items-center justify-between p-2 rounded bg-background-primary border border-border hover:border-primary transition-colors text-xs"
                            >
                              <div className="flex items-center gap-2.5 min-w-0">
                                <PlayerAvatar 
                                  photoUrl={p.photo_url} 
                                  name={p.name} 
                                  shirt={p.shirt || idx + 1} 
                                  fallback="initials" 
                                  size="w-7 h-7 text-xs" 
                                  className="shrink-0" 
                                />
                                <span className="w-5 h-5 rounded-full bg-background-tertiary border border-border flex items-center justify-center font-mono font-semibold text-xs text-text-primary shrink-0">
                                  {p.shirt || idx + 1}
                                </span>
                                <span className="font-semibold text-text-primary truncate">{p.name}</span>
                                {p.captain && (
                                  <span className="text-xs font-semibold px-1 rounded bg-background-tertiary text-status-warning shrink-0">
                                    C
                                  </span>
                                )}
                              </div>
                              <span className={`text-xs font-semibold px-2 py-0.5 rounded-md border shrink-0 ${getPositionBadgeClass(p.position)}`}>
                                {formatPosition(p.position)}
                              </span>
                            </div>
                          ))}
                        </div>

                        {awayLineup?.substitutes?.length > 0 && (
                          <div className="pt-2 border-t border-border space-y-1.5">
                            <span className="text-xs font-semibold uppercase tracking-wider text-text-secondary block">
                              Yedekler ({awayLineup.substitutes.length})
                            </span>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                              {awayLineup.substitutes.map((sub, idx) => (
                                <div 
                                  key={sub.id || idx}
                                  className="flex items-center justify-between p-1.5 rounded bg-background-primary border border-border text-xs"
                                >
                                  <div className="flex items-center gap-2 min-w-0">
                                    <PlayerAvatar 
                                      photoUrl={sub.photo_url} 
                                      name={sub.name} 
                                      shirt={sub.shirt} 
                                      fallback="initials" 
                                      size="w-6 h-6 text-xs" 
                                      className="shrink-0" 
                                    />
                                    <span className="font-mono text-xs font-semibold text-text-secondary">#{sub.shirt}</span>
                                    <span className="font-medium text-text-primary truncate">{sub.name}</span>
                                  </div>
                                  <span className={`text-xs font-semibold px-1.5 py-0.5 rounded border shrink-0 ${getPositionBadgeClass(sub.position)}`}>
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
