export default function TeamTacticalMetric({ metric, totalMatches }) {
  if (!metric) return null;
  const formatNumber = value => Number(value).toLocaleString('tr-TR', { maximumFractionDigits: 1 });

  return (
    <div key={key} className="min-h-[218px] rounded-lg border border-slate-200 bg-white p-4 transition-colors hover:border-slate-400 hover:bg-slate-50/40">
            <div className="flex min-h-8 items-start justify-between gap-3">
              <p className="text-[11px] font-semibold leading-4 text-slate-600">{metric.label}</p>
              <span className="shrink-0 text-[9px] font-semibold uppercase tracking-wide text-slate-400">
                {metric.unit === '%' ? 'Oran' : metric.unit === 'PPDA' ? 'PPDA' : 'Maç başı'}
              </span>
            </div>

            <div className="mt-3 flex items-baseline gap-1.5">
              <p className="text-[32px] font-semibold leading-none tracking-tight tabular-nums text-slate-950">{valueLabel}</p>
              {metric.unit === 'PPDA' && <span className="text-[10px] text-slate-400">düşük = yoğun pres</span>}
            </div>
            <p className="mt-2 min-h-9 text-[10px] leading-[1.15rem] text-slate-500">{metric.description}</p>

            <div className="mt-3 border-t border-slate-100 pt-2.5">
              <div className="flex items-center justify-between gap-2 text-[10px]">
                <span className="text-slate-500">Lig ortalaması</span>
                <span className="font-semibold tabular-nums text-slate-700">
                  {metric.league_average === null || metric.league_average === undefined
                    ? '—'
                    : `${Number(metric.league_average).toFixed(1)}${metric.unit === '%' ? '%' : ''}`}
                </span>
              </div>
              <div className="mt-1 flex items-center justify-between gap-2 text-[10px]">
                <span className="text-slate-500">Lig ortalamasına fark</span>
                <span className="font-semibold tabular-nums text-slate-700">{differenceLabel || '—'}</span>
              </div>
              {metric.percentile !== null && metric.percentile !== undefined && (
                <div className="mt-2.5">
                  <div className="mb-1 flex items-center justify-between text-[9px] text-slate-500">
                    <span>Lig dağılımı</span>
                    <span className="font-semibold tabular-nums text-slate-700">P{metric.percentile}</span>
                  </div>
                  <div className="h-1 rounded-full bg-slate-200" title={`Lig dağılımında P${metric.percentile}`}>
                    <div className="h-full rounded-full bg-slate-700" style={{ width: `${metric.percentile}%` }} />
                  </div>
                </div>
              )}
              <p className="mt-2 text-[9px] text-slate-400">
                {metric.matches}/{totalMatches || 0} maç · %{formatNumber(metric.coverage_pct || 0)} veri kapsamı
              </p>
              {metric.unit === 'PPDA' && (
                <p className="mt-1 text-[9px] leading-4 text-slate-500">
                  Lig kapsaması %{formatNumber(metric.league_coverage_pct || 0)}
                  {metric.value == null && ' · Karşılaştırma için en az %80 kapsam gerekir.'}
                </p>
              )}
            </div>
          </div>
  );
}
