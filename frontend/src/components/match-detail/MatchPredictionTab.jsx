export default function MatchPredictionTab({ prediction, loadingPrediction, predSubTab, setPredSubTab, homeTeam, awayTeam, variant = 'page' }) {
  const containerClass = variant === 'modal' ? 'space-y-4 max-w-2xl mx-auto py-1' : 'space-y-3 max-w-xl mx-auto py-2';
  return (
    <div className={containerClass}>

                {loadingPrediction || !prediction ? (
                  <div className="py-12 text-center">
                    <div className="w-6 h-6 border-2 border-slate-900 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                    <p className="text-xs font-semibold text-slate-700">Tahminler hesaplanıyor...</p>
                  </div>
                ) : (
                  <>
                    {/* Category Tabs */}
                    <div className="flex items-center justify-center gap-1.5 p-1 bg-slate-100 rounded-xl border border-slate-200">
                      <button
                        onClick={() => setPredSubTab('outcome')}
                        className={`flex-1 py-1.5 text-xs font-bold rounded-lg transition-all ${
                          predSubTab === 'outcome'
                            ? 'bg-white text-slate-900 shadow-xs'
                            : 'text-slate-600 hover:text-slate-900'
                        }`}
                      >
                        Maç Sonucu (1X2)
                      </button>
                      <button
                        onClick={() => setPredSubTab('goals')}
                        className={`flex-1 py-1.5 text-xs font-bold rounded-lg transition-all ${
                          predSubTab === 'goals'
                            ? 'bg-white text-slate-900 shadow-xs'
                            : 'text-slate-600 hover:text-slate-900'
                        }`}
                      >
                        Goller & Piyasalar
                      </button>
                      <button
                        onClick={() => setPredSubTab('stats')}
                        className={`flex-1 py-1.5 text-xs font-bold rounded-lg transition-all ${
                          predSubTab === 'stats'
                            ? 'bg-white text-slate-900 shadow-xs'
                            : 'text-slate-600 hover:text-slate-900'
                        }`}
                      >
                        Diğer İstatistikler
                      </button>
                    </div>

                    {/* TAB 1: MAÇ SONUCU (1X2) */}
                    {predSubTab === 'outcome' && (
                      <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 animate-fadeIn space-y-3">
                        <div className="flex items-center justify-between pb-2 border-b border-slate-200 text-xs">
                          <span className="font-bold text-slate-800">1X2 Olasılık Dağılımı</span>
                          <span className="font-semibold text-slate-600 bg-white px-2 py-0.5 rounded border border-slate-200">
                            Favori: {prediction.favorite_label}
                          </span>
                        </div>

                        <div className="grid grid-cols-3 gap-3 pt-1 text-center">
                          <div className="bg-white p-3 rounded-lg border border-slate-200">
                            <span className="text-xs font-semibold text-slate-600 truncate block">{homeTeam.name}</span>
                            <div className="text-2xl font-black font-mono text-slate-900 my-1">%{prediction.outcome.home_win_pct}</div>
                            <span className="text-[11px] text-slate-400">1 (Ev Sahibi)</span>
                          </div>

                          <div className="bg-white p-3 rounded-lg border border-slate-200">
                            <span className="text-xs font-semibold text-slate-600 block">Beraberlik</span>
                            <div className="text-2xl font-black font-mono text-slate-900 my-1">%{prediction.outcome.draw_pct}</div>
                            <span className="text-[11px] text-slate-400">X (Eşitlik)</span>
                          </div>

                          <div className="bg-white p-3 rounded-lg border border-slate-200">
                            <span className="text-xs font-semibold text-slate-600 truncate block">{awayTeam.name}</span>
                            <div className="text-2xl font-black font-mono text-slate-900 my-1">%{prediction.outcome.away_win_pct}</div>
                            <span className="text-[11px] text-slate-400">2 (Deplasman)</span>
                          </div>
                        </div>

                        <div className="h-1.5 rounded-full bg-slate-200 overflow-hidden flex mt-2">
                          <div style={{ width: `${prediction.outcome.home_win_pct}%` }} className="h-full bg-slate-900" />
                          <div style={{ width: `${prediction.outcome.draw_pct}%` }} className="h-full bg-slate-400" />
                          <div style={{ width: `${prediction.outcome.away_win_pct}%` }} className="h-full bg-emerald-600" />
                        </div>
                      </div>
                    )}

                    {/* TAB 2: GOLLER & PİYASALAR */}
                    {predSubTab === 'goals' && (
                      <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 animate-fadeIn space-y-4">
                        <div className="flex items-center justify-between pb-2 border-b border-slate-200 text-xs">
                          <span className="font-bold text-slate-800">Toplam Gol Beklentisi & İhtimaller</span>
                          <span className="font-mono text-slate-600">
                            Toplam Beklenen Gol: <strong className="text-slate-900 text-sm">{prediction.goals?.expected_total_goals || (Number(prediction.goals?.expected_home_goals || 1.4) + Number(prediction.goals?.expected_away_goals || 1.2)).toFixed(2)}</strong>
                          </span>
                        </div>

                        <div className="text-xs text-slate-600 flex justify-between px-1">
                          <span>{homeTeam.name}: <strong className="text-slate-900">{prediction.goals?.expected_home_goals || '1.4'}</strong> gol</span>
                          <span>{awayTeam.name}: <strong className="text-slate-900">{prediction.goals?.expected_away_goals || '1.2'}</strong> gol</span>
                        </div>

                        <div className="grid grid-cols-4 gap-2 pt-1 text-center">
                          <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                            <span className="text-[11px] text-slate-500 block">1.5 Üst</span>
                            <strong className="text-lg font-black font-mono text-slate-900">%{prediction.goals?.['over_1.5']?.pct || '75.0'}</strong>
                          </div>
                          <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                            <span className="text-[11px] text-slate-500 block">2.5 Üst</span>
                            <strong className="text-lg font-black font-mono text-slate-900">%{prediction.outcome?.over_2_5_goals_pct}</strong>
                          </div>
                          <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                            <span className="text-[11px] text-slate-500 block">3.5 Üst</span>
                            <strong className="text-lg font-black font-mono text-slate-900">%{prediction.goals?.['over_3.5']?.pct || '32.0'}</strong>
                          </div>
                          <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                            <span className="text-[11px] text-slate-500 block">KG Var</span>
                            <strong className="text-lg font-black font-mono text-slate-900">%{prediction.goals?.btts_pct || '55.0'}</strong>
                          </div>
                        </div>

                        {/* TAKIM BAZLI GOL BAREMLERİ (TEAM TOTALS) */}
                        {prediction.goals?.team_totals && (
                          <div className="pt-2 border-t border-slate-200 space-y-2.5">
                            <div className="flex items-center justify-between">
                              <span className="text-xs font-bold text-slate-800">
                                Tek Taraflı Takım Gol Baremleri
                              </span>
                              <span className="text-[10px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full">
                                Dinamik Barem Çıkarımı
                              </span>
                            </div>

                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                              {['home', 'away'].map((side) => {
                                const teamData = prediction.goals.team_totals[side];
                                const teamObj = side === 'home' ? homeTeam : awayTeam;
                                if (!teamData) return null;

                                return (
                                  <div key={side} className="bg-white rounded-xl border border-slate-200 p-3 space-y-2 shadow-2xs">
                                    <div className="flex items-center justify-between pb-1.5 border-b border-slate-100">
                                      <div className="min-w-0 pr-1">
                                        <span className="text-xs font-bold text-slate-900 block truncate">{teamObj.name}</span>
                                        <span className="text-[10px] text-slate-500">λ = {teamData.expected_goals} beklenen gol</span>
                                      </div>
                                      <div className="text-right shrink-0">
                                        <span className="text-[9px] uppercase font-bold tracking-wider text-slate-400 block">Ana Çizgi</span>
                                        <span className="text-[11px] font-mono font-black text-indigo-700 bg-indigo-50 px-1.5 py-0.5 rounded border border-indigo-100">
                                          {teamData.primary_line} Üst
                                        </span>
                                      </div>
                                    </div>

                                    <div className="space-y-1.5 text-xs">
                                      {Object.entries(teamData.lines).map(([lineStr, lineData]) => {
                                        const isPrimary = Number(lineStr) === teamData.primary_line;
                                        return (
                                          <div 
                                            key={lineStr} 
                                            className={`flex items-center justify-between px-2 py-1.5 rounded-lg transition-colors ${
                                              isPrimary 
                                                ? 'bg-amber-50/80 border border-amber-200 font-semibold text-slate-900' 
                                                : 'bg-slate-50 border border-slate-100 text-slate-700'
                                            }`}
                                          >
                                            <div className="flex items-center gap-1.5">
                                              <span className="font-mono font-bold text-slate-900">{lineStr} Üst</span>
                                              {isPrimary && (
                                                <span className="text-[9px] bg-amber-500 text-white px-1 py-0.5 rounded font-bold uppercase tracking-wider">
                                                  Piyasa
                                                </span>
                                              )}
                                            </div>
                                            <div className="flex items-center gap-1.5 font-mono text-[11px]">
                                              <span className="text-emerald-700 font-bold">%{lineData.over_pct}</span>
                                              <span className="text-slate-500 font-medium">({lineData.fair_odds_over})</span>
                                              <span className="text-slate-300">|</span>
                                              <span className="text-slate-400 text-[10px]">Alt: %{lineData.under_pct}</span>
                                            </div>
                                          </div>
                                        );
                                      })}
                                    </div>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* TAB 3: DİĞER İSTATİSTİKLER */}
                    {predSubTab === 'stats' && (
                      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden divide-y divide-slate-100 text-xs animate-fadeIn">
                        
                        {/* Korner */}
                        <div className="p-3 flex items-center justify-between">
                          <div>
                            <span className="font-bold text-slate-900 block">Korner</span>
                            <span className="text-slate-500 text-[11px]">{homeTeam.short}: {prediction.corners.expected_home} • {awayTeam.short}: {prediction.corners.expected_away}</span>
                          </div>
                          <div className="text-right">
                            <span className="font-mono font-black text-slate-900 text-base">{prediction.corners.expected_total} korner</span>
                            <span className="text-slate-500 text-[11px] block">9.5 Üst: %{prediction.corners.prob_over_9_5_pct}</span>
                          </div>
                        </div>

                        {/* Kart & Hakem */}
                        <div className="p-3 flex items-center justify-between">
                          <div>
                            <span className="font-bold text-slate-900 block">Kart & Disiplin</span>
                            <span className="text-slate-500 text-[11px]">Hakem: {prediction.referee?.name || 'Belirtilmedi'} ({prediction.referee?.avg_cards || '4.0'} kart/m)</span>
                          </div>
                          <div className="text-right">
                            <span className="font-mono font-black text-slate-900 text-base">{prediction.cards?.expected_total || '4.2'} kart</span>
                            <span className="text-slate-500 text-[11px] block">3.5 Üst: %{prediction.cards?.prob_over_3_5_pct || '62.0'}</span>
                          </div>
                        </div>

                        {/* Şut & Kaleci */}
                        <div className="p-3 flex items-center justify-between">
                          <div>
                            <span className="font-bold text-slate-900 block">Şut & Kurtarış</span>
                            <span className="text-slate-500 text-[11px]">Kurtarış: {homeTeam.short} ({prediction.saves.expected_home}) • {awayTeam.short} ({prediction.saves.expected_away})</span>
                          </div>
                          <div className="text-right">
                            <span className="font-mono font-black text-slate-900 text-base">{prediction.shots?.expected_total || '26.0'} şut</span>
                            <span className="text-slate-500 text-[11px] block">{prediction.saves.expected_total} kaleci kurtarışı</span>
                          </div>
                        </div>

                        {/* Taç & Ofsayt */}
                        <div className="p-3 flex items-center justify-between">
                          <div>
                            <span className="font-bold text-slate-900 block">Taç & Ofsayt</span>
                            <span className="text-slate-500 text-[11px]">Taktik: {(prediction.offsides?.expected_total || 3.3) >= 3.6 ? 'Yüksek Savunma Hattı' : 'Derin Blok Savunma'}</span>
                          </div>
                          <div className="text-right">
                            <span className="font-mono font-black text-slate-900 text-base">{prediction.throws.expected_total} taç</span>
                            <span className="text-slate-500 text-[11px] block">{prediction.offsides?.expected_total || '3.3'} ofsayt</span>
                          </div>
                        </div>

                      </div>
                    )}
                  </>
                )}

              </div>
  );
}
