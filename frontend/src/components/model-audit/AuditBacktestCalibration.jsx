import React from 'react';
import { History, Layers } from 'lucide-react';
import { formatSeasonLabel } from '../../utils/dateFormatters';
import { Badge } from '../common/Badge';
import { Card } from '../common/Card';
import EmptyState from '../common/EmptyState';

function fmt(value, decimals = 4) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—';
  return Number(value).toFixed(decimals);
}

export default function AuditBacktestCalibration({ backtestCalibration = {} }) {
  const o25Rel = backtestCalibration?.o25_reliability;
  const goalSeasons = backtestCalibration?.goal_outer_seasons || [];
  const x12Holdouts = backtestCalibration?.x12_season_holdouts || [];

  const hasAny = Boolean(o25Rel?.bins?.length || goalSeasons.length || x12Holdouts.length);
  if (!hasAny) {
    return null;
  }

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      {/* Walk-Forward Outer O2.5 Reliability Bins */}
      <Card padding="none" className="overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border-light p-4 sm:px-5">
          <div className="flex items-center gap-2">
            <Layers className="h-4 w-4 text-text-secondary shrink-0" strokeWidth={1.5} aria-hidden="true" />
            <div>
              <h3 className="text-base font-semibold text-text-primary">Geçmiş Sezon Kalibrasyonu (2.5 Üst)</h3>
              <p className="text-xs text-text-secondary tabular-nums">
                2023-26 havuzlanmış walk-forward dilimleri ({o25Rel?.n || 0} maç)
              </p>
            </div>
          </div>
          {o25Rel && (
            <div className="flex items-center gap-2 text-xs tabular-nums">
              <Badge variant="neutral" size="sm">ECE {fmt(o25Rel.ece)}</Badge>
              <Badge variant="neutral" size="sm">
                Monoton %{((o25Rel.monotonic_adjacent_share || 0) * 100).toFixed(0)}
              </Badge>
            </div>
          )}
        </div>

        {!o25Rel?.bins?.length ? (
          <EmptyState icon={Layers}>Dış sezon kalibrasyon dilimleri bulunamadı.</EmptyState>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left text-xs">
              <thead>
                <tr className="border-b border-border bg-background-tertiary text-text-secondary">
                  <th scope="col" className="py-2 pl-4 pr-2 font-medium">Dilim</th>
                  <th scope="col" className="py-2 px-2 font-medium text-right">Maç</th>
                  <th scope="col" className="py-2 px-2 font-medium text-right">Model Tahmini</th>
                  <th scope="col" className="py-2 px-2 font-medium text-right">Gerçekleşen</th>
                  <th scope="col" className="py-2 pl-2 pr-4 font-medium text-right">Sapma</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-light">
                {o25Rel.bins.map((b) => {
                  const predPct = b.mean_predicted * 100;
                  const obsPct = b.observed_rate * 100;
                  const gap = obsPct - predPct;
                  const within = Math.abs(gap) <= 5.0;
                  return (
                    <tr key={b.bin}>
                      <td className="py-2 pl-4 pr-2 font-medium text-text-primary tabular-nums">
                        Dilim {b.bin}
                      </td>
                      <td className="py-2 px-2 text-right tabular-nums text-text-secondary">{b.n}</td>
                      <td className="py-2 px-2 text-right tabular-nums text-text-secondary">%{predPct.toFixed(1)}</td>
                      <td className="py-2 px-2 text-right tabular-nums font-medium text-text-primary">%{obsPct.toFixed(1)}</td>
                      <td className={`py-2 pl-2 pr-4 text-right tabular-nums ${within ? 'text-status-success' : 'text-text-secondary'}`}>
                        {gap > 0 ? '+' : ''}
                        {gap.toFixed(1)} yp
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Walk-Forward Outer Seasons Log Loss Holdouts */}
      <Card padding="none" className="overflow-hidden">
        <div className="flex items-center gap-2 border-b border-border-light p-4 sm:px-5">
          <History className="h-4 w-4 text-text-secondary shrink-0" strokeWidth={1.5} aria-hidden="true" />
          <div>
            <h3 className="text-base font-semibold text-text-primary">Walk-Forward Dış Test Sezonları</h3>
            <p className="text-xs text-text-secondary">
              Her sezon, yalnızca kendisinden önceki sezonlarda eğitilen modellerle sızmasız değerlendirilir.
            </p>
          </div>
        </div>

        <div className="divide-y divide-border-light">
          {x12Holdouts.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-left text-xs">
                <thead>
                  <tr className="border-b border-border bg-background-tertiary text-text-secondary">
                    <th scope="col" className="py-2 pl-4 pr-2 font-medium">1X2 Sezon</th>
                    <th scope="col" className="py-2 px-2 font-medium">Model</th>
                    <th scope="col" className="py-2 px-2 font-medium text-right">Eğitim / Test</th>
                    <th scope="col" className="py-2 px-2 font-medium text-right">CV Loss</th>
                    <th scope="col" className="py-2 pl-2 pr-4 font-medium text-right">Test Log Loss</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-light">
                  {x12Holdouts.map((row) => (
                    <tr key={row.season}>
                      <td className="py-2 pl-4 pr-2 font-medium text-text-primary">
                        {formatSeasonLabel(row.season, '/')}
                      </td>
                      <td className="py-2 px-2 font-mono text-text-secondary">{row.selected_model}</td>
                      <td className="py-2 px-2 text-right tabular-nums text-text-secondary">
                        {row.train_samples} / {row.test_samples}
                      </td>
                      <td className="py-2 px-2 text-right tabular-nums text-text-secondary">
                        {fmt(row.cv_log_loss)}
                      </td>
                      <td className="py-2 pl-2 pr-4 text-right tabular-nums font-semibold text-text-primary">
                        {fmt(row.standard_log_loss)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {goalSeasons.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-left text-xs">
                <thead>
                  <tr className="border-b border-border bg-background-tertiary text-text-secondary">
                    <th scope="col" className="py-2 pl-4 pr-2 font-medium">2.5 Üst Sezon</th>
                    <th scope="col" className="py-2 px-2 font-medium text-right">Öncül Taban</th>
                    <th scope="col" className="py-2 px-2 font-medium text-right">Blend DC+Feat</th>
                    <th scope="col" className="py-2 pl-2 pr-4 font-medium text-right">Fark (%95 GA)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-light">
                  {goalSeasons.map((row) => {
                    const better = row.delta_vs_prior != null && row.delta_vs_prior < 0;
                    return (
                      <tr key={row.season}>
                        <td className="py-2 pl-4 pr-2 font-medium text-text-primary">
                          {formatSeasonLabel(row.season, '/')} ({row.n})
                        </td>
                        <td className="py-2 px-2 text-right tabular-nums text-text-secondary">
                          {fmt(row.prior_log_loss)}
                        </td>
                        <td className="py-2 px-2 text-right tabular-nums font-semibold text-text-primary">
                          {fmt(row.blend_log_loss)}
                        </td>
                        <td className={`py-2 pl-2 pr-4 text-right tabular-nums ${better ? 'text-status-success font-medium' : 'text-text-secondary'}`}>
                          {row.delta_vs_prior > 0 ? '+' : ''}
                          {fmt(row.delta_vs_prior)} [{fmt(row.ci_low)}, {fmt(row.ci_high)}]
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
