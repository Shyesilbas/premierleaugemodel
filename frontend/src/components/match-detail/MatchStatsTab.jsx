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
                  <h3 className="text-sm font-semibold text-text-primary">
                    Takım Karşılaştırmalı İstatistikleri
                  </h3>
                  <p className="text-xs text-text-secondary">
                    İki takımın maç boyunca ürettiği tüm metrikler
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-4 text-xs font-semibold tabular-nums">
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
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {teamStats.map((cat, catIdx) => (
                  <div 
                    key={catIdx} 
                    className="bg-background-primary border border-border rounded p-4 space-y-4"
                  >
                    <h4 className="text-xs font-semibold text-text-primary pb-2 border-b border-border flex items-center justify-between">
                      <span>{cat.category}</span>
                      <span className="text-xs tabular-nums px-2 py-0.5 rounded-sm bg-background-tertiary text-text-primary">
                        {cat.items.length} Metrik
                      </span>
                    </h4>

                    <div className="space-y-3">
                      {cat.items.map((item, itemIdx) => {
                        const { homePct, awayPct } = calcBarWidths(item);
                        const hVal = item.home !== undefined ? item.home : '-';
                        const aVal = item.away !== undefined ? item.away : '-';
                        const suffix = item.suffix || '';
                        const isNotFound = (hVal === 'Veri yok' && aVal === 'Veri yok') || Boolean(item.notFound);
                        const isXg = Boolean(item.isXg || item.label?.includes('xG'));

                        return (
                          <div key={itemIdx} className={`space-y-1.5 text-xs ${isXg ? 'bg-background-tertiary p-2.5 rounded border border-status-error' : ''}`}>
                            <div className="flex items-center justify-between text-xs font-semibold text-text-primary">
                              <span className={`tabular-nums min-w-10 ${isXg ? 'text-status-error font-semibold text-sm' : 'font-semibold text-text-primary'}`}>
                                {hVal === 'Veri yok' ? (
                                  <span className="text-text-tertiary font-normal text-xs">Yok</span>
                                ) : (
                                  `${hVal}${suffix}`
                                )}
                              </span>
                              <span className={`font-semibold text-center truncate px-2 ${isXg ? 'text-status-error font-semibold' : 'text-text-primary'}`}>
                                {item.label}
                              </span>
                              <span className={`tabular-nums min-w-10 text-right ${isXg ? 'text-status-error font-semibold text-sm' : 'font-semibold text-text-primary'}`}>
                                {aVal === 'Veri yok' ? (
                                  <span className="text-text-tertiary font-normal text-xs">Yok</span>
                                ) : (
                                  `${aVal}${suffix}`
                                )}
                              </span>
                            </div>

                            {/* Dual Bar */}
                            {isNotFound ? (
                              <div className="h-2 rounded-sm overflow-hidden bg-background-tertiary border border-dashed border-border" title="Veri Bulunamadı" />
                            ) : (
                              <div className="h-2 rounded-sm overflow-hidden flex bg-background-tertiary gap-0.5">
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
