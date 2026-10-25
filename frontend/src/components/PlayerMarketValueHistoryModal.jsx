import { useState, useEffect } from 'react';
import { X, TrendingUp, TrendingDown, Coins } from 'lucide-react';
import PlayerAvatar from './PlayerAvatar';
import Skeleton from './common/Skeleton';
import InlineError from './common/InlineError';
import { getPlayerMarketValueHistory } from '../services/playerService';

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

function ModalSkeleton() {
  return (
    <div className="flex flex-col gap-6" aria-busy="true" aria-label="Yükleniyor">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24 w-full" />
        ))}
      </div>
      <Skeleton className="h-56 w-full" />
      <Skeleton className="h-40 w-full" />
    </div>
  );
}

export default function PlayerMarketValueHistoryModal({
  isOpen,
  onClose,
  player,
  playerId,
  playerName,
  playerPhoto,
  teamBadge,
  teamName,
  position
}) {
  const [result, setResult] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [hoveredPoint, setHoveredPoint] = useState(null);

  const effectiveId = playerId || player?.tm_id || player?.id;
  const effectiveName = playerName || player?.name || '';
  const effectivePhoto = playerPhoto || player?.photo_url;
  const effectiveBadge = teamBadge || player?.team_badge;
  const effectiveTeamName = teamName || player?.team_name;
  const effectivePos = position || player?.position;

  const requestKey = `${effectiveId}:${reloadKey}`;

  useEffect(() => {
    if (!isOpen || !effectiveId) return undefined;

    let isMounted = true;
    getPlayerMarketValueHistory(effectiveId, { name: effectiveName || undefined })
      .then(resData => {
        if (isMounted) setResult({ key: requestKey, data: resData, error: false });
      })
      .catch(err => {
        console.error('Failed to load player market value history:', err);
        if (isMounted) setResult({ key: requestKey, data: null, error: true });
      });

    return () => {
      isMounted = false;
    };
  }, [isOpen, effectiveId, effectiveName, requestKey]);

  useEffect(() => {
    if (!isOpen) return undefined;
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const settled = result && result.key === requestKey;
  const loading = !settled;
  const error = settled && result.error;
  const data = settled ? result.data : null;

  const history = data?.history || [];
  const peakVal = data?.peak_value;
  const currentVal = data?.current_value;
  const firstVal = data?.first_value;
  const totalGrowthPct = data?.total_growth_pct;
  const totalGrowthDiff = data?.total_growth_diff;

  const values = history.map(h => h.market_value_eur || 0);
  const maxVal = values.length > 0 ? Math.max(...values) * 1.15 : 100;
  const minVal = values.length > 0 ? Math.max(0, Math.min(...values) * 0.85) : 0;
  const yRange = maxVal - minVal || 1;

  const points = history.map((item, idx) => {
    const x = history.length > 1 ? PADDING_X + (idx / (history.length - 1)) * CHART_WIDTH : SVG_WIDTH / 2;
    const y = SVG_HEIGHT - PADDING_Y - (((item.market_value_eur || 0) - minVal) / yRange) * CHART_HEIGHT;
    const isPeak = peakVal && item.date === peakVal.date && item.market_value_eur === peakVal.market_value_eur;
    const isLatest = idx === history.length - 1;
    return { ...item, x, y, isPeak, isLatest, idx };
  });

  const linePath = points.length > 1
    ? points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ')
    : '';

  const reversedHistory = [...history].reverse();
  const growthPositive = totalGrowthPct != null && totalGrowthPct >= 0;

  const tooltipX = hoveredPoint ? Math.max(10, Math.min(SVG_WIDTH - 140, hoveredPoint.x - 65)) : 0;
  const tooltipY = hoveredPoint ? Math.max(8, hoveredPoint.y - 48) : 0;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-3 sm:p-6"
      onMouseDown={e => { if (e.target === e.currentTarget) onClose(); }}
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-label="Oyuncu piyasa değeri kariyer değişim grafiği"
        className="w-full max-w-3xl max-h-screen overflow-y-auto rounded-md bg-background-primary shadow-md border border-border"
      >
        <div className="border-b border-border p-5 sm:p-6">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-4 min-w-0">
              <div className="relative shrink-0">
                <PlayerAvatar
                  player={player}
                  photoUrl={effectivePhoto}
                  name={effectiveName}
                  size="xl"
                  shape="circle"
                  fallback="shirt"
                  className="w-14 h-14 sm:w-16 sm:h-16 border border-border"
                />
                {effectiveBadge && (
                  <div className="absolute -bottom-1 -right-1 w-6 h-6 rounded-full bg-background-primary p-0.5 border border-border">
                    <img src={effectiveBadge} alt="" className="w-full h-full object-contain" onError={e => { e.target.style.display = 'none'; }} />
                  </div>
                )}
              </div>

              <div className="min-w-0">
                <span className="text-xs text-text-secondary flex items-center gap-1">
                  <Coins className="w-3.5 h-3.5 text-text-tertiary" strokeWidth={1.5} aria-hidden="true" />
                  Transfermarkt verileri · Kariyer değer gelişimi
                </span>
                <h2 className="text-xl font-semibold text-text-primary truncate mt-0.5">
                  {effectiveName}
                </h2>
                <p className="mt-1 text-xs text-text-secondary truncate">
                  {[effectiveTeamName, effectivePos].filter(Boolean).join(' · ')}
                </p>
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
          {loading && <ModalSkeleton />}

          {error && (
            <InlineError
              message="Piyasa değeri geçmişi yüklenemedi."
              onRetry={() => setReloadKey(k => k + 1)}
            />
          )}

          {!loading && !error && data && (
            <>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <KpiCard
                  label="Güncel değer"
                  value={currentVal?.formatted || '—'}
                  meta={currentVal?.date_formatted || 'Son kayıt'}
                />
                <KpiCard
                  label="Kariyer zirvesi"
                  value={peakVal?.formatted || '—'}
                  meta={peakVal ? `${peakVal.age ? `${peakVal.age} yaş · ` : ''}${peakVal.date_formatted}` : '—'}
                />
                <KpiCard
                  label="Kariyer büyümesi"
                  value={totalGrowthPct != null ? `${growthPositive ? '+' : ''}${totalGrowthPct}%` : '—'}
                  icon={totalGrowthPct == null ? null : growthPositive ? TrendingUp : TrendingDown}
                  meta={totalGrowthDiff != null ? `${totalGrowthDiff >= 0 ? '+' : ''}€${totalGrowthDiff}M` : '—'}
                />
                <KpiCard
                  label="Değerleme sayısı"
                  value={`${history.length} kayıt`}
                  meta={firstVal ? `İlk: ${firstVal.formatted} (${firstVal.year})` : 'Kayıt yok'}
                />
              </div>

              <div className="bg-background-primary rounded border border-border p-4 sm:p-5 flex flex-col gap-3">
                <div className="flex items-center justify-between gap-3 text-xs">
                  <span className="font-medium text-text-primary">Kariyer piyasa değeri gelişimi (€ milyon)</span>
                  <span className="text-text-tertiary">
                    {peakVal ? `Zirve: ${peakVal.formatted} · ` : ''}Transfermarkt
                  </span>
                </div>

                <div className="relative w-full overflow-x-auto">
                  <svg
                    viewBox={`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`}
                    className="w-full h-auto min-w-96 select-none"
                    role="img"
                    aria-label="Kariyer boyunca piyasa değeri grafiği"
                    onMouseLeave={() => setHoveredPoint(null)}
                  >
                    {[0.25, 0.5, 0.75, 1.0].map(ratio => {
                      const y = SVG_HEIGHT - PADDING_Y - ratio * CHART_HEIGHT;
                      const valAtY = minVal + ratio * (maxVal - minVal);
                      return (
                        <g key={ratio}>
                          <line
                            x1={PADDING_X}
                            y1={y}
                            x2={SVG_WIDTH - PADDING_X}
                            y2={y}
                            className="stroke-border"
                            strokeWidth="1"
                            strokeDasharray="3 3"
                          />
                          <text x={PADDING_X - 8} y={y + 3} textAnchor="end" fontSize="11" className="fill-text-tertiary">
                            €{valAtY >= 1 ? valAtY.toFixed(0) : (valAtY * 1000).toFixed(0)}M
                          </text>
                        </g>
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
                      const isHovered = hoveredPoint?.idx === p.idx;
                      const filled = p.isPeak || p.isLatest || isHovered;
                      return (
                        <g key={p.idx} className="cursor-pointer" onMouseEnter={() => setHoveredPoint(p)}>
                          {(p.isPeak || isHovered) && (
                            <circle
                              cx={p.x}
                              cy={p.y}
                              r={isHovered ? 7 : 6}
                              fill="none"
                              className="stroke-primary"
                              strokeWidth="1.5"
                              strokeOpacity="0.3"
                            />
                          )}
                          <circle
                            cx={p.x}
                            cy={p.y}
                            r={p.isPeak || isHovered ? 4.5 : p.isLatest ? 4 : 3}
                            className={`stroke-primary ${filled ? 'fill-primary' : 'fill-background-primary'}`}
                            strokeWidth="1.5"
                          />
                          {(p.idx === 0 || p.idx === points.length - 1 || (points.length > 6 && p.idx % Math.ceil(points.length / 5) === 0)) && (
                            <text x={p.x} y={SVG_HEIGHT - 12} textAnchor="middle" fontSize="11" className="fill-text-tertiary">
                              {p.year}
                            </text>
                          )}
                        </g>
                      );
                    })}

                    {hoveredPoint && (
                      <g pointerEvents="none">
                        <rect x={tooltipX} y={tooltipY} width="130" height="40" rx="4" className="fill-primary" />
                        <text x={tooltipX + 65} y={tooltipY + 16} textAnchor="middle" fontSize="12" fontWeight="600" className="fill-background-primary">
                          {hoveredPoint.formatted}
                          {hoveredPoint.change_pct != null && ` (${hoveredPoint.change_pct >= 0 ? '+' : ''}${hoveredPoint.change_pct}%)`}
                        </text>
                        <text x={tooltipX + 65} y={tooltipY + 31} textAnchor="middle" fontSize="11" className="fill-text-muted">
                          {hoveredPoint.date_formatted}{hoveredPoint.age ? ` · ${hoveredPoint.age} yaş` : ''}
                        </text>
                      </g>
                    )}
                  </svg>
                </div>
              </div>

              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between gap-3">
                  <h3 className="text-sm font-semibold text-text-primary">
                    Değerleme kayıtları <span className="font-normal text-text-secondary tabular-nums">({reversedHistory.length})</span>
                  </h3>
                  <span className="text-xs text-text-tertiary">Yeniden eskiye</span>
                </div>

                <div className="overflow-auto rounded border border-border max-h-72">
                  <table className="w-full text-left text-sm border-collapse">
                    <thead className="sticky top-0 z-10">
                      <tr className="bg-background-tertiary border-b border-border text-text-secondary">
                        <th scope="col" className="py-2 px-3 font-medium">Tarih</th>
                        <th scope="col" className="py-2 px-3 font-medium border-l border-border">Kulüp</th>
                        <th scope="col" className="py-2 px-3 font-medium text-right border-l border-border">Yaş</th>
                        <th scope="col" className="py-2 px-3 font-medium text-right border-l border-border">Piyasa değeri</th>
                        <th scope="col" className="py-2 px-3 font-medium text-right border-l border-border">Değişim</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border-light bg-background-primary">
                      {reversedHistory.map((h, idx) => {
                        const isPeak = peakVal && h.date === peakVal.date && h.market_value_eur === peakVal.market_value_eur;
                        const isLatest = idx === 0;
                        const tone = h.change_pct > 0 ? 'text-status-success' : h.change_pct < 0 ? 'text-status-error' : 'text-text-muted';

                        return (
                          <tr key={idx} className="transition-colors duration-150 ease-out hover:bg-background-tertiary">
                            <td className="py-2.5 px-3 whitespace-nowrap text-text-primary">
                              <span className="font-medium tabular-nums">{h.date_formatted}</span>
                              {isLatest && <span className="ml-2 text-xs text-text-secondary">Güncel</span>}
                              {isPeak && !isLatest && <span className="ml-2 text-xs text-text-secondary">Zirve</span>}
                            </td>
                            <td className="py-2.5 px-3 whitespace-nowrap text-text-secondary border-l border-border-light">{h.club_name || '—'}</td>
                            <td className="py-2.5 px-3 text-right text-text-secondary tabular-nums border-l border-border-light">{h.age || '—'}</td>
                            <td className="py-2.5 px-3 text-right font-medium text-text-primary tabular-nums whitespace-nowrap border-l border-border-light">{h.formatted}</td>
                            <td className={`py-2.5 px-3 text-right tabular-nums whitespace-nowrap border-l border-border-light ${h.change_pct != null ? `font-medium ${tone}` : 'text-text-muted'}`}>
                              {h.change_pct != null ? (
                                <>
                                  {h.change_pct > 0 ? '+' : ''}{h.change_pct}%
                                  {h.change_diff != null && (
                                    <span className="ml-1 text-xs font-normal text-text-tertiary">
                                      ({h.change_diff > 0 ? `+€${h.change_diff}M` : `€${h.change_diff}M`})
                                    </span>
                                  )}
                                </>
                              ) : '—'}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}
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
