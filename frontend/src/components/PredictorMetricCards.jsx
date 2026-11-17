import { Activity, CreditCard, Eye, Flag, Scale, Shield, Target } from 'lucide-react';

function SkillBadge({ skill }) {
  const isBaseline = skill === 'baseline';
  const title = isBaseline
    ? 'Özellikli model beceri kapısını geçemedi; toplam tahmin eğitim ortalamasını kullanıyor.'
    : 'Tahmin beceri kapısını geçen özellikli modelden geliyor.';

  return (
    <span
      className={`mb-3 inline-block text-xs font-semibold ${isBaseline ? 'text-status-warning' : 'text-status-success'}`}
      title={title}
    >
      {isBaseline ? 'Veri ortalaması tabanlı tahmin' : 'Model tahmini'}
    </span>
  );
}

function SplitPill({ leftLabel, leftVal, rightLabel, rightVal }) {
  return (
    <div className="flex items-center justify-between text-xs text-text-secondary font-medium bg-background-tertiary px-3 py-1.5 rounded border border-border-light mb-4">
      <div className="flex items-center gap-1.5 truncate">
        <span className="text-text-secondary">{leftLabel}:</span>
        <strong className="text-text-primary font-mono font-semibold tabular-nums">{leftVal}</strong>
      </div>
      <span className="text-text-muted" aria-hidden="true">·</span>
      <div className="flex items-center gap-1.5 truncate">
        <span className="text-text-secondary">{rightLabel}:</span>
        <strong className="text-text-primary font-mono font-semibold tabular-nums">{rightVal}</strong>
      </div>
    </div>
  );
}

function ProbRow({ label, pct, muted = false }) {
  const clamped = Math.min(100, Math.max(0, Number(pct) || 0));
  return (
    <div>
      <div className="flex justify-between items-center text-xs mb-1">
        <span className="text-text-secondary font-medium">{label}</span>
        <span className="font-mono font-semibold tabular-nums text-text-secondary bg-background-tertiary px-1.5 py-0.5 rounded text-xs">
          %{pct}
        </span>
      </div>
      <div className="h-1.5 rounded-full bg-background-tertiary overflow-hidden">
        <div
          style={{ width: `${clamped}%` }}
          className={`h-full rounded-full ${muted ? 'bg-text-tertiary' : 'bg-primary'}`}
        />
      </div>
    </div>
  );
}

export default function PredictorMetricCards({ prediction, homeTeam, awayTeam }) {
  if (!prediction) return null;

  const homeLabel = homeTeam.abbr || homeTeam.short;
  const awayLabel = awayTeam.abbr || awayTeam.short;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
      {/* Corners */}
      <div className="bg-background-primary border border-border rounded p-5 hover:border-card-border-hover transition-colors flex flex-col justify-between">
        <div>
          <div className="flex items-center gap-2 text-text-secondary min-w-0 mb-3">
            <Flag className="w-4 h-4 shrink-0" strokeWidth={1.5} aria-hidden="true" />
            <span className="text-xs font-semibold text-text-secondary truncate">Toplam Korner</span>
          </div>
          <div className="flex items-baseline gap-2 mb-2">
            <span className="text-3xl sm:text-4xl font-semibold tracking-tight font-mono tabular-nums text-text-primary">
              {prediction.corners.expected_total}
            </span>
            <span className="text-xs font-semibold text-text-secondary">beklenen korner</span>
          </div>
          <SkillBadge skill={prediction.corners.model_skill} />
          <SplitPill
            leftLabel={homeLabel}
            leftVal={prediction.corners.expected_home}
            rightLabel={awayLabel}
            rightVal={prediction.corners.expected_away}
          />
        </div>
        <div className="space-y-2.5 pt-3 border-t border-border-light">
          <ProbRow label="9.5 Üst Olasılığı" pct={prediction.corners.prob_over_9_5_pct} />
          <ProbRow label="10.5 Üst Olasılığı" pct={prediction.corners.prob_over_10_5_pct} muted />
        </div>
      </div>

      {/* Throws */}
      <div className="bg-background-primary border border-border rounded p-5 hover:border-card-border-hover transition-colors flex flex-col justify-between">
        <div>
          <div className="flex items-center gap-2 text-text-secondary min-w-0 mb-3">
            <Activity className="w-4 h-4 shrink-0" strokeWidth={1.5} aria-hidden="true" />
            <span className="text-xs font-semibold text-text-secondary truncate">Toplam Taç</span>
          </div>
          <div className="flex items-baseline gap-2 mb-2">
            <span className="text-3xl sm:text-4xl font-semibold tracking-tight font-mono tabular-nums text-text-primary">
              {prediction.throws.expected_total}
            </span>
            <span className="text-xs font-semibold text-text-secondary">beklenen taç atışı</span>
          </div>
          <SkillBadge skill={prediction.throws.model_skill} />
          <SplitPill
            leftLabel={homeLabel}
            leftVal={prediction.throws.expected_home}
            rightLabel={awayLabel}
            rightVal={prediction.throws.expected_away}
          />
        </div>
        <div className="space-y-2.5 pt-3 border-t border-border-light">
          <ProbRow label="33.5 Üst Olasılığı" pct={prediction.throws.prob_over_33_5_pct} />
          <ProbRow label="36.5 Üst Olasılığı" pct={prediction.throws.prob_over_36_5_pct} muted />
        </div>
      </div>

      {/* Saves */}
      <div className="bg-background-primary border border-border rounded p-5 hover:border-card-border-hover transition-colors flex flex-col justify-between">
        <div>
          <div className="flex items-center gap-2 text-text-secondary min-w-0 mb-3">
            <Shield className="w-4 h-4 shrink-0" strokeWidth={1.5} aria-hidden="true" />
            <span className="text-xs font-semibold text-text-secondary truncate">Kaleci Kurtarışları</span>
          </div>
          <div className="flex items-baseline gap-2 mb-2">
            <span className="text-3xl sm:text-4xl font-semibold tracking-tight font-mono tabular-nums text-text-primary">
              {prediction.saves.expected_total}
            </span>
            <span className="text-xs font-semibold text-text-secondary">toplam kurtarış</span>
          </div>
          <SkillBadge skill={prediction.saves.model_skill} />
          <SplitPill
            leftLabel="Ev GK"
            leftVal={prediction.saves.expected_home}
            rightLabel="Dep GK"
            rightVal={prediction.saves.expected_away}
          />
        </div>
        <div className="space-y-2 pt-3 border-t border-border-light">
          <div className="flex items-center justify-between text-xs p-2.5 rounded bg-background-tertiary border border-border-light gap-2">
            <span className="text-text-secondary font-medium shrink-0">Kurtarış Baskısı</span>
            <span className="font-semibold text-text-primary truncate text-right">
              {prediction.saves.expected_away > prediction.saves.expected_home ? `${awayLabel} GK Yoğun` : `${homeLabel} GK Yoğun`}
            </span>
          </div>
          <div className="flex items-center justify-between text-xs p-2.5 rounded bg-background-tertiary border border-border-light gap-2">
            <span className="text-text-secondary font-medium shrink-0">Ceza Sahası Tehdidi</span>
            <span className="font-mono font-semibold text-text-secondary truncate text-right">Yüksek Hacim</span>
          </div>
        </div>
      </div>

      {/* Offsides */}
      <div className="bg-background-primary border border-border rounded p-5 hover:border-card-border-hover transition-colors flex flex-col justify-between">
        <div>
          <div className="flex items-center gap-2 text-text-secondary min-w-0 mb-3">
            <Eye className="w-4 h-4 shrink-0" strokeWidth={1.5} aria-hidden="true" />
            <span className="text-xs font-semibold text-text-secondary truncate">Yakalanılan Ofsayt</span>
          </div>
          <div className="flex items-baseline gap-2 mb-2">
            <span className="text-3xl sm:text-4xl font-semibold tracking-tight font-mono tabular-nums text-text-primary">
              {prediction.offsides?.expected_total || '3.3'}
            </span>
            <span className="text-xs font-semibold text-text-secondary">beklenen ofsayt</span>
          </div>
          <SkillBadge skill={prediction.offsides?.model_skill} />
          <SplitPill
            leftLabel={homeLabel}
            leftVal={prediction.offsides?.expected_home || '1.7'}
            rightLabel={awayLabel}
            rightVal={prediction.offsides?.expected_away || '1.6'}
          />
        </div>
        <div className="space-y-2.5 pt-3 border-t border-border-light">
          <ProbRow label="3.5 Üst Olasılığı" pct={prediction.offsides?.prob_over_3_5_pct || '45.0'} />
          {prediction.outcome.over_2_5_source === 'baseline' && (
            <span className="block text-xs font-semibold text-status-warning">
              Taban oran (model sinyali zayıf)
            </span>
          )}
          {prediction.goals && (
            <div className="grid grid-cols-2 gap-x-4 gap-y-2 pt-3 border-t border-border-light text-xs">
              <div className="flex justify-between text-text-secondary">
                <span>1.5 Gol Üstü</span>
                <strong className="text-text-primary font-mono tabular-nums">%{prediction.goals['over_1.5']?.pct}</strong>
              </div>
              <div className="flex justify-between text-text-secondary">
                <span>3.5 Gol Üstü</span>
                <strong className="text-text-primary font-mono tabular-nums">%{prediction.goals['over_3.5']?.pct}</strong>
              </div>
              <div className="flex justify-between text-text-secondary">
                <span title={prediction.goals.btts_informative === false ? 'Model lig ortalamasından iyi değil; düşük ayırt edicilik' : undefined}>
                  Karşılıklı Gol{prediction.goals.btts_informative === false && ' (düşük)'}
                </span>
                <strong className="text-text-primary font-mono tabular-nums">%{prediction.goals.btts_pct}</strong>
              </div>
              <div className="flex justify-between text-text-secondary">
                <span>Gol modeli λ</span>
                <strong className="text-text-primary font-mono tabular-nums">
                  {prediction.goals.expected_home_goals} – {prediction.goals.expected_away_goals}
                </strong>
              </div>
            </div>
          )}
          <div className="flex items-center justify-between text-xs p-2.5 rounded bg-background-tertiary border border-border-light gap-2">
            <span className="text-text-secondary font-medium shrink-0">Taktiksel Çizgi</span>
            <span className="font-semibold text-text-primary truncate text-right">
              {(prediction.offsides?.expected_total || 3.3) >= 3.6 ? 'Yüksek Hat / Tuzak' : 'Derin Blok Savunma'}
            </span>
          </div>
        </div>
      </div>

      {/* Cards & discipline */}
      <div className="bg-background-primary border border-border rounded p-5 hover:border-card-border-hover transition-colors flex flex-col justify-between">
        <div>
          <div className="flex items-center gap-2 text-text-secondary min-w-0 mb-3">
            <CreditCard className="w-4 h-4 shrink-0" strokeWidth={1.5} aria-hidden="true" />
            <span className="text-xs font-semibold text-text-secondary truncate">Kartlar &amp; Disiplin</span>
          </div>
          <div className="flex items-baseline gap-2 mb-2">
            <span className="text-3xl sm:text-4xl font-semibold tracking-tight font-mono tabular-nums text-text-primary">
              {prediction.cards?.expected_total || '4.2'}
            </span>
            <span className="text-xs font-semibold text-text-secondary">beklenen kart</span>
          </div>
          <SkillBadge skill={prediction.cards?.model_skill} />
          <SplitPill
            leftLabel={homeLabel}
            leftVal={prediction.cards?.expected_home || '2.1'}
            rightLabel={awayLabel}
            rightVal={prediction.cards?.expected_away || '2.1'}
          />
        </div>
        <div className="space-y-2.5 pt-3 border-t border-border-light">
          <ProbRow label="3.5 Üst Olasılığı" pct={prediction.cards?.prob_over_3_5_pct || '62.0'} />
          {prediction.lineup_analysis?.lineup_impact?.delta_cards != null && (
            <div className="flex items-center justify-between text-xs p-2 rounded bg-background-tertiary border border-border text-status-warning">
              <span className="font-medium">11 Kart Risk Etkisi</span>
              <span className="font-mono font-semibold tabular-nums">
                {prediction.lineup_analysis.lineup_impact.delta_cards > 0
                  ? `+${prediction.lineup_analysis.lineup_impact.delta_cards}`
                  : prediction.lineup_analysis.lineup_impact.delta_cards} Kart
              </span>
            </div>
          )}
          <div className="flex items-center justify-between text-xs p-2.5 rounded bg-background-tertiary border border-border-light gap-2">
            <span className="text-text-secondary font-medium shrink-0 flex items-center gap-1">
              <Scale className="w-3.5 h-3.5 text-text-muted" strokeWidth={1.5} aria-hidden="true" />
              <span>Hakem:</span>
            </span>
            <span className="font-semibold text-text-primary truncate text-right tabular-nums">
              {prediction.referee?.name || 'Premier League Hakem Heyeti'} ({prediction.referee?.avg_cards || '4.2'} k/m)
            </span>
          </div>
        </div>
      </div>

      {/* Expected goals and shots */}
      <div className="bg-background-primary border border-border rounded p-5 hover:border-card-border-hover transition-colors flex flex-col justify-between">
        <div>
          <div className="flex items-center gap-2 text-text-secondary min-w-0 mb-3">
            <Target className="w-4 h-4 shrink-0" strokeWidth={1.5} aria-hidden="true" />
            <span className="text-xs font-semibold text-text-secondary truncate">Gol Tahmini · Şut İstatistikleri</span>
          </div>
          <div className="flex items-baseline gap-2 mb-2">
            <span className="text-3xl sm:text-4xl font-semibold tracking-tight font-mono tabular-nums text-text-primary">
              {prediction.goals?.expected_total_goals || (Number(prediction.goals?.expected_home_goals || 1.4) + Number(prediction.goals?.expected_away_goals || 1.2)).toFixed(2)}
            </span>
            <span className="text-xs font-semibold text-text-secondary">beklenen toplam gol</span>
          </div>
          <SplitPill
            leftLabel={homeLabel}
            leftVal={`${prediction.goals?.expected_home_goals || '1.4'} gol`}
            rightLabel={awayLabel}
            rightVal={`${prediction.goals?.expected_away_goals || '1.2'} gol`}
          />
        </div>
        <div className="space-y-2.5 pt-3 border-t border-border-light">
          <ProbRow label="2.5 Gol Üst Olasılığı" pct={prediction.outcome.over_2_5_goals_pct} />
          {prediction.goals?.team_totals && (
            <div className="p-2.5 rounded bg-background-tertiary border border-border-light space-y-1.5 text-xs">
              <div className="flex items-center justify-between font-medium text-text-secondary">
                <span>Dinamik Takım Baremleri</span>
                <span className="text-xs text-status-info font-semibold">Ana Çizgi</span>
              </div>
              <div className="flex justify-between items-center text-text-secondary">
                <span className="font-medium truncate">{homeLabel}:</span>
                <span className="font-mono font-semibold tabular-nums text-text-primary bg-background-primary px-2 py-0.5 rounded border border-border">
                  {prediction.goals.team_totals.home.primary_line} Üst (%{prediction.goals.team_totals.home.primary_over_pct} · {prediction.goals.team_totals.home.primary_fair_odds_over})
                </span>
              </div>
              <div className="flex justify-between items-center text-text-secondary">
                <span className="font-medium truncate">{awayLabel}:</span>
                <span className="font-mono font-semibold tabular-nums text-text-primary bg-background-primary px-2 py-0.5 rounded border border-border">
                  {prediction.goals.team_totals.away.primary_line} Üst (%{prediction.goals.team_totals.away.primary_over_pct} · {prediction.goals.team_totals.away.primary_fair_odds_over})
                </span>
              </div>
            </div>
          )}
          <div className="flex items-center justify-between text-xs p-2.5 rounded bg-background-tertiary border border-border-light gap-2">
            <span className="text-text-secondary font-medium shrink-0">Şut Beklentisi</span>
            <span className="font-mono font-semibold tabular-nums text-text-primary truncate text-right">
              {prediction.shots.expected_total} Toplam Şut (~9 isabet)
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
