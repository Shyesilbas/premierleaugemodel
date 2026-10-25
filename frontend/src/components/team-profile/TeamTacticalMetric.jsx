export const LOW_SAMPLE_MATCHES = 10;

const UNIT_BADGES = {
  '%': 'Oran',
  PPDA: 'PPDA',
  'maç başına': 'Maç başı',
  'şut başına': 'Şut başı',
  '100 dokunuş başına': '100 dokunuşta',
};

const DIFFERENCE_SUFFIXES = {
  '%': ' yüzde puan',
  PPDA: '',
  'maç başına': ' / maç',
  'şut başına': ' / şut',
  '100 dokunuş başına': ' / 100 dokunuş',
};

export default function TeamTacticalMetric({ metric, totalMatches }) {
  if (!metric) return null;
  const decimals = metric.decimals ?? 1;
  const formatNumber = value => Number(value).toLocaleString('tr-TR', { maximumFractionDigits: decimals });

  const hasValue = metric.value !== null && metric.value !== undefined;
  const valueLabel = hasValue
    ? `${Number(metric.value).toFixed(decimals)}${metric.unit === '%' ? '%' : ''}`
    : '—';
  const difference = metric.difference ?? null;
  const lowSample = hasValue && metric.matches < LOW_SAMPLE_MATCHES;
  const differenceLabel = difference === null
    ? null
    : `${difference > 0 ? '+' : ''}${formatNumber(difference)}${DIFFERENCE_SUFFIXES[metric.unit] ?? ''}`;

  return (
    <div className="min-h-56 rounded border border-border bg-background-primary p-4 transition-colors hover:border-card-border-hover">
            <div className="flex min-h-8 items-start justify-between gap-3">
              <p className="text-xs font-semibold leading-4 text-text-secondary">{metric.label}</p>
              <span className="shrink-0 text-xs font-semibold text-text-muted">
                {UNIT_BADGES[metric.unit] ?? metric.unit}
              </span>
            </div>

            <div className="mt-3 flex items-baseline gap-1.5">
              <p className="text-2xl font-semibold leading-none tracking-tight tabular-nums text-text-primary">{valueLabel}</p>
              {metric.unit === 'PPDA' && <span className="text-xs text-text-muted">düşük = yoğun pres</span>}
            </div>
            <p className="mt-2 min-h-9 text-xs leading-5 text-text-secondary">{metric.description}</p>

            <div className="mt-3 border-t border-border-light pt-2.5">
              <div className="flex items-center justify-between gap-2 text-xs">
                <span className="text-text-secondary">Diğer takımların ortalaması</span>
                <span className="font-semibold tabular-nums text-text-primary">
                  {metric.league_average === null || metric.league_average === undefined
                    ? '—'
                    : `${Number(metric.league_average).toFixed(decimals)}${metric.unit === '%' ? '%' : ''}`}
                </span>
              </div>
              <div className="mt-1 flex items-center justify-between gap-2 text-xs">
                <span className="text-text-secondary">Ortalamaya fark</span>
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
              {lowSample && (
                <p className="mt-1 text-xs leading-4 text-status-warning">
                  Örnek küçük ({metric.matches} maç); değer değişken olabilir.
                </p>
              )}
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
