import React, { useState } from 'react';
import { LineChart, ScatterChart } from 'lucide-react';
import { Card } from '../common/Card';
import EmptyState from '../common/EmptyState';

export default function AuditChartsSection({ rollingAccuracy = [], calibrationBands = [] }) {
  const [hoverIdx, setHoverIdx] = useState(null);

  const chartW = 480;
  const chartH = 180;
  const padX = 36;
  const padY = 20;
  const innerW = chartW - padX * 2;
  const innerH = chartH - padY * 2;

  const hasRolling = rollingAccuracy.length >= 2;
  const activePoint = hasRolling
    ? (hoverIdx != null && rollingAccuracy[hoverIdx] ? rollingAccuracy[hoverIdx] : rollingAccuracy[rollingAccuracy.length - 1])
    : null;

  const toX = (i, len) => (len <= 1 ? padX + innerW / 2 : padX + (i / (len - 1)) * innerW);
  const toY = (pct) => padY + innerH - (Math.max(0, Math.min(100, pct)) / 100) * innerH;

  const modelPolyline = hasRolling
    ? rollingAccuracy.map((p, i) => `${toX(i, rollingAccuracy.length).toFixed(1)},${toY(p.rolling_acc).toFixed(1)}`).join(' ')
    : '';
  const homePolyline = hasRolling
    ? rollingAccuracy.map((p, i) => `${toX(i, rollingAccuracy.length).toFixed(1)},${toY(p.home_baseline_acc).toFixed(1)}`).join(' ')
    : '';

  const maxBandCount = Math.max(1, ...calibrationBands.map((b) => b.count || 0));

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      {/* Left: Rolling 1X2 Accuracy vs Home Baseline */}
      <Card padding="md" className="space-y-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            <LineChart className="h-4 w-4 text-text-secondary shrink-0" strokeWidth={1.5} aria-hidden="true" />
            <div>
              <h3 className="text-base font-semibold text-text-primary">Kayan 1X2 Doğruluk</h3>
              <p className="text-xs text-text-secondary">
                Son 20 maç kayan ortalama vs ev sahibi kazanma tabanı
              </p>
            </div>
          </div>
          {activePoint && (
            <div className="text-right text-xs tabular-nums">
              <span className="block font-semibold text-text-primary">
                {activePoint.label} · Model %{activePoint.rolling_acc}
              </span>
              <span className="block text-text-tertiary">
                Taban %{activePoint.home_baseline_acc}
              </span>
            </div>
          )}
        </div>

        {!hasRolling ? (
          <EmptyState icon={LineChart}>Kayan grafik için en az 6 tamamlanmış maç gereklidir.</EmptyState>
        ) : (
          <>
            <div className="rounded border border-border-light bg-background-secondary p-2">
              <svg
                viewBox={`0 0 ${chartW} ${chartH}`}
                className="h-44 w-full overflow-visible"
                role="img"
                aria-label="Kayan 1X2 doğruluk grafiği"
              >
                {[25, 50, 75].map((tick) => {
                  const y = toY(tick);
                  return (
                    <g key={tick}>
                      <line x1={padX} x2={chartW - padX} y1={y} y2={y} className="stroke-border" strokeWidth="1" />
                      <text x={padX - 6} y={y + 3} textAnchor="end" className="fill-text-muted text-xs tabular-nums">
                        {tick}%
                      </text>
                    </g>
                  );
                })}
                <polyline
                  fill="none"
                  className="stroke-text-muted"
                  strokeWidth="1.5"
                  strokeDasharray="4 4"
                  points={homePolyline}
                />
                <polyline
                  fill="none"
                  className="stroke-primary"
                  strokeWidth="2"
                  strokeLinejoin="round"
                  strokeLinecap="round"
                  points={modelPolyline}
                />
                {rollingAccuracy.map((p, idx) => {
                  const cx = toX(idx, rollingAccuracy.length);
                  const cy = toY(p.rolling_acc);
                  const isActive = idx === (hoverIdx ?? rollingAccuracy.length - 1);
                  return (
                    <g key={p.index}>
                      {isActive && (
                        <circle
                          cx={cx}
                          cy={cy}
                          r={4}
                          className="fill-primary stroke-background-primary"
                          strokeWidth="1.5"
                        />
                      )}
                      <circle
                        cx={cx}
                        cy={cy}
                        r={10}
                        fill="transparent"
                        className="cursor-pointer"
                        onMouseEnter={() => setHoverIdx(idx)}
                      />
                    </g>
                  );
                })}
              </svg>
            </div>
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-text-secondary tabular-nums">
              <span>İlk 5 maç sonrası başlayan kayan pencere (n={rollingAccuracy[rollingAccuracy.length - 1]?.index})</span>
              <span>Genel kümülatif: %{rollingAccuracy[rollingAccuracy.length - 1]?.cumulative_acc}</span>
            </div>
          </>
        )}
      </Card>

      {/* Right: Confidence Calibration Scatter + Bands Table */}
      <Card padding="md" className="space-y-3">
        <div className="flex items-center gap-2">
          <ScatterChart className="h-4 w-4 text-text-secondary shrink-0" strokeWidth={1.5} aria-hidden="true" />
          <div>
            <h3 className="text-base font-semibold text-text-primary">Canlı Güven Kalibrasyonu</h3>
            <p className="text-xs text-text-secondary">
              Tahmin güven bandına göre gerçekleşen isabet yüzdesi (kesikli çizgi ideal y = x)
            </p>
          </div>
        </div>

        {calibrationBands.length === 0 ? (
          <EmptyState icon={ScatterChart}>Kalibrasyon bantları için tamamlanmış maç yok.</EmptyState>
        ) : (
          <>
            <div className="rounded border border-border-light bg-background-secondary p-2">
              <svg
                viewBox={`0 0 ${chartW} ${chartH}`}
                className="h-44 w-full overflow-visible"
                role="img"
                aria-label="Güven bandı kalibrasyon grafiği"
              >
                {[30, 50, 70, 90].map((tick) => {
                  const y = toY(tick);
                  const x = padX + (tick / 100) * innerW;
                  return (
                    <g key={tick}>
                      <line x1={padX} x2={chartW - padX} y1={y} y2={y} className="stroke-border" strokeWidth="1" />
                      <text x={padX - 6} y={y + 3} textAnchor="end" className="fill-text-muted text-xs">
                        {tick}%
                      </text>
                      <text x={x} y={chartH - 3} textAnchor="middle" className="fill-text-muted text-xs">
                        {tick}%
                      </text>
                    </g>
                  );
                })}
                <line
                  x1={padX + 0.25 * innerW}
                  y1={toY(25)}
                  x2={padX + 0.95 * innerW}
                  y2={toY(95)}
                  className="stroke-text-muted"
                  strokeWidth="1"
                  strokeDasharray="4 4"
                />
                <polyline
                  fill="none"
                  className="stroke-primary"
                  strokeWidth="1.75"
                  points={calibrationBands
                    .map((b) => `${(padX + (b.avg_confidence / 100) * innerW).toFixed(1)},${toY(b.actual_accuracy).toFixed(1)}`)
                    .join(' ')}
                />
                {calibrationBands.map((b) => {
                  const cx = padX + (b.avg_confidence / 100) * innerW;
                  const cy = toY(b.actual_accuracy);
                  const r = 4 + ((b.count || 0) / maxBandCount) * 4;
                  const gap = Math.abs(b.actual_accuracy - b.avg_confidence);
                  return (
                    <g key={b.label}>
                      <circle
                        cx={cx}
                        cy={cy}
                        r={r}
                        className={`${gap <= 6 ? 'fill-status-success' : 'fill-primary'} stroke-background-primary`}
                        strokeWidth="1.5"
                      />
                    </g>
                  );
                })}
              </svg>
            </div>

            <div className="overflow-x-auto rounded border border-border-light">
              <table className="w-full border-collapse text-left text-xs">
                <thead>
                  <tr className="border-b border-border bg-background-tertiary text-text-secondary">
                    <th scope="col" className="py-1.5 pl-3 pr-2 font-medium">Güven Bandı</th>
                    <th scope="col" className="py-1.5 px-2 font-medium text-right">Maç</th>
                    <th scope="col" className="py-1.5 px-2 font-medium text-right">Ort. Güven</th>
                    <th scope="col" className="py-1.5 pl-2 pr-3 font-medium text-right">Gerçek İsabet</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-light">
                  {calibrationBands.map((b) => {
                    const diff = b.actual_accuracy - b.avg_confidence;
                    return (
                      <tr key={b.label}>
                        <td className="py-1.5 pl-3 pr-2 font-medium text-text-primary">{b.label}</td>
                        <td className="py-1.5 px-2 text-right tabular-nums text-text-secondary">{b.count}</td>
                        <td className="py-1.5 px-2 text-right tabular-nums text-text-secondary">%{b.avg_confidence.toFixed(1)}</td>
                        <td className={`py-1.5 pl-2 pr-3 text-right tabular-nums font-medium ${Math.abs(diff) <= 5 ? 'text-status-success' : 'text-text-primary'}`}>
                          %{b.actual_accuracy.toFixed(1)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </>
        )}
      </Card>
    </div>
  );
}
