import React from 'react';
import { GitBranch, Scale, ShieldCheck, Target } from 'lucide-react';
import { formatSeasonLabel } from '../../utils/dateFormatters';
import { Badge } from '../common/Badge';
import { Card } from '../common/Card';
import EmptyState from '../common/EmptyState';

function fmtNum(value, decimals = 4) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—';
  return Number(value).toFixed(decimals);
}

function fmtSigned(value, decimals = 4) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—';
  const n = Number(value);
  return `${n > 0 ? '+' : ''}${n.toFixed(decimals)}`;
}

function VerdictBadge({ verdict }) {
  if (!verdict) return <span className="text-xs text-text-muted">—</span>;
  const variant = verdict.verdict === 'better'
    ? 'success'
    : verdict.verdict === 'worse'
      ? 'error'
      : 'neutral';
  const label = verdict.verdict === 'better'
    ? 'Daha iyi'
    : verdict.verdict === 'worse'
      ? 'Gerisinde'
      : 'Fark sınırda';

  return (
    <div className="flex flex-col items-end gap-1">
      <Badge variant={variant} size="sm">{label}</Badge>
      <span className="text-xs text-text-tertiary tabular-nums">
        {fmtSigned(verdict.mean_delta)} [{fmtSigned(verdict.ci_low)}, {fmtSigned(verdict.ci_high)}]
      </span>
    </div>
  );
}

const SCOPE_LABELS = {
  prospective: 'Sızıntısız canlı',
  hybrid: 'Karma (canlı + geriye dönük)',
  in_sample_backfill: 'Geriye dönük tanısal',
  upcoming_only: 'Yalnızca gelecek maçlar',
};

const GOAL_MARKET_LABELS = {
  'over_1.5': '1.5 Üst',
  'over_2.5': '2.5 Üst',
  'over_3.5': '3.5 Üst',
  btts: 'Karşılıklı Gol',
};

export default function AuditBaselinesSection({
  benchmark = {},
  overall = {},
  prospectiveScorecard = {},
  season,
}) {
  const scores = benchmark?.scores || {};
  const verdicts = benchmark?.verdicts || {};
  const groups = prospectiveScorecard?.groups || [];
  const goalGroups = prospectiveScorecard?.goal_market_groups || [];

  const comparisonRows = [
    scores.model && {
      key: 'model',
      label: 'Aktif Model',
      sub: 'Kalibre 1X2 tahminleri',
      highlight: true,
      report: scores.model,
      verdict: null,
    },
    scores.elo && {
      key: 'elo',
      label: 'Saf Elo Referansı',
      sub: `${benchmark.prior_matches_used || 0} geçmiş maç ile eğitildi`,
      report: scores.elo,
      verdict: verdicts.model_vs_elo,
    },
    scores.base_rate && {
      key: 'base_rate',
      label: 'Taban Oran (Sıklık)',
      sub: 'Ev / beraberlik / deplasman dağılımı',
      report: scores.base_rate,
      verdict: verdicts.model_vs_base_rate,
    },
    scores.market && {
      key: 'market',
      label: 'Piyasa Kapanış Oranı',
      sub: `Overround arındırılmış (${scores.market.n} maç; model log loss: ${fmtNum(scores.model_on_market?.log_loss)})`,
      report: scores.market,
      verdict: verdicts.model_vs_market,
    },
  ].filter(Boolean);

  const prospectiveMetrics = overall?.prospective_metrics || {};
  const backfillMetrics = overall?.in_sample_backfill_metrics || {};

  return (
    <div className="space-y-6">
      {/* 1. Baseline & Market Paired Bootstrap Comparison */}
      <Card padding="none" className="overflow-hidden">
        <div className="flex flex-col gap-1 border-b border-border-light p-4 sm:flex-row sm:items-center sm:justify-between sm:px-5">
          <div className="flex items-center gap-2">
            <Scale className="h-4 w-4 text-text-secondary shrink-0" strokeWidth={1.5} aria-hidden="true" />
            <div>
              <h3 className="text-base font-semibold text-text-primary">Referans ve Piyasa Karşılaştırması</h3>
              <p className="text-xs text-text-secondary">
                {formatSeasonLabel(season, '/')} · Kapsam: {SCOPE_LABELS[benchmark?.scope] || 'Tanısal'}. Negatif log loss farkı model lehinedir (%95 güven aralığı, eşli bootstrap).
              </p>
            </div>
          </div>
          {scores.model && (
            <Badge variant="neutral" size="sm" className="self-start sm:self-center">
              {scores.model.n} maç değerlendirildi
            </Badge>
          )}
        </div>

        {comparisonRows.length === 0 ? (
          <EmptyState icon={Scale}>Bu sezon için karşılaştırma verisi yok.</EmptyState>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-border bg-background-tertiary text-xs text-text-secondary">
                  <th scope="col" className="py-2.5 pl-4 pr-3 font-medium">Referans</th>
                  <th scope="col" className="py-2.5 px-3 font-medium text-right">Maç</th>
                  <th scope="col" className="py-2.5 px-3 font-medium text-right">Log Loss</th>
                  <th scope="col" className="py-2.5 px-3 font-medium text-right">Brier</th>
                  <th scope="col" className="py-2.5 px-3 font-medium text-right">RPS</th>
                  <th scope="col" className="py-2.5 px-3 font-medium text-right">1X2 %</th>
                  <th scope="col" className="py-2.5 pl-3 pr-4 font-medium text-right">Model Farkı (%95 GA)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-light">
                {comparisonRows.map((row) => (
                  <tr
                    key={row.key}
                    className={row.highlight ? 'bg-background-secondary' : 'hover:bg-background-secondary/60'}
                  >
                    <td className="py-3 pl-4 pr-3">
                      <span className={`block text-sm ${row.highlight ? 'font-semibold text-text-primary' : 'font-medium text-text-primary'}`}>
                        {row.label}
                      </span>
                      <span className="block text-xs text-text-tertiary">{row.sub}</span>
                    </td>
                    <td className="py-3 px-3 text-right tabular-nums text-text-secondary">
                      {row.report.n}
                    </td>
                    <td className={`py-3 px-3 text-right tabular-nums ${row.highlight ? 'font-semibold text-text-primary' : 'text-text-primary'}`}>
                      {fmtNum(row.report.log_loss)}
                    </td>
                    <td className="py-3 px-3 text-right tabular-nums text-text-secondary">
                      {fmtNum(row.report.brier)}
                    </td>
                    <td className="py-3 px-3 text-right tabular-nums text-text-secondary">
                      {fmtNum(row.report.rps)}
                    </td>
                    <td className="py-3 px-3 text-right tabular-nums text-text-primary">
                      %{fmtNum(row.report.accuracy_pct, 1)}
                    </td>
                    <td className="py-3 pl-3 pr-4 text-right">
                      {row.highlight ? (
                        <Badge variant="info" size="sm">Referans model</Badge>
                      ) : (
                        <VerdictBadge verdict={row.verdict} />
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* 2. Live Prospective vs Backfill Split */}
      <Card padding="none" className="overflow-hidden">
        <div className="flex items-center gap-2 border-b border-border-light p-4 sm:px-5">
          <ShieldCheck className="h-4 w-4 text-text-secondary shrink-0" strokeWidth={1.5} aria-hidden="true" />
          <div>
            <h3 className="text-base font-semibold text-text-primary">Kayıt Kaynağı Ayrımı</h3>
            <p className="text-xs text-text-secondary">
              Başlama saatinden önce dondurulan canlı kayıtlar ile geriye dönük hesaplanan maçların karşılaştırması.
            </p>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-border bg-background-tertiary text-xs text-text-secondary">
                <th scope="col" className="py-2.5 pl-4 pr-3 font-medium">Kaynak</th>
                <th scope="col" className="py-2.5 px-3 font-medium text-right">Maç</th>
                <th scope="col" className="py-2.5 px-3 font-medium text-right">1X2 %</th>
                <th scope="col" className="py-2.5 px-3 font-medium text-right">2.5 Üst %</th>
                <th scope="col" className="py-2.5 px-3 font-medium text-right">KG %</th>
                <th scope="col" className="py-2.5 px-3 font-medium text-right">Log Loss</th>
                <th scope="col" className="py-2.5 pl-3 pr-4 font-medium text-right">RPS</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-light">
              {[
                { key: 'live', label: 'Canlı Kayıt (Prospective)', badge: 'success', data: prospectiveMetrics },
                { key: 'backfill', label: 'Sonradan Hesaplanan (Backfill)', badge: 'neutral', data: backfillMetrics },
              ].map((item) => (
                <tr key={item.key}>
                  <td className="py-3 pl-4 pr-3">
                    <div className="flex items-center gap-2">
                      <Badge variant={item.badge} size="sm">{item.key === 'live' ? 'Canlı' : 'Backfill'}</Badge>
                      <span className="font-medium text-text-primary">{item.label}</span>
                    </div>
                  </td>
                  <td className="py-3 px-3 text-right tabular-nums text-text-primary">
                    {item.data.matches_count || 0}
                  </td>
                  <td className="py-3 px-3 text-right tabular-nums text-text-primary">
                    {item.data.matches_count ? `%${fmtNum(item.data.hit_rate_1x2_pct, 1)}` : '—'}
                  </td>
                  <td className="py-3 px-3 text-right tabular-nums text-text-secondary">
                    {item.data.matches_count ? `%${fmtNum(item.data.hit_rate_over_25_pct, 1)}` : '—'}
                  </td>
                  <td className="py-3 px-3 text-right tabular-nums text-text-secondary">
                    {item.data.matches_count ? `%${fmtNum(item.data.hit_rate_btts_pct, 1)}` : '—'}
                  </td>
                  <td className="py-3 px-3 text-right tabular-nums text-text-primary">
                    {fmtNum(item.data.log_loss)}
                  </td>
                  <td className="py-3 pl-3 pr-4 text-right tabular-nums text-text-secondary">
                    {fmtNum(item.data.rps)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* 3. Artifact Versions Breakdown */}
      <Card padding="none" className="overflow-hidden">
        <div className="flex flex-col gap-2 border-b border-border-light p-4 sm:flex-row sm:items-center sm:justify-between sm:px-5">
          <div className="flex items-center gap-2">
            <GitBranch className="h-4 w-4 text-text-secondary shrink-0" strokeWidth={1.5} aria-hidden="true" />
            <div>
              <h3 className="text-base font-semibold text-text-primary">Artifact Sürümleri (Prospektif Defter)</h3>
              <p className="text-xs text-text-secondary tabular-nums">
                Günlük toplamı: {prospectiveScorecard?.distinct_logged_matches || 0} tekil maç ({prospectiveScorecard?.total_logged_entries || 0} kayıt)
              </p>
            </div>
          </div>
          {prospectiveScorecard?.active_outcome_sha256 && (
            <div className="flex items-center gap-1.5 text-xs text-text-secondary">
              <span>Aktif üretim SHA:</span>
              <code className="rounded-sm border border-border bg-background-tertiary px-1.5 py-0.5 font-mono text-text-primary">
                {prospectiveScorecard.active_outcome_sha256}
              </code>
            </div>
          )}
        </div>

        {groups.length === 0 ? (
          <EmptyState icon={GitBranch}>Prospektif skor kartı henüz oluşturulmadı.</EmptyState>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-border bg-background-tertiary text-xs text-text-secondary">
                  <th scope="col" className="py-2.5 pl-4 pr-3 font-medium">Artifact SHA</th>
                  <th scope="col" className="py-2.5 px-3 font-medium text-right">Maç</th>
                  <th scope="col" className="py-2.5 px-3 font-medium text-right">Doğruluk %</th>
                  <th scope="col" className="py-2.5 px-3 font-medium text-right">Log Loss</th>
                  <th scope="col" className="py-2.5 px-3 font-medium text-right">Brier</th>
                  <th scope="col" className="py-2.5 px-3 font-medium text-right">RPS</th>
                  <th scope="col" className="py-2.5 pl-3 pr-4 font-medium text-right">Beraberlik (Tahmin / Gerçek)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-light">
                {groups.map((g) => (
                  <tr key={g.artifact_sha256}>
                    <td className="py-2.5 pl-4 pr-3">
                      <div className="flex items-center gap-2">
                        <code className="font-mono text-xs text-text-primary">{g.short_sha}</code>
                        {g.is_active && <Badge variant="info" size="sm">Güncel</Badge>}
                      </div>
                    </td>
                    <td className="py-2.5 px-3 text-right tabular-nums text-text-secondary">{g.matches}</td>
                    <td className="py-2.5 px-3 text-right tabular-nums text-text-primary">%{fmtNum(g.accuracy_pct, 1)}</td>
                    <td className="py-2.5 px-3 text-right tabular-nums text-text-primary">{fmtNum(g.log_loss)}</td>
                    <td className="py-2.5 px-3 text-right tabular-nums text-text-secondary">{fmtNum(g.multiclass_brier)}</td>
                    <td className="py-2.5 px-3 text-right tabular-nums text-text-secondary">{fmtNum(g.rps)}</td>
                    <td className="py-2.5 pl-3 pr-4 text-right tabular-nums text-text-secondary">
                      %{fmtNum((g.mean_draw_probability || 0) * 100, 1)} / %{fmtNum((g.actual_draw_rate || 0) * 100, 1)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* 4. Goal Market Prospective Breakdown */}
      {goalGroups.length > 0 && (
        <Card padding="none" className="overflow-hidden">
          <div className="flex flex-col gap-2 border-b border-border-light p-4 sm:flex-row sm:items-center sm:justify-between sm:px-5">
            <div className="flex items-center gap-2">
              <Target className="h-4 w-4 text-text-secondary shrink-0" strokeWidth={1.5} aria-hidden="true" />
              <div>
                <h3 className="text-base font-semibold text-text-primary">Gol Pazarları Skorkartı</h3>
                <p className="text-xs text-text-secondary">
                  Son gol artifact sürümlerinde Over/Under ve Karşılıklı Gol log loss karşılaştırması.
                </p>
              </div>
            </div>
            {prospectiveScorecard?.active_goals_sha256 && (
              <code className="self-start rounded-sm border border-border bg-background-tertiary px-1.5 py-0.5 font-mono text-xs text-text-primary sm:self-center">
                Goals SHA: {prospectiveScorecard.active_goals_sha256}
              </code>
            )}
          </div>

          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-border bg-background-tertiary text-xs text-text-secondary">
                  <th scope="col" className="py-2.5 pl-4 pr-3 font-medium">Artifact</th>
                  <th scope="col" className="py-2.5 px-3 font-medium">Pazar</th>
                  <th scope="col" className="py-2.5 px-3 font-medium text-right">Maç</th>
                  <th scope="col" className="py-2.5 px-3 font-medium text-right">Model Log Loss</th>
                  <th scope="col" className="py-2.5 px-3 font-medium text-right">Taban Log Loss</th>
                  <th scope="col" className="py-2.5 pl-3 pr-4 font-medium text-right">Fark vs Taban</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-light">
                {goalGroups.slice(0, 2).flatMap((grp) =>
                  Object.entries(grp.markets || {}).map(([marketKey, stats]) => {
                    const delta = stats?.log_loss_delta_vs_baseline;
                    const better = delta != null && delta < 0;
                    return (
                      <tr key={`${grp.short_sha}-${marketKey}`}>
                        <td className="py-2 pl-4 pr-3">
                          <code className="font-mono text-xs text-text-secondary">{grp.short_sha}</code>
                        </td>
                        <td className="py-2 px-3 font-medium text-text-primary">
                          {GOAL_MARKET_LABELS[marketKey] || marketKey}
                        </td>
                        <td className="py-2 px-3 text-right tabular-nums text-text-secondary">
                          {stats.matches ?? 0}
                        </td>
                        <td className="py-2 px-3 text-right tabular-nums text-text-primary">
                          {fmtNum(stats.comparable_model_log_loss ?? stats.log_loss)}
                        </td>
                        <td className="py-2 px-3 text-right tabular-nums text-text-secondary">
                          {fmtNum(stats.baseline_log_loss)}
                        </td>
                        <td className={`py-2 pl-3 pr-4 text-right tabular-nums font-medium ${better ? 'text-status-success' : 'text-status-warning'}`}>
                          {fmtSigned(delta)}
                        </td>
                      </tr>
                    );
                  }),
                )}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
