import { BarChart3 } from 'lucide-react';

export default function MatchStatsTab({ teamStats, homeTeam, awayTeam, calcBarWidths }) {
  return (

<div className="space-y-8">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-border">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded bg-background-tertiary text-primary">
                  <BarChart3 className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold uppercase tracking-wider text-text-primary">
                    Takım Karşılaştırmalı İstatistikleri
                  </h3>
                  <p className="text-xs text-text-secondary">
                    İki takımın maç boyunca ürettiği tüm metrikler
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-4 text-xs font-semibold font-mono">
                <span className="flex items-center gap-1.5 text-primary">
                  <span className="w-3 h-3 rounded-full bg-primary" />
                  {homeTeam.short}
                </span>
                <span className="flex items-center gap-1.5 text-status-success">
                  <span className="w-3 h-3 rounded-full bg-background-tertiary" />
                  {awayTeam.short}
                </span>
              </div>
            </div>

            {teamStats.length === 0 ? (
              <div className="py-12 text-center text-sm text-text-secondary font-medium">
                Bu karşılaşma henüz oynanmadığı için takım istatistikleri bulunmamaktadır.
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {teamStats.map((cat, catIdx) => (
                  <div 
                    key={catIdx} 
                    className="bg-background-tertiary border border-border rounded p-5 space-y-4 hover:border-border transition-colors"
                  >
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-text-primary pb-2 border-b border-border flex items-center justify-between">
                      <span>{cat.category}</span>
                      <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-background-tertiary text-text-primary">
                        {cat.items.length} Metrik
                      </span>
                    </h4>

                    <div className="space-y-3">
                      {cat.items.map((item, itemIdx) => {
                        const { homePct, awayPct } = calcBarWidths(item);
                        const hVal = item.home !== undefined ? item.home : '-';
                        const aVal = item.away !== undefined ? item.away : '-';
                        const suffix = item.suffix || '';
                        const isNotFound = (hVal === 'Not Found' && aVal === 'Not Found') || Boolean(item.notFound);
                        const isXg = Boolean(item.isXg || item.label?.includes('xG'));

                        return (
                          <div key={itemIdx} className={`space-y-1.5 text-xs ${isXg ? 'bg-background-tertiary p-2.5 rounded border border-status-error' : ''}`}>
                            <div className="flex items-center justify-between text-xs font-semibold text-text-primary">
                              <span className={`font-mono min-w-[40px] ${isXg ? 'text-status-error font-semibold text-sm' : 'font-semibold text-text-primary'}`}>
                                {hVal === 'Not Found' ? (
                                  <span className="text-text-tertiary font-normal italic text-xs">Yok</span>
                                ) : (
                                  `${hVal}${suffix}`
                                )}
                              </span>
                              <span className={`font-semibold text-center truncate px-2 ${isXg ? 'text-status-error font-semibold' : 'text-text-primary'}`}>
                                {item.label}
                              </span>
                              <span className={`font-mono min-w-[40px] text-right ${isXg ? 'text-status-error font-semibold text-sm' : 'font-semibold text-text-primary'}`}>
                                {aVal === 'Not Found' ? (
                                  <span className="text-text-tertiary font-normal italic text-xs">Yok</span>
                                ) : (
                                  `${aVal}${suffix}`
                                )}
                              </span>
                            </div>

                            {/* Dual Bar */}
                            {isNotFound ? (
                              <div className="h-2 rounded-full overflow-hidden bg-background-tertiary border border-dashed border-border" title="Veri Bulunamadı" />
                            ) : (
                              <div className="h-2 rounded-full overflow-hidden flex bg-background-tertiary gap-0.5">
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

  );
}
