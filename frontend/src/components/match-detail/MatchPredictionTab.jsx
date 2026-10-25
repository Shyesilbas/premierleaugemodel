import InlineError from '../common/InlineError';
import Skeleton from '../common/Skeleton';

export default function MatchPredictionTab({ prediction, loadingPrediction, predSubTab, setPredSubTab, homeTeam, awayTeam, variant = 'page', failed = false, onRetry }) {
  const containerClass = variant === 'modal' ? 'space-y-4 max-w-2xl mx-auto py-1' : 'space-y-3 max-w-xl mx-auto py-2';
  return (
    <div className={containerClass}>

                {loadingPrediction || (!prediction && !failed) ? (
                  <div className="space-y-3" role="status" aria-label="Yükleniyor">
                    <Skeleton className="h-10 w-full" />
                    <Skeleton className="h-24 w-full" />
                    <Skeleton className="h-24 w-full" />
                  </div>
                ) : !prediction ? (
                  <InlineError message="Tahminler alınamadı." onRetry={onRetry} />
                ) : (
                  <>
                    {/* Category Tabs */}
                    <div className="flex items-center justify-center gap-1.5 p-1 bg-background-tertiary rounded border border-border">
                      <button
                        onClick={() => setPredSubTab('outcome')}
                        className={`flex-1 py-1.5 text-xs font-semibold rounded transition-all ${
                          predSubTab === 'outcome'
                            ? 'bg-background-primary text-text-primary '
                            : 'text-text-secondary hover:text-text-primary'
                        }`}
                      >
                        Maç Sonucu (1X2)
                      </button>
                      <button
                        onClick={() => setPredSubTab('goals')}
                        className={`flex-1 py-1.5 text-xs font-semibold rounded transition-all ${
                          predSubTab === 'goals'
                            ? 'bg-background-primary text-text-primary '
                            : 'text-text-secondary hover:text-text-primary'
                        }`}
                      >
                        Goller & Piyasalar
                      </button>
                      <button
                        onClick={() => setPredSubTab('stats')}
                        className={`flex-1 py-1.5 text-xs font-semibold rounded transition-all ${
                          predSubTab === 'stats'
                            ? 'bg-background-primary text-text-primary '
                            : 'text-text-secondary hover:text-text-primary'
                        }`}
                      >
                        Diğer İstatistikler
                      </button>
                    </div>

                    {/* TAB 1: MAÇ SONUCU (1X2) */}
                    {predSubTab === 'outcome' && (
                      <div className="bg-background-primary border border-border rounded p-4 animate-fadeIn space-y-3">
                        <div className="flex items-center justify-between pb-2 border-b border-border text-xs">
                          <span className="font-semibold text-text-primary">1X2 Olasılık Dağılımı</span>
                          <span className="font-semibold text-text-secondary bg-background-tertiary px-2 py-0.5 rounded">
                            Favori: {prediction.favorite_label}
                          </span>
                        </div>

                        <div className="grid grid-cols-3 gap-3 pt-1 text-center">
                          <div className="bg-background-tertiary p-3 rounded">
                            <span className="text-xs font-semibold text-text-secondary truncate block">{homeTeam.name}</span>
                            <div className="text-2xl font-semibold tabular-nums text-text-primary my-1">%{prediction.outcome.home_win_pct}</div>
                            <span className="text-xs text-text-tertiary">1 (Ev Sahibi)</span>
                          </div>

                          <div className="bg-background-tertiary p-3 rounded">
                            <span className="text-xs font-semibold text-text-secondary block">Beraberlik</span>
                            <div className="text-2xl font-semibold tabular-nums text-text-primary my-1">%{prediction.outcome.draw_pct}</div>
                            <span className="text-xs text-text-tertiary">X (Eşitlik)</span>
                          </div>

                          <div className="bg-background-tertiary p-3 rounded">
                            <span className="text-xs font-semibold text-text-secondary truncate block">{awayTeam.name}</span>
                            <div className="text-2xl font-semibold tabular-nums text-text-primary my-1">%{prediction.outcome.away_win_pct}</div>
                            <span className="text-xs text-text-tertiary">2 (Deplasman)</span>
                          </div>
                        </div>

                        <div className="h-1.5 rounded-sm bg-background-tertiary overflow-hidden flex mt-2">
                          <div style={{ width: `${prediction.outcome.home_win_pct}%` }} className="h-full bg-primary" />
                          <div style={{ width: `${prediction.outcome.draw_pct}%` }} className="h-full bg-border" />
                          <div style={{ width: `${prediction.outcome.away_win_pct}%` }} className="h-full bg-text-tertiary" />
                        </div>
                      </div>
                    )}

                    {/* TAB 2: GOLLER & PİYASALAR */}
                    {predSubTab === 'goals' && (
                      <div className="bg-background-primary border border-border rounded p-4 animate-fadeIn space-y-4">
                        <div className="flex items-center justify-between pb-2 border-b border-border text-xs">
                          <span className="font-semibold text-text-primary">Toplam Gol Beklentisi & İhtimaller</span>
                          <span className="tabular-nums text-text-secondary">
                            Toplam Beklenen Gol: <strong className="text-text-primary text-sm">{prediction.goals?.expected_total_goals || (Number(prediction.goals?.expected_home_goals || 1.4) + Number(prediction.goals?.expected_away_goals || 1.2)).toFixed(2)}</strong>
                          </span>
                        </div>

                        <div className="text-xs text-text-secondary flex justify-between px-1">
                          <span>{homeTeam.name}: <strong className="text-text-primary">{prediction.goals?.expected_home_goals || '1.4'}</strong> gol</span>
                          <span>{awayTeam.name}: <strong className="text-text-primary">{prediction.goals?.expected_away_goals || '1.2'}</strong> gol</span>
                        </div>

                        <div className="grid grid-cols-4 gap-2 pt-1 text-center">
                          <div className="bg-background-tertiary p-2.5 rounded">
                            <span className="text-xs text-text-secondary block">1.5 Üst</span>
                            <strong className="text-lg font-semibold tabular-nums text-text-primary">%{prediction.goals?.['over_1.5']?.pct || '75.0'}</strong>
                          </div>
                          <div className="bg-background-tertiary p-2.5 rounded">
                            <span className="text-xs text-text-secondary block">2.5 Üst</span>
                            <strong className="text-lg font-semibold tabular-nums text-text-primary">%{prediction.outcome?.over_2_5_goals_pct}</strong>
                          </div>
                          <div className="bg-background-tertiary p-2.5 rounded">
                            <span className="text-xs text-text-secondary block">3.5 Üst</span>
                            <strong className="text-lg font-semibold tabular-nums text-text-primary">%{prediction.goals?.['over_3.5']?.pct || '32.0'}</strong>
                          </div>
                          <div className="bg-background-tertiary p-2.5 rounded">
                            <span className="text-xs text-text-secondary block">KG Var</span>
                            <strong className="text-lg font-semibold tabular-nums text-text-primary">%{prediction.goals?.btts_pct || '55.0'}</strong>
                          </div>
                        </div>

                        {/* TAKIM BAZLI GOL BAREMLERİ (TEAM TOTALS) */}
                        {prediction.goals?.team_totals && (
                          <div className="pt-2 border-t border-border space-y-2.5">
                            <div className="flex items-center justify-between">
                              <span className="text-xs font-semibold text-text-primary">
                                Tek Taraflı Takım Gol Baremleri
                              </span>
                              <span className="text-xs font-semibold text-status-success bg-background-tertiary border border-status-success px-2 py-0.5 rounded-sm">
                                Dinamik Barem Çıkarımı
                              </span>
                            </div>

                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                              {['home', 'away'].map((side) => {
                                const teamData = prediction.goals.team_totals[side];
                                const teamObj = side === 'home' ? homeTeam : awayTeam;
                                if (!teamData) return null;

                                return (
                                  <div key={side} className="bg-background-tertiary rounded p-3 space-y-2">
                                    <div className="flex items-center justify-between pb-1.5 border-b border-border-light">
                                      <div className="min-w-0 pr-1">
                                        <span className="text-xs font-semibold text-text-primary block truncate">{teamObj.name}</span>
                                        <span className="text-xs text-text-secondary">λ = {teamData.expected_goals} beklenen gol</span>
                                      </div>
                                      <div className="text-right shrink-0">
                                        <span className="text-xs font-semibold text-text-tertiary block">Ana Çizgi</span>
                                        <span className="text-xs tabular-nums font-semibold text-primary bg-background-tertiary px-1.5 py-0.5 rounded border border-primary">
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
                                            className={`flex items-center justify-between px-2 py-1.5 rounded transition-colors ${
                                              isPrimary 
                                                ? 'bg-background-tertiary border border-status-warning font-semibold text-text-primary' 
                                                : 'bg-background-tertiary border border-border-light text-text-primary'
                                            }`}
                                          >
                                            <div className="flex items-center gap-1.5">
                                              <span className="tabular-nums font-semibold text-text-primary">{lineStr} Üst</span>
                                              {isPrimary && (
                                                <span className="text-xs bg-background-tertiary text-text-primary px-1 py-0.5 rounded font-semibold">
                                                  Piyasa
                                                </span>
                                              )}
                                            </div>
                                            <div className="flex items-center gap-1.5 tabular-nums text-xs">
                                              <span className="text-status-success font-semibold">%{lineData.over_pct}</span>
                                              <span className="text-text-secondary font-medium">({lineData.fair_odds_over})</span>
                                              <span className="text-text-tertiary">|</span>
                                              <span className="text-text-tertiary text-xs">Alt: %{lineData.under_pct}</span>
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
                      <div className="bg-background-primary border border-border rounded overflow-hidden divide-y divide-border-light text-xs animate-fadeIn">
                        
                        {/* Korner */}
                        <div className="p-3 flex items-center justify-between">
                          <div>
                            <span className="font-semibold text-text-primary block">Korner</span>
                            <span className="text-text-secondary text-xs">{homeTeam.short}: {prediction.corners.expected_home} • {awayTeam.short}: {prediction.corners.expected_away}</span>
                          </div>
                          <div className="text-right">
                            <span className="tabular-nums font-semibold text-text-primary text-base">{prediction.corners.expected_total} korner</span>
                            <span className="text-text-secondary text-xs block">9.5 Üst: %{prediction.corners.prob_over_9_5_pct}</span>
                          </div>
                        </div>

                        {/* Kart & Hakem */}
                        <div className="p-3 flex items-center justify-between">
                          <div>
                            <span className="font-semibold text-text-primary block">Kart & Disiplin</span>
                            <span className="text-text-secondary text-xs">Hakem: {prediction.referee?.name || 'Belirtilmedi'} ({prediction.referee?.avg_cards || '4.0'} kart/m)</span>
                          </div>
                          <div className="text-right">
                            <span className="tabular-nums font-semibold text-text-primary text-base">{prediction.cards?.expected_total || '4.2'} kart</span>
                            <span className="text-text-secondary text-xs block">3.5 Üst: %{prediction.cards?.prob_over_3_5_pct || '62.0'}</span>
                          </div>
                        </div>

                        {/* Şut & Kaleci */}
                        <div className="p-3 flex items-center justify-between">
                          <div>
                            <span className="font-semibold text-text-primary block">Şut & Kurtarış</span>
                            <span className="text-text-secondary text-xs">Kurtarış: {homeTeam.short} ({prediction.saves.expected_home}) • {awayTeam.short} ({prediction.saves.expected_away})</span>
                          </div>
                          <div className="text-right">
                            <span className="tabular-nums font-semibold text-text-primary text-base">{prediction.shots?.expected_total || '26.0'} şut</span>
                            <span className="text-text-secondary text-xs block">{prediction.saves.expected_total} kaleci kurtarışı</span>
                          </div>
                        </div>

                        {/* Taç & Ofsayt */}
                        <div className="p-3 flex items-center justify-between">
                          <div>
                            <span className="font-semibold text-text-primary block">Taç & Ofsayt</span>
                            <span className="text-text-secondary text-xs">Taktik: {(prediction.offsides?.expected_total || 3.3) >= 3.6 ? 'Yüksek Savunma Hattı' : 'Derin Blok Savunma'}</span>
                          </div>
                          <div className="text-right">
                            <span className="tabular-nums font-semibold text-text-primary text-base">{prediction.throws.expected_total} taç</span>
                            <span className="text-text-secondary text-xs block">{prediction.offsides?.expected_total || '3.3'} ofsayt</span>
                          </div>
                        </div>

                      </div>
                    )}
                  </>
                )}

              </div>
  );
}
