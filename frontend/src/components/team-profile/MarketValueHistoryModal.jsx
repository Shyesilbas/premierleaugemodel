import { useEffect, useState } from 'react';
import { Coins, TrendingDown, TrendingUp, X } from 'lucide-react';
import { getTeam } from '../../data/teams';
import { formatSeasonLabel } from '../../utils/dateFormatters';

const SVG_WIDTH = 620;
const SVG_HEIGHT = 220;
const PADDING_X = 45;
const PADDING_Y = 40;
const CHART_WIDTH = SVG_WIDTH - PADDING_X * 2;
const CHART_HEIGHT = SVG_HEIGHT - PADDING_Y * 2;

function KpiCard({ label, value, meta, icon: Icon }) {
  return (
    <div className="bg-background-primary border border-border rounded p-3 sm:p-4 flex flex-col gap-1 min-w-0">
      <span className="text-xs text-text-secondary truncate">{label}</span>
      <span className="flex items-baseline gap-1 text-xl font-semibold text-text-primary tabular-nums">
        {value}
        {Icon && <Icon className="w-4 h-4 shrink-0 self-center text-text-secondary" strokeWidth={1.5} aria-hidden="true" />}
      </span>
      <span className="text-xs text-text-tertiary truncate tabular-nums">{meta}</span>
    </div>
  );
}

export default function MarketValueHistoryModal({ isOpen, onClose, profile, selectedSeason }) {
  const [hoveredPoint, setHoveredPoint] = useState(null);

  useEffect(() => {
    if (!isOpen) return undefined;
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !profile || !profile.market_value) return null;

  const mv = profile.market_value;
  const history = mv.history || [];
  const teamName = profile.team?.name || 'Takım';
  const teamBadge = profile.team?.badge || getTeam(profile.team?.id, teamName).badge;

  const firstSeason = history[0];
  const lastSeason = history[history.length - 1];
  const totalChangePct = firstSeason && lastSeason && firstSeason.market_value_eur > 0
    ? (((lastSeason.market_value_eur - firstSeason.market_value_eur) / firstSeason.market_value_eur) * 100).toFixed(1)
    : null;
  const totalChangeDiff = firstSeason && lastSeason
    ? (lastSeason.market_value_eur - firstSeason.market_value_eur).toFixed(1)
    : null;
  const growthPositive = totalChangePct !== null && Number(totalChangePct) >= 0;

  const values = history.map(h => h.market_value_eur || 0);
  const maxVal = values.length > 0 ? Math.max(...values) * 1.15 : 1000;
  const minVal = values.length > 0 ? Math.max(0, Math.min(...values) * 0.8) : 0;
  const yRange = maxVal - minVal || 1;

  const points = history.map((item, idx) => {
    const x = history.length > 1 ? PADDING_X + (idx / (history.length - 1)) * CHART_WIDTH : SVG_WIDTH / 2;
    const y = SVG_HEIGHT - PADDING_Y - (((item.market_value_eur || 0) - minVal) / yRange) * CHART_HEIGHT;
    return { ...item, x, y, idx, isSelected: item.season === selectedSeason };
  });

  const linePath = points.length > 1
    ? points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ')
    : '';

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-3 sm:p-6"
      onMouseDown={e => { if (e.target === e.currentTarget) onClose(); }}
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-label="Kadro piyasa değeri değişim grafiği"
        className="w-full max-w-3xl max-h-screen overflow-y-auto rounded-md bg-background-primary shadow-md border border-border"
      >
        <div className="border-b border-border p-5 sm:p-6">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-4 min-w-0">
              <div className="w-14 h-14 rounded border border-border bg-background-secondary p-2 shrink-0">
                <img src={teamBadge} alt="" className="w-full h-full object-contain" />
              </div>
              <div className="min-w-0">
                <span className="text-xs text-text-secondary flex items-center gap-1">
                  <Coins className="w-3.5 h-3.5 text-text-tertiary" strokeWidth={1.5} aria-hidden="true" />
                  Transfermarkt verileri · 5 yıllık trend
                </span>
                <h2 className="text-xl font-semibold text-text-primary truncate mt-0.5">
                  {teamName} kadro piyasa değeri
                </h2>
              </div>
            </div>

            <button
              type="button"
              onClick={onClose}
              title="Kapat"
              aria-label="Kapat"
              className="rounded border border-border bg-background-primary hover:bg-background-tertiary p-2 text-text-secondary hover:text-text-primary transition-colors duration-150 ease-out cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-border-focus"
            >
              <X className="w-4 h-4" strokeWidth={1.5} />
            </button>
          </div>
        </div>

        <div className="p-5 sm:p-6 flex flex-col gap-6">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <KpiCard
              label={`Güncel değer (${formatSeasonLabel(mv.season, '/')})`}
              value={mv.formatted}
              meta={`Oyuncu başı ort. ${mv.avg_formatted || '—'}`}
            />
            <KpiCard
              label="5 yıllık büyüme"
              value={totalChangePct !== null ? `${growthPositive ? '+' : ''}${totalChangePct}%` : '—'}
              icon={totalChangePct === null ? null : growthPositive ? TrendingUp : TrendingDown}
              meta={totalChangeDiff !== null ? `${Number(totalChangeDiff) >= 0 ? '+' : ''}€${totalChangeDiff}M` : '—'}
            />
            <KpiCard
              label="Kadro genişliği"
              value={mv.squad_size ? `${mv.squad_size} oyuncu` : '—'}
              meta="Kayıtlı kadro"
            />
            <KpiCard
              label={`İlk sezon${firstSeason?.season_label ? ` (${firstSeason.season_label})` : ''}`}
              value={firstSeason?.formatted || '—'}
              meta="Karşılaştırma başlangıcı"
            />
          </div>

          <div className="bg-background-primary rounded border border-border p-4 sm:p-5 flex flex-col gap-3">
            <div className="flex items-center justify-between gap-3 text-xs">
              <span className="font-medium text-text-primary">Sezonluk kadro değeri (€ milyon)</span>
              <span className="text-text-tertiary">Transfermarkt</span>
            </div>

            <div className="relative w-full overflow-x-auto">
              <svg
                viewBox={`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`}
                className="w-full h-auto min-w-96 select-none"
                role="img"
                aria-label="Sezonlara göre kadro piyasa değeri grafiği"
                onMouseLeave={() => setHoveredPoint(null)}
              >
                {[0.25, 0.5, 0.75, 1.0].map(ratio => {
                  const y = SVG_HEIGHT - PADDING_Y - ratio * CHART_HEIGHT;
                  return (
                    <line
                      key={ratio}
                      x1={PADDING_X}
                      y1={y}
                      x2={SVG_WIDTH - PADDING_X}
                      y2={y}
                      className="stroke-border"
                      strokeWidth="1"
                      strokeDasharray="3 3"
                    />
                  );
                })}

                {linePath && (
                  <path
                    d={linePath}
                    fill="none"
                    className="stroke-primary"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                )}

                {points.map(p => {
                  const emphasised = p.isSelected || hoveredPoint?.idx === p.idx;
                  return (
                    <g key={p.season} onMouseEnter={() => setHoveredPoint(p)} className="cursor-pointer">
                      <circle
                        cx={p.x}
                        cy={p.y}
                        r={emphasised ? 5 : 3.5}
                        className={`stroke-primary ${emphasised ? 'fill-primary' : 'fill-background-primary'}`}
                        strokeWidth="1.5"
                      />
                      <text
                        x={p.x}
                        y={p.y - 12}
                        textAnchor="middle"
                        fontSize="11"
                        fontWeight={emphasised ? '600' : '400'}
                        className={emphasised ? 'fill-text-primary' : 'fill-text-secondary'}
                      >
                        {p.formatted}
                      </text>
                      <text
                        x={p.x}
                        y={SVG_HEIGHT - 12}
                        textAnchor="middle"
                        fontSize="11"
                        fontWeight={p.isSelected ? '600' : '400'}
                        className={p.isSelected ? 'fill-text-primary' : 'fill-text-tertiary'}
                      >
                        {p.season_label}
                      </text>
                    </g>
                  );
                })}
              </svg>
            </div>
          </div>

          <div className="flex flex-col gap-2">
            <h3 className="text-sm font-semibold text-text-primary">Sezon bazlı değişim</h3>
            <div className="overflow-x-auto rounded border border-border">
              <table className="w-full text-left text-sm border-collapse">
                <thead>
                  <tr className="bg-background-tertiary border-b border-border text-text-secondary">
                    <th scope="col" className="py-2 px-3 font-medium">Sezon</th>
                    <th scope="col" className="py-2 px-3 font-medium text-right border-l border-border">Kadro değeri</th>
                    <th scope="col" className="py-2 px-3 font-medium text-right border-l border-border">Oyuncu başı ort.</th>
                    <th scope="col" className="py-2 px-3 font-medium text-right border-l border-border">Kadro</th>
                    <th scope="col" className="py-2 px-3 font-medium text-right border-l border-border">Yıllık değişim</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-light bg-background-primary">
                  {history.map((row, idx) => {
                    const prevRow = idx > 0 ? history[idx - 1] : null;
                    const diffPct = prevRow && prevRow.market_value_eur > 0
                      ? (((row.market_value_eur - prevRow.market_value_eur) / prevRow.market_value_eur) * 100).toFixed(1)
                      : null;
                    const isSelected = row.season === selectedSeason;
                    const diffTone = diffPct === null || Number(diffPct) === 0
                      ? 'text-text-muted'
                      : Number(diffPct) > 0 ? 'text-status-success' : 'text-status-error';

                    return (
                      <tr key={row.season} className={isSelected ? 'bg-background-tertiary' : ''}>
                        <td className="py-2.5 px-3 whitespace-nowrap text-text-primary">
                          <span className={isSelected ? 'font-semibold' : 'font-medium'}>{row.season_label}</span>
                          {isSelected && <span className="ml-2 text-xs text-text-secondary">Seçili sezon</span>}
                        </td>
                        <td className="py-2.5 px-3 text-right font-medium text-text-primary tabular-nums border-l border-border-light">{row.formatted}</td>
                        <td className="py-2.5 px-3 text-right text-text-secondary tabular-nums border-l border-border-light">{row.avg_formatted}</td>
                        <td className="py-2.5 px-3 text-right text-text-secondary tabular-nums border-l border-border-light">{row.squad_size}</td>
                        <td className={`py-2.5 px-3 text-right font-medium tabular-nums border-l border-border-light ${diffTone}`}>
                          {diffPct === null ? '—' : `${Number(diffPct) > 0 ? '+' : ''}${diffPct}%`}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-between border-t border-border px-5 py-4">
          <span className="text-xs text-text-tertiary flex items-center gap-1.5">
            <Coins className="w-3.5 h-3.5 text-text-muted" strokeWidth={1.5} aria-hidden="true" />
            Transfermarkt resmi piyasa değerleme arşivi
          </span>
          <button
            type="button"
            onClick={onClose}
            className="h-9 rounded border border-border bg-background-primary px-4 text-sm font-medium text-text-primary hover:bg-background-tertiary transition-colors duration-150 ease-out cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-border-focus"
          >
            Kapat
          </button>
        </div>
      </section>
    </div>
  );
}
