import { Activity, CreditCard, Eye, Flag, Scale, Shield, Target } from 'lucide-react';

export default function PredictorMetricCards({ prediction, homeTeam, awayTeam }) {
  if (!prediction) return null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              
              {/* Corners */}
              <div className="bg-background-primary border border-border rounded p-5  hover:border-slate-300 transition-all flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <div className="flex items-center gap-2 text-text-secondary min-w-0">
                      <Flag className="w-4 h-4 shrink-0" />
                      <span className="text-xs font-bold uppercase tracking-wider truncate">Toplam Korner</span>
                    </div>
                  </div>

                  <div className="flex items-baseline gap-2 mb-2">
                    <span className="text-3xl sm:text-4xl font-semibold tracking-tight font-mono text-text-primary">
                      {prediction.corners.expected_total}
                    </span>
                    <span className="text-xs font-semibold text-text-secondary">beklenen korner</span>
                  </div>
                  <span className={`mb-3 inline-block text-xs font-semibold ${prediction.corners.model_skill === 'baseline' ? 'text-amber-700' : 'text-emerald-700'}`} title={prediction.corners.model_skill === 'baseline' ? 'Özellikli model beceri kapısını geçemedi; toplam tahmin eğitim ortalamasını kullanıyor.' : 'Tahmin beceri kapısını geçen özellikli modelden geliyor.'}>
                    {prediction.corners.model_skill === 'baseline' ? 'Veri ortalaması tabanlı tahmin' : 'Model tahmini'}
                  </span>

                  {/* Team split pill */}
                  <div className="flex items-center justify-between text-xs text-text-secondary font-medium bg-background-tertiary px-3 py-1.5 rounded border border-border-light mb-4">
                    <div className="flex items-center gap-1.5 truncate">
                      <span className="text-text-secondary">{homeTeam.abbr || homeTeam.short}:</span>
                      <strong className="text-text-primary font-mono font-bold">{prediction.corners.expected_home}</strong>
                    </div>
                    <span className="text-slate-300">•</span>
                    <div className="flex items-center gap-1.5 truncate">
                      <span className="text-text-secondary">{awayTeam.abbr || awayTeam.short}:</span>
                      <strong className="text-text-primary font-mono font-bold">{prediction.corners.expected_away}</strong>
                    </div>
                  </div>
                </div>

                <div className="space-y-2.5 pt-3 border-t border-border-light">
                  <div>
                    <div className="flex justify-between items-center text-xs mb-1">
                      <span className="text-text-secondary font-medium">9.5 Üst Olasılığı</span>
                      <span className="font-mono font-bold text-text-secondary bg-background-tertiary px-1.5 py-0.5 rounded text-xs">
                        %{prediction.corners.prob_over_9_5_pct}
                      </span>
                    </div>
                    <div className="h-1.5 rounded-full bg-background-tertiary overflow-hidden">
                      <div 
                        style={{ width: `${Math.min(100, Math.max(0, prediction.corners.prob_over_9_5_pct))}%` }}
                        className="h-full bg-slate-700 rounded-full"
                      />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between items-center text-xs mb-1">
                      <span className="text-text-secondary font-medium">10.5 Üst Olasılığı</span>
                      <span className="font-mono font-bold text-text-secondary bg-background-tertiary px-1.5 py-0.5 rounded text-xs">
                        %{prediction.corners.prob_over_10_5_pct}
                      </span>
                    </div>
                    <div className="h-1.5 rounded-full bg-background-tertiary overflow-hidden">
                      <div 
                        style={{ width: `${Math.min(100, Math.max(0, prediction.corners.prob_over_10_5_pct))}%` }}
                        className="h-full bg-background-tertiary0 rounded-full"
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Throws / Taç */}
              <div className="bg-background-primary border border-border rounded p-5  hover:border-slate-300 transition-all flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <div className="flex items-center gap-2 text-text-secondary min-w-0">
                      <Activity className="w-4 h-4 shrink-0" />
                      <span className="text-xs font-bold uppercase tracking-wider truncate">Toplam Taç</span>
                    </div>
                  </div>

                  <div className="flex items-baseline gap-2 mb-2">
                    <span className="text-3xl sm:text-4xl font-semibold tracking-tight font-mono text-text-primary">
                      {prediction.throws.expected_total}
                    </span>
                    <span className="text-xs font-semibold text-text-secondary">beklenen taç atışı</span>
                  </div>
                  <span className={`mb-3 inline-block text-xs font-semibold ${prediction.throws.model_skill === 'baseline' ? 'text-amber-700' : 'text-emerald-700'}`} title={prediction.throws.model_skill === 'baseline' ? 'Özellikli model beceri kapısını geçemedi; toplam tahmin eğitim ortalamasını kullanıyor.' : 'Tahmin beceri kapısını geçen özellikli modelden geliyor.'}>
                    {prediction.throws.model_skill === 'baseline' ? 'Veri ortalaması tabanlı tahmin' : 'Model tahmini'}
                  </span>

                  {/* Team split pill */}
                  <div className="flex items-center justify-between text-xs text-text-secondary font-medium bg-background-tertiary px-3 py-1.5 rounded border border-border-light mb-4">
                    <div className="flex items-center gap-1.5 truncate">
                      <span className="text-text-secondary">{homeTeam.abbr || homeTeam.short}:</span>
                      <strong className="text-text-primary font-mono font-bold">{prediction.throws.expected_home}</strong>
                    </div>
                    <span className="text-slate-300">•</span>
                    <div className="flex items-center gap-1.5 truncate">
                      <span className="text-text-secondary">{awayTeam.abbr || awayTeam.short}:</span>
                      <strong className="text-text-primary font-mono font-bold">{prediction.throws.expected_away}</strong>
                    </div>
                  </div>
                </div>

                <div className="space-y-2.5 pt-3 border-t border-border-light">
                  <div>
                    <div className="flex justify-between items-center text-xs mb-1">
                      <span className="text-text-secondary font-medium">33.5 Üst Olasılığı</span>
                      <span className="font-mono font-bold text-text-secondary bg-background-tertiary px-1.5 py-0.5 rounded text-xs">
                        %{prediction.throws.prob_over_33_5_pct}
                      </span>
                    </div>
                    <div className="h-1.5 rounded-full bg-background-tertiary overflow-hidden">
                      <div 
                        style={{ width: `${Math.min(100, Math.max(0, prediction.throws.prob_over_33_5_pct))}%` }}
                        className="h-full bg-slate-700 rounded-full"
                      />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between items-center text-xs mb-1">
                      <span className="text-text-secondary font-medium">36.5 Üst Olasılığı</span>
                      <span className="font-mono font-bold text-text-secondary bg-background-tertiary px-1.5 py-0.5 rounded text-xs">
                        %{prediction.throws.prob_over_36_5_pct}
                      </span>
                    </div>
                    <div className="h-1.5 rounded-full bg-background-tertiary overflow-hidden">
                      <div 
                        style={{ width: `${Math.min(100, Math.max(0, prediction.throws.prob_over_36_5_pct))}%` }}
                        className="h-full bg-background-tertiary0 rounded-full"
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Saves */}
              <div className="bg-background-primary border border-border rounded p-5  hover:border-slate-300 transition-all flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <div className="flex items-center gap-2 text-text-secondary min-w-0">
                      <Shield className="w-4 h-4 shrink-0" />
                      <span className="text-xs font-bold uppercase tracking-wider truncate">Kaleci Kurtarışları</span>
                    </div>
                  </div>

                  <div className="flex items-baseline gap-2 mb-2">
                    <span className="text-3xl sm:text-4xl font-semibold tracking-tight font-mono text-text-primary">
                      {prediction.saves.expected_total}
                    </span>
                    <span className="text-xs font-semibold text-text-secondary">toplam kurtarış</span>
                  </div>
                  <span className={`mb-3 inline-block text-xs font-semibold ${prediction.saves.model_skill === 'baseline' ? 'text-amber-700' : 'text-emerald-700'}`} title={prediction.saves.model_skill === 'baseline' ? 'Özellikli model beceri kapısını geçemedi; toplam tahmin eğitim ortalamasını kullanıyor.' : 'Tahmin beceri kapısını geçen özellikli modelden geliyor.'}>
                    {prediction.saves.model_skill === 'baseline' ? 'Veri ortalaması tabanlı tahmin' : 'Model tahmini'}
                  </span>

                  {/* Team split pill */}
                  <div className="flex items-center justify-between text-xs text-text-secondary font-medium bg-background-tertiary px-3 py-1.5 rounded border border-border-light mb-4">
                    <div className="flex items-center gap-1.5 truncate">
                      <span className="text-text-secondary">Ev GK:</span>
                      <strong className="text-text-primary font-mono font-bold">{prediction.saves.expected_home}</strong>
                    </div>
                    <span className="text-slate-300">•</span>
                    <div className="flex items-center gap-1.5 truncate">
                      <span className="text-text-secondary">Dep GK:</span>
                      <strong className="text-text-primary font-mono font-bold">{prediction.saves.expected_away}</strong>
                    </div>
                  </div>
                </div>

                <div className="space-y-2 pt-3 border-t border-border-light">
                  <div className="flex items-center justify-between text-xs p-2.5 rounded bg-background-tertiary border border-border-light gap-2">
                    <span className="text-text-secondary font-medium shrink-0">Kurtarış Baskısı</span>
                    <span className="font-bold text-text-secondary truncate text-right">
                      {prediction.saves.expected_away > prediction.saves.expected_home ? `${awayTeam.abbr || awayTeam.short} GK Yoğun` : `${homeTeam.abbr || homeTeam.short} GK Yoğun`}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-xs p-2.5 rounded bg-background-tertiary border border-border-light gap-2">
                    <span className="text-text-secondary font-medium shrink-0">Ceza Sahası Tehdidi</span>
                    <span className="font-mono font-bold text-text-secondary truncate text-right">Yüksek Hacim</span>
                  </div>
                </div>
              </div>

              {/* Offsides */}
              <div className="bg-background-primary border border-border rounded p-5  hover:border-slate-300 transition-all flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <div className="flex items-center gap-2 text-text-secondary min-w-0">
                      <Eye className="w-4 h-4 shrink-0" />
                      <span className="text-xs font-bold uppercase tracking-wider truncate">Yakalanılan Ofsayt</span>
                    </div>
                  </div>

                  <div className="flex items-baseline gap-2 mb-2">
                    <span className="text-3xl sm:text-4xl font-semibold tracking-tight font-mono text-text-primary">
                      {prediction.offsides?.expected_total || '3.3'}
                    </span>
                    <span className="text-xs font-semibold text-text-secondary">beklenen ofsayt</span>
                  </div>
                  <span className={`mb-3 inline-block text-xs font-semibold ${prediction.offsides?.model_skill === 'baseline' ? 'text-amber-700' : 'text-emerald-700'}`} title={prediction.offsides?.model_skill === 'baseline' ? 'Özellikli model beceri kapısını geçemedi; toplam tahmin eğitim ortalamasını kullanıyor.' : 'Tahmin beceri kapısını geçen özellikli modelden geliyor.'}>
                    {prediction.offsides?.model_skill === 'baseline' ? 'Veri ortalaması tabanlı tahmin' : 'Model tahmini'}
                  </span>

                  {/* Team split pill */}
                  <div className="flex items-center justify-between text-xs text-text-secondary font-medium bg-background-tertiary px-3 py-1.5 rounded border border-border-light mb-4">
                    <div className="flex items-center gap-1.5 truncate">
                      <span className="text-text-secondary">{homeTeam.abbr || homeTeam.short}:</span>
                      <strong className="text-text-primary font-mono font-bold">{prediction.offsides?.expected_home || '1.7'}</strong>
                    </div>
                    <span className="text-slate-300">•</span>
                    <div className="flex items-center gap-1.5 truncate">
                      <span className="text-text-secondary">{awayTeam.abbr || awayTeam.short}:</span>
                      <strong className="text-text-primary font-mono font-bold">{prediction.offsides?.expected_away || '1.6'}</strong>
                    </div>
                  </div>
                </div>

                <div className="space-y-2.5 pt-3 border-t border-border-light">
                  <div>
                    <div className="flex justify-between items-center text-xs mb-1">
                      <span className="text-text-secondary font-medium">3.5 Üst Olasılığı</span>
                      <span className="font-mono font-bold text-text-secondary bg-background-tertiary px-1.5 py-0.5 rounded text-xs">
                        %{prediction.offsides?.prob_over_3_5_pct || '45.0'}
                      </span>
                    </div>
                    <div className="h-1.5 rounded-full bg-background-tertiary overflow-hidden">
                      <div 
                        style={{ width: `${Math.min(100, Math.max(0, prediction.offsides?.prob_over_3_5_pct || 45))}%` }}
                        className="h-full bg-slate-700 rounded-full"
                      />
                    </div>
                    {prediction.outcome.over_2_5_source === 'baseline' && (
                      <span className="mt-1 block text-xs font-semibold text-amber-700">
                        Taban oran (model sinyali zayıf)
                      </span>
                    )}
                  </div>

                  {prediction.goals && (
                    <div className="grid grid-cols-2 gap-x-4 gap-y-2 mt-3 pt-3 border-t border-border-light text-xs">
                      <div className="flex justify-between text-text-secondary">
                        <span>1.5 Gol Üstü</span>
                        <strong className="text-text-primary font-mono">%{prediction.goals['over_1.5']?.pct}</strong>
                      </div>
                      <div className="flex justify-between text-text-secondary">
                        <span>3.5 Gol Üstü</span>
                        <strong className="text-text-primary font-mono">%{prediction.goals['over_3.5']?.pct}</strong>
                      </div>
                      <div className="flex justify-between text-text-secondary">
                        <span title={prediction.goals.btts_informative === false ? 'Model lig ortalamasından iyi değil; düşük ayırt edicilik' : undefined}>
                          Karşılıklı Gol{prediction.goals.btts_informative === false && ' (düşük ayırt edicilik)'}
                        </span>
                        <strong className="text-text-primary font-mono">%{prediction.goals.btts_pct}</strong>
                      </div>
                      <div className="flex justify-between text-text-secondary">
                        <span>Gol modeli λ</span>
                        <strong className="text-text-primary font-mono">
                          {prediction.goals.expected_home_goals} – {prediction.goals.expected_away_goals}
                        </strong>
                      </div>
                    </div>
                  )}

                  <div className="flex items-center justify-between text-xs p-2.5 rounded bg-background-tertiary border border-border-light gap-2">
                    <span className="text-text-secondary font-medium shrink-0">Taktiksel Çizgi</span>
                    <span className="font-bold text-text-secondary truncate text-right">
                      {(prediction.offsides?.expected_total || 3.3) >= 3.6 ? 'Yüksek Hat / Tuzak' : 'Derin Blok Savunma'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Cards & discipline */}
              <div className="bg-background-primary border border-border rounded p-5  hover:border-slate-300 transition-all flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <div className="flex items-center gap-2 text-text-secondary min-w-0">
                      <CreditCard className="w-4 h-4 shrink-0" />
                      <span className="text-xs font-bold uppercase tracking-wider truncate">Kartlar & Disiplin</span>
                    </div>
                  </div>

                  <div className="flex items-baseline gap-2 mb-2">
                    <span className="text-3xl sm:text-4xl font-semibold tracking-tight font-mono text-text-primary">
                      {prediction.cards?.expected_total || '4.2'}
                    </span>
                    <span className="text-xs font-semibold text-text-secondary">beklenen kart</span>
                  </div>
                  <span className={`mb-3 inline-block text-xs font-semibold ${prediction.cards?.model_skill === 'baseline' ? 'text-amber-700' : 'text-emerald-700'}`} title={prediction.cards?.model_skill === 'baseline' ? 'Özellikli model beceri kapısını geçemedi; toplam tahmin eğitim ortalamasını kullanıyor.' : 'Tahmin beceri kapısını geçen özellikli modelden geliyor.'}>
                    {prediction.cards?.model_skill === 'baseline' ? 'Veri ortalaması tabanlı tahmin' : 'Model tahmini'}
                  </span>

                  {/* Team split pill */}
                  <div className="flex items-center justify-between text-xs text-text-secondary font-medium bg-background-tertiary px-3 py-1.5 rounded border border-border-light mb-4">
                    <div className="flex items-center gap-1.5 truncate">
                      <span className="text-text-secondary">{homeTeam.abbr || homeTeam.short}:</span>
                      <strong className="text-text-primary font-mono font-bold">{prediction.cards?.expected_home || '2.1'}</strong>
                    </div>
                    <span className="text-slate-300">•</span>
                    <div className="flex items-center gap-1.5 truncate">
                      <span className="text-text-secondary">{awayTeam.abbr || awayTeam.short}:</span>
                      <strong className="text-text-primary font-mono font-bold">{prediction.cards?.expected_away || '2.1'}</strong>
                    </div>
                  </div>
                </div>

                <div className="space-y-2.5 pt-3 border-t border-border-light">
                  <div>
                    <div className="flex justify-between items-center text-xs mb-1">
                      <span className="text-text-secondary font-medium">3.5 Üst Olasılığı</span>
                      <span className="font-mono font-bold text-text-secondary bg-background-tertiary px-1.5 py-0.5 rounded text-xs">
                        %{prediction.cards?.prob_over_3_5_pct || '62.0'}
                      </span>
                    </div>
                    <div className="h-1.5 rounded-full bg-background-tertiary overflow-hidden">
                      <div 
                        style={{ width: `${Math.min(100, Math.max(0, prediction.cards?.prob_over_3_5_pct || 62))}%` }}
                        className="h-full bg-slate-700 rounded-full"
                      />
                    </div>
                  </div>

                  {prediction.lineup_analysis?.lineup_impact?.delta_cards != null && (
                    <div className="flex items-center justify-between text-xs p-2 rounded bg-amber-50/70 border border-amber-200 text-amber-950">
                      <span className="font-medium text-xs">11 Kart Risk Etkisi:</span>
                      <span className="font-mono font-bold text-xs">
                        {prediction.lineup_analysis.lineup_impact.delta_cards > 0 ? `+${prediction.lineup_analysis.lineup_impact.delta_cards}` : prediction.lineup_analysis.lineup_impact.delta_cards} Kart
                      </span>
                    </div>
                  )}

                  <div className="flex items-center justify-between text-xs p-2.5 rounded bg-background-tertiary border border-border-light gap-2">
                    <span className="text-text-secondary font-medium shrink-0 flex items-center gap-1">
                      <Scale className="w-3.5 h-3.5 text-text-muted" />
                      <span>Hakem:</span>
                    </span>
                    <span className="font-bold text-text-primary truncate text-right">
                      {prediction.referee?.name || 'Premier League Hakem Heyeti'} ({prediction.referee?.avg_cards || '4.2'} k/m)
                    </span>
                  </div>
                </div>
              </div>

              {/* Expected goals and shots */}
              <div className="bg-background-primary border border-border rounded p-5  hover:border-slate-300 transition-all flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <div className="flex items-center gap-2 text-text-secondary min-w-0">
                      <Target className="w-4 h-4 shrink-0" />
                      <span className="text-xs font-bold uppercase tracking-wider truncate">Gol Tahmini · Şut İstatistikleri</span>
                    </div>
                  </div>

                  <div className="flex items-baseline gap-2 mb-2">
                    <span className="text-3xl sm:text-4xl font-semibold tracking-tight font-mono text-text-primary">
                      {prediction.goals?.expected_total_goals || (Number(prediction.goals?.expected_home_goals || 1.4) + Number(prediction.goals?.expected_away_goals || 1.2)).toFixed(2)}
                    </span>
                    <span className="text-xs font-semibold text-text-secondary">beklenen toplam gol</span>
                  </div>

                  {/* Team split pill */}
                  <div className="flex items-center justify-between text-xs text-text-secondary font-medium bg-background-tertiary px-3 py-1.5 rounded border border-border-light mb-4">
                    <div className="flex items-center gap-1.5 truncate">
                      <span className="text-text-secondary">{homeTeam.abbr || homeTeam.short}:</span>
                      <strong className="text-text-primary font-mono font-bold">{prediction.goals?.expected_home_goals || '1.4'} gol</strong>
                    </div>
                    <span className="text-slate-300">•</span>
                    <div className="flex items-center gap-1.5 truncate">
                      <span className="text-text-secondary">{awayTeam.abbr || awayTeam.short}:</span>
                      <strong className="text-text-primary font-mono font-bold">{prediction.goals?.expected_away_goals || '1.2'} gol</strong>
                    </div>
                  </div>
                </div>

                <div className="space-y-2.5 pt-3 border-t border-border-light">
                  <div>
                    <div className="flex justify-between items-center text-xs mb-1">
                      <span className="text-text-secondary font-medium">2.5 Gol Üst Olasılığı</span>
                      <span className="font-mono font-bold text-text-secondary bg-background-tertiary px-1.5 py-0.5 rounded text-xs">
                        %{prediction.outcome.over_2_5_goals_pct}
                      </span>
                    </div>
                    <div className="h-1.5 rounded-full bg-background-tertiary overflow-hidden">
                      <div 
                        style={{ width: `${Math.min(100, Math.max(0, prediction.outcome.over_2_5_goals_pct))}%` }}
                        className="h-full bg-slate-700 rounded-full"
                      />
                    </div>
                  </div>

                  {prediction.goals?.team_totals && (
                    <div className="p-2.5 rounded bg-background-tertiary border border-border-light space-y-1.5 text-xs">
                      <div className="flex items-center justify-between font-medium text-text-secondary text-xs">
                        <span>Dinamik Takım Baremleri</span>
                        <span className="text-xs text-indigo-700 font-semibold bg-indigo-50 px-1.5 py-0.5 rounded border border-indigo-100">Ana Çizgi</span>
                      </div>
                      <div className="flex justify-between items-center text-text-secondary">
                        <span className="font-medium truncate">{homeTeam.abbr || homeTeam.short}:</span>
                        <span className="font-mono font-bold text-text-primary bg-background-primary px-2 py-0.5 rounded border border-border text-xs">
                          {prediction.goals.team_totals.home.primary_line} Üst (%{prediction.goals.team_totals.home.primary_over_pct} · {prediction.goals.team_totals.home.primary_fair_odds_over})
                        </span>
                      </div>
                      <div className="flex justify-between items-center text-text-secondary">
                        <span className="font-medium truncate">{awayTeam.abbr || awayTeam.short}:</span>
                        <span className="font-mono font-bold text-text-primary bg-background-primary px-2 py-0.5 rounded border border-border text-xs">
                          {prediction.goals.team_totals.away.primary_line} Üst (%{prediction.goals.team_totals.away.primary_over_pct} · {prediction.goals.team_totals.away.primary_fair_odds_over})
                        </span>
                      </div>
                    </div>
                  )}

                  <div className="flex items-center justify-between text-xs p-2.5 rounded bg-background-tertiary border border-border-light gap-2">
                    <span className="text-text-secondary font-medium shrink-0">Şut Beklentisi</span>
                    <span className="font-mono font-bold text-text-primary truncate text-right">
                      {prediction.shots.expected_total} Toplam Şut (~9 isabet)
                    </span>
                  </div>
                </div>
              </div>

            </div>
  );
}
