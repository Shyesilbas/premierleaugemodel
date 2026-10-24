export default function TeamTacticalMetric({ metric, totalMatches }) {
  if (!metric) return null;
  const formatNumber = value => Number(value).toLocaleString('tr-TR', { maximumFractionDigits: 1 });

  const hasValue = metric.value !== null && metric.value !== undefined;
  const valueLabel = hasValue
    ? `${Number(metric.value).toFixed(1)}${metric.unit === '%' ? '%' : ''}`
    : '—';
  const difference = hasValue && metric.league_average !== null && metric.league_average !== undefined
    ? Number(metric.value) - Number(metric.league_average)
    : null;
  const differenceLabel = difference === null
    ? null
    : `${difference > 0 ? '+' : ''}${formatNumber(difference)}${metric.unit === '%' ? ' yüzde puan' : metric.unit === 'PPDA' ? '' : ' / maç'}`;

  return (
    <div className="min-h-[218px] rounded border border-border bg-background-primary p-4 transition-colors hover:border-card-border-hover">
            <div className="flex min-h-8 items-start justify-between gap-3">
              <p className="text-xs font-semibold leading-4 text-text-secondary">{metric.label}</p>
              <span className="shrink-0 text-xs font-semibold uppercase tracking-wide text-text-muted">
                {metric.unit === '%' ? 'Oran' : metric.unit === 'PPDA' ? 'PPDA' : 'Maç başı'}
              </span>
            </div>

            <div className="mt-3 flex items-baseline gap-1.5">
              <p className="text-2xl font-semibold leading-none tracking-tight tabular-nums text-text-primary">{valueLabel}</p>
              {metric.unit === 'PPDA' && <span className="text-xs text-text-muted">düşük = yoğun pres</span>}
            </div>
            <p className="mt-2 min-h-9 text-xs leading-[1.15rem] text-text-secondary">{metric.description}</p>

            <div className="mt-3 border-t border-border-light pt-2.5">
              <div className="flex items-center justify-between gap-2 text-xs">
                <span className="text-text-secondary">Lig ortalaması</span>
                <span className="font-semibold tabular-nums text-text-primary">
                  {metric.league_average === null || metric.league_average === undefined
                    ? '—'
                    : `${Number(metric.league_average).toFixed(1)}${metric.unit === '%' ? '%' : ''}`}
                </span>
              </div>
              <div className="mt-1 flex items-center justify-between gap-2 text-xs">
                <span className="text-text-secondary">Lig ortalamasına fark</span>
                <span className="font-semibold tabular-nums text-text-primary">{differenceLabel || '—'}</span>
              </div>
              {metric.percentile !== null && metric.percentile !== undefined && (
                <div className="mt-2.5">
                  <div className="mb-1 flex items-center justify-between text-xs text-text-secondary">
                    <span>Lig dağılımı</span>
                    <span className="font-semibold tabular-nums text-text-primary">P{metric.percentile}</span>
                  </div>
                  <div className="h-1 rounded-full bg-border" title={`Lig dağılımında P${metric.percentile}`}>
                    <div className="h-full rounded-full bg-text-secondary" style={{ width: `${metric.percentile}%` }} />
                  </div>
                </div>
              )}
              <p className="mt-2 text-xs text-text-muted">
                {metric.matches}/{totalMatches || 0} maç · %{formatNumber(metric.coverage_pct || 0)} veri kapsamı
              </p>
              {metric.unit === 'PPDA' && (
                <p className="mt-1 text-xs leading-4 text-text-secondary">
                  Lig kapsaması %{formatNumber(metric.league_coverage_pct || 0)}
                  {metric.value == null && ' · Karşılaştırma için en az %80 kapsam gerekir.'}
                </p>
              )}
            </div>
          </div>
  );
}
