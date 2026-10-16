import { BarChart3 } from 'lucide-react';

export default function MatchStatsTab({ teamStats, homeTeam, awayTeam, calcBarWidths }) {
  return (

<div className="space-y-8">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-200">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-xl bg-slate-100 text-[#38003c]">
                  <BarChart3 className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-black uppercase tracking-wider text-slate-900">
                    Takım Karşılaştırmalı İstatistikleri
                  </h3>
                  <p className="text-xs text-slate-500">
                    İki takımın maç boyunca ürettiği tüm metrikler
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-4 text-xs font-bold font-mono">
                <span className="flex items-center gap-1.5 text-[#38003c]">
                  <span className="w-3 h-3 rounded-full bg-[#38003c]" />
                  {homeTeam.short}
                </span>
                <span className="flex items-center gap-1.5 text-emerald-700">
                  <span className="w-3 h-3 rounded-full bg-emerald-600" />
                  {awayTeam.short}
                </span>
              </div>
            </div>

            {teamStats.length === 0 ? (
              <div className="py-12 text-center text-sm text-slate-500 font-medium">
                Bu karşılaşma henüz oynanmadığı için takım istatistikleri bulunmamaktadır.
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {teamStats.map((cat, catIdx) => (
                  <div 
                    key={catIdx} 
                    className="bg-slate-50 border border-slate-200 rounded-2xl p-5 space-y-4 hover:border-slate-300 transition-colors"
                  >
                    <h4 className="text-xs font-black uppercase tracking-wider text-slate-800 pb-2 border-b border-slate-200 flex items-center justify-between">
                      <span>{cat.category}</span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-200 text-slate-700">
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
                          <div key={itemIdx} className={`space-y-1.5 text-xs ${isXg ? 'bg-rose-50/60 p-2.5 rounded-xl border border-rose-200/80' : ''}`}>
                            <div className="flex items-center justify-between text-xs font-semibold text-slate-700">
                              <span className={`font-mono min-w-[40px] ${isXg ? 'text-rose-700 font-black text-sm' : 'font-bold text-slate-900'}`}>
                                {hVal === 'Not Found' ? (
                                  <span className="text-slate-400 font-normal italic text-[11px]">Yok</span>
                                ) : (
                                  `${hVal}${suffix}`
                                )}
                              </span>
                              <span className={`font-bold text-center truncate px-2 ${isXg ? 'text-rose-900 font-black' : 'text-slate-700'}`}>
                                {item.label}
                              </span>
                              <span className={`font-mono min-w-[40px] text-right ${isXg ? 'text-rose-700 font-black text-sm' : 'font-bold text-slate-900'}`}>
                                {aVal === 'Not Found' ? (
                                  <span className="text-slate-400 font-normal italic text-[11px]">Yok</span>
                                ) : (
                                  `${aVal}${suffix}`
                                )}
                              </span>
                            </div>

                            {/* Dual Bar */}
                            {isNotFound ? (
                              <div className="h-2 rounded-full overflow-hidden bg-slate-100 border border-dashed border-slate-200" title="Veri Bulunamadı" />
                            ) : (
                              <div className="h-2 rounded-full overflow-hidden flex bg-slate-200 gap-0.5">
                                <div 
                                  style={{ width: `${homePct}%` }}
                                  className={`h-full transition-all duration-500 rounded-l-full ${isXg ? 'bg-rose-600' : 'bg-[#38003c]'}`}
                                />
                                <div 
                                  style={{ width: `${awayPct}%` }}
                                  className={`h-full transition-all duration-500 rounded-r-full ${isXg ? 'bg-pink-600' : 'bg-emerald-600'}`}
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
