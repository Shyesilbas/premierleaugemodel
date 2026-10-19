import React, { useState, useEffect } from 'react';
import { X, TrendingUp, TrendingDown, Coins, Calendar, Award, Loader2 } from 'lucide-react';
import PlayerAvatar from './PlayerAvatar';
import { getPlayerMarketValueHistory } from '../services/playerService';

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
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [hoveredPoint, setHoveredPoint] = useState(null);

  const effectiveId = playerId || player?.tm_id || player?.id;
  const effectiveName = playerName || player?.name || '';
  const effectivePhoto = playerPhoto || player?.photo_url;
  const effectiveBadge = teamBadge || player?.team_badge;
  const effectiveTeamName = teamName || player?.team_name;
  const effectivePos = position || player?.position;

  useEffect(() => {
    if (!isOpen || !effectiveId) {
      setData(null);
      setError(null);
      setHoveredPoint(null);
      return;
    }

    let isMounted = true;
    setLoading(true);
    setError(null);

    getPlayerMarketValueHistory(effectiveId, { name: effectiveName || undefined })
      .then(resData => {
        if (isMounted) {
          setData(resData);
          setLoading(false);
        }
      })
      .catch(err => {
        if (isMounted) {
          console.error('Failed to load player market value history:', err);
          setError('Piyasa değeri geçmişi yüklenemedi.');
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [isOpen, effectiveId, effectiveName]);

  // Handle ESC key press
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const history = data?.history || [];
  const peakVal = data?.peak_value;
  const currentVal = data?.current_value;
  const firstVal = data?.first_value;
  const totalGrowthPct = data?.total_growth_pct;
  const totalGrowthDiff = data?.total_growth_diff;

  // Chart coordinate calculation
  const maxVal = history.length > 0
    ? Math.max(...history.map(h => h.market_value_eur || 0)) * 1.15
    : 100;
  const minVal = history.length > 0
    ? Math.max(0, Math.min(...history.map(h => h.market_value_eur || 0)) * 0.85)
    : 0;

  const svgWidth = 620;
  const svgHeight = 220;
  const paddingX = 45;
  const paddingY = 40;
  const chartWidth = svgWidth - paddingX * 2;
  const chartHeight = svgHeight - paddingY * 2;

  const points = history.map((item, idx) => {
    const x = history.length > 1 ? paddingX + (idx / (history.length - 1)) * chartWidth : svgWidth / 2;
    const yRange = maxVal - minVal || 1;
    const y = svgHeight - paddingY - (((item.market_value_eur || 0) - minVal) / yRange) * chartHeight;
    const isPeak = peakVal && item.date === peakVal.date && item.market_value_eur === peakVal.market_value_eur;
    const isLatest = idx === history.length - 1;
    return { ...item, x, y, isPeak, isLatest, idx };
  });

  const linePath = points.length > 1
    ? points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ')
    : '';

  const areaPath = points.length > 1
    ? `${linePath} L ${points[points.length - 1].x.toFixed(1)} ${svgHeight - paddingY} L ${points[0].x.toFixed(1)} ${svgHeight - paddingY} Z`
    : '';

  // Reverse chronological list for table view
  const reversedHistory = [...history].reverse();

  return (
    <div
      className="fixed inset-0 z-[120] flex items-center justify-center bg-black/40 p-3 sm:p-6"
      onMouseDown={e => { if (e.target === e.currentTarget) onClose(); }}
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-label="Oyuncu piyasa değeri kariyer değişim grafiği"
        className="w-full max-w-3xl max-h-[92dvh] overflow-y-auto rounded-md bg-background-primary shadow-md border border-border"
      >
        {/* Header */}
        <div className="border-b border-border p-5 sm:p-6 bg-background-primary">
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
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-xs font-medium text-text-secondary flex items-center gap-1">
                    <Coins className="w-3.5 h-3.5 text-text-tertiary" />
                    Transfermarkt Verileri
                  </span>
                  <span className="text-xs text-text-muted">· Kariyer Değer Gelişimi</span>
                </div>
                <h2 className="text-xl sm:text-2xl font-semibold text-text-primary tracking-tight truncate mt-0.5">
                  {effectiveName}
                </h2>
                <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-text-secondary">
                  {effectiveTeamName && (
                    <span className="font-medium text-text-primary">{effectiveTeamName}</span>
                  )}
                  {effectivePos && (
                    <span className="rounded-sm border border-border bg-background-tertiary px-1.5 py-0.2 text-xs font-medium text-text-secondary">
                      {effectivePos}
                    </span>
                  )}
                  {data?.tm_id && (
                    <span className="text-xs font-mono text-text-muted">
                      ID: #{data.tm_id}
                    </span>
                  )}
                </div>
              </div>
            </div>

            <button
              type="button"
              onClick={onClose}
              className="rounded border border-border bg-background-primary hover:bg-background-secondary p-2 text-text-secondary hover:text-text-primary transition-colors cursor-pointer"
              title="Kapat"
              aria-label="Kapat"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="p-5 sm:p-6 space-y-6">
          {loading && (
            <div className="flex flex-col items-center justify-center py-16 text-text-tertiary space-y-2">
              <Loader2 className="w-6 h-6 animate-spin text-primary" />
              <p className="text-xs font-medium text-text-secondary">
                Piyasa değeri geçmişi yükleniyor...
              </p>
            </div>
          )}

          {error && !loading && (
            <div className="rounded border border-status-error bg-background-secondary p-4 text-center text-status-error space-y-2">
              <p className="font-medium text-sm">{error}</p>
              <button
                type="button"
                onClick={() => {
                  setData(null);
                  setError(null);
                  setLoading(true);
                }}
                className="text-xs font-semibold underline cursor-pointer"
              >
                Yeniden dene
              </button>
            </div>
          )}

          {!loading && !error && data && (
            <>
              {/* 4 KPI Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {/* Güncel Değer */}
                <div className="bg-background-primary border border-border rounded p-3.5 space-y-1">
                  <span className="text-xs font-medium text-text-secondary block">
                    Güncel Değer
                  </span>
                  <span className="text-xl sm:text-2xl font-semibold font-mono text-text-primary block tabular-nums">
                    {currentVal?.formatted || '—'}
                  </span>
                  <span className="text-xs text-text-tertiary font-mono block truncate">
                    {currentVal?.date_formatted || 'Son kayıt'}
                  </span>
                </div>

                {/* Kariyer Zirvesi */}
                <div className="bg-background-primary border border-border rounded p-3.5 space-y-1">
                  <span className="text-xs font-medium text-text-secondary flex items-center justify-between">
                    <span>Kariyer Zirvesi</span>
                    <Award className="w-3.5 h-3.5 text-text-tertiary" />
                  </span>
                  <span className="text-xl sm:text-2xl font-semibold font-mono text-text-primary block tabular-nums">
                    {peakVal?.formatted || '—'}
                  </span>
                  <span className="text-xs text-text-tertiary font-mono block truncate">
                    {peakVal ? `${peakVal.age ? `${peakVal.age} Yaş · ` : ''}${peakVal.date_formatted}` : '—'}
                  </span>
                </div>

                {/* Toplam Büyüme */}
                <div className="bg-background-primary border border-border rounded p-3.5 space-y-1">
                  <span className="text-xs font-medium text-text-secondary block">
                    Kariyer Büyümesi
                  </span>
                  <div className="flex items-baseline gap-1">
                    <span className="text-xl sm:text-2xl font-semibold font-mono text-text-primary tabular-nums">
                      {totalGrowthPct != null ? (totalGrowthPct >= 0 ? `+${totalGrowthPct}%` : `${totalGrowthPct}%`) : '—'}
                    </span>
                    {totalGrowthPct != null && totalGrowthPct >= 0 ? (
                      <TrendingUp className="w-4 h-4 text-status-success shrink-0 self-center" />
                    ) : totalGrowthPct != null ? (
                      <TrendingDown className="w-4 h-4 text-status-error shrink-0 self-center" />
                    ) : null}
                  </div>
                  <span className="text-xs text-text-tertiary font-mono block">
                    {totalGrowthDiff != null ? (totalGrowthDiff >= 0 ? `+€${totalGrowthDiff}M` : `€${totalGrowthDiff}M`) : '—'}
                  </span>
                </div>

                {/* Değerleme Sayısı & İlk Değer */}
                <div className="bg-background-primary border border-border rounded p-3.5 space-y-1">
                  <span className="text-xs font-medium text-text-secondary block">
                    Değerleme Sayısı
                  </span>
                  <span className="text-xl sm:text-2xl font-semibold font-mono text-text-primary block tabular-nums">
                    {history.length} Kayıt
                  </span>
                  <span className="text-xs text-text-tertiary font-mono block truncate">
                    {firstVal ? `İlk: ${firstVal.formatted} (${firstVal.year})` : 'Kayıt yok'}
                  </span>
                </div>
              </div>

              {/* Trend Chart */}
              <div className="bg-background-primary rounded border border-border p-4 sm:p-5 space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-medium text-text-primary flex items-center gap-1.5">
                    <Coins className="w-3.5 h-3.5 text-text-tertiary" />
                    Kariyer Piyasa Değeri Gelişimi (€ Milyon)
                  </span>
                  <div className="flex items-center gap-3">
                    {peakVal && (
                      <span className="flex items-center gap-1.5 text-xs text-text-secondary font-medium">
                        <span className="w-2 h-2 rounded-full bg-primary" />
                        Zirve: {peakVal.formatted}
                      </span>
                    )}
                    <span className="text-xs text-text-muted bg-background-tertiary px-2 py-0.5 rounded font-mono">
                      Transfermarkt
                    </span>
                  </div>
                </div>

                {/* SVG Curve Canvas */}
                <div className="relative w-full overflow-x-auto">
                  <svg
                    viewBox={`0 0 ${svgWidth} ${svgHeight}`}
                    className="w-full h-auto min-w-[420px] select-none"
                    onMouseLeave={() => setHoveredPoint(null)}
                  >
                    <defs>
                      <linearGradient id="playerAreaGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#0f172a" stopOpacity="0.12" />
                        <stop offset="100%" stopColor="#0f172a" stopOpacity="0.0" />
                      </linearGradient>
                    </defs>

                    {/* Horizontal gridlines */}
                    {[0.25, 0.5, 0.75, 1.0].map((ratio, idx) => {
                      const y = svgHeight - paddingY - ratio * chartHeight;
                      const valAtY = minVal + ratio * (maxVal - minVal);
                      return (
                        <g key={idx}>
                          <line
                            x1={paddingX}
                            y1={y}
                            x2={svgWidth - paddingX}
                            y2={y}
                            stroke="#e2e8f0"
                            strokeWidth="1"
                            strokeDasharray="3 3"
                          />
                          <text
                            x={paddingX - 8}
                            y={y + 3}
                            textAnchor="end"
                            fontSize="10"
                            fill="#64748b"
                            fontFamily="monospace"
                          >
                            €{valAtY >= 1 ? valAtY.toFixed(0) : (valAtY * 1000).toFixed(0)}M
                          </text>
                        </g>
                      );
                    })}

                    {/* Gradient Fill Area */}
                    {areaPath && (
                      <path d={areaPath} fill="url(#playerAreaGrad)" />
                    )}

                    {/* Main Trend Line */}
                    {linePath && (
                      <path
                        d={linePath}
                        fill="none"
                        stroke="#0f172a"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    )}

                    {/* Data Points */}
                    {points.map((p) => {
                      const isHovered = hoveredPoint?.idx === p.idx;
                      const isPeak = p.isPeak;
                      const isLatest = p.isLatest;

                      return (
                        <g
                          key={p.idx}
                          className="cursor-pointer"
                          onMouseEnter={() => setHoveredPoint(p)}
                        >
                          {/* Outer ring on hover/peak */}
                          {(isPeak || isHovered) && (
                            <circle
                              cx={p.x}
                              cy={p.y}
                              r={isHovered ? 7 : 6}
                              fill="none"
                              stroke="#0f172a"
                              strokeWidth="1.5"
                              strokeOpacity="0.3"
                            />
                          )}

                          {/* Center point circle */}
                          <circle
                            cx={p.x}
                            cy={p.y}
                            r={isPeak ? 4.5 : isHovered ? 4.5 : isLatest ? 4 : 3}
                            fill={isPeak || isLatest || isHovered ? '#0f172a' : '#ffffff'}
                            stroke="#0f172a"
                            strokeWidth="1.5"
                          />

                          {/* Year labels */}
                          {(p.idx === 0 || p.idx === points.length - 1 || (points.length > 6 && p.idx % Math.ceil(points.length / 5) === 0)) && (
                            <text
                              x={p.x}
                              y={svgHeight - 12}
                              textAnchor="middle"
                              fontSize="10"
                              fill="#64748b"
                              fontFamily="monospace"
                            >
                              {p.year}
                            </text>
                          )}
                        </g>
                      );
                    })}

                    {/* Tooltip on hover */}
                    {hoveredPoint && (
                      <g>
                        <rect
                          x={Math.max(10, Math.min(svgWidth - 140, hoveredPoint.x - 65))}
                          y={Math.max(8, hoveredPoint.y - 48)}
                          width="130"
                          height="40"
                          rx="4"
                          fill="#0f172a"
                        />
                        <text
                          x={Math.max(10, Math.min(svgWidth - 140, hoveredPoint.x - 65)) + 65}
                          y={Math.max(8, hoveredPoint.y - 48) + 15}
                          textAnchor="middle"
                          fontSize="11"
                          fontWeight="600"
                          fill="#ffffff"
                          fontFamily="monospace"
                        >
                          {hoveredPoint.formatted}
                          {hoveredPoint.change_pct != null && (
                            <tspan fill={hoveredPoint.change_pct >= 0 ? '#34d399' : '#f87171'} fontSize="10">
                              {' '}({hoveredPoint.change_pct >= 0 ? `+${hoveredPoint.change_pct}%` : `${hoveredPoint.change_pct}%`})
                            </tspan>
                          )}
                        </text>
                        <text
                          x={Math.max(10, Math.min(svgWidth - 140, hoveredPoint.x - 65)) + 65}
                          y={Math.max(8, hoveredPoint.y - 48) + 30}
                          textAnchor="middle"
                          fontSize="9.5"
                          fill="#94a3b8"
                        >
                          {hoveredPoint.date_formatted} {hoveredPoint.age ? `· ${hoveredPoint.age} yaş` : ''}
                        </text>
                      </g>
                    )}
                  </svg>
                </div>
              </div>

              {/* Chronological History Table */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-text-secondary flex items-center gap-1.5">
                    <Calendar className="w-3.5 h-3.5 text-text-tertiary" />
                    Kariyer Değerleme Kayıtları ({reversedHistory.length})
                  </h3>
                  <span className="text-xs text-text-tertiary">
                    Yeniden eskiye
                  </span>
                </div>

                <div className="overflow-hidden rounded border border-border max-h-[300px] overflow-y-auto">
                  <table className="w-full text-xs text-left">
                    <thead className="bg-background-tertiary text-xs font-medium text-text-secondary border-b border-border sticky top-0 z-10">
                      <tr>
                        <th className="py-2.5 px-3.5">Tarih</th>
                        <th className="py-2.5 px-3.5">Kulüp</th>
                        <th className="py-2.5 px-2.5 text-center">Yaş</th>
                        <th className="py-2.5 px-3.5 text-right">Piyasa Değeri</th>
                        <th className="py-2.5 px-3.5 text-right">Değişim</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border-light bg-background-primary">
                      {reversedHistory.map((h, idx) => {
                        const isPeak = peakVal && h.date === peakVal.date && h.market_value_eur === peakVal.market_value_eur;
                        const isLatest = idx === 0;

                        return (
                          <tr
                            key={idx}
                            className="hover:bg-background-secondary transition-colors"
                          >
                            <td className="py-2.5 px-3.5 font-medium text-text-primary whitespace-nowrap">
                              <div className="flex items-center gap-1.5">
                                <span>{h.date_formatted}</span>
                                {isLatest && (
                                  <span className="px-1.5 py-0.2 rounded-sm bg-background-tertiary text-text-primary text-xs font-mono border border-border">
                                    Güncel
                                  </span>
                                )}
                                {isPeak && !isLatest && (
                                  <span className="px-1.5 py-0.2 rounded-sm bg-background-tertiary text-text-secondary text-xs font-mono border border-border">
                                    Zirve
                                  </span>
                                )}
                              </div>
                            </td>
                            <td className="py-2.5 px-3.5 text-text-secondary whitespace-nowrap">
                              {h.club_name || '—'}
                            </td>
                            <td className="py-2.5 px-2.5 text-center font-mono text-text-secondary">
                              {h.age || '—'}
                            </td>
                            <td className="py-2.5 px-3.5 text-right font-mono font-medium text-text-primary tabular-nums whitespace-nowrap">
                              {h.formatted}
                            </td>
                            <td className="py-2.5 px-3.5 text-right font-mono tabular-nums whitespace-nowrap">
                              {h.change_pct != null ? (
                                <span className={`inline-flex items-center gap-0.5 font-medium ${h.change_pct > 0 ? 'text-status-success' : h.change_pct < 0 ? 'text-status-error' : 'text-text-muted'}`}>
                                  {h.change_pct > 0 ? '+' : ''}{h.change_pct}%
                                  {h.change_diff != null && (
                                    <span className="text-xs text-text-muted ml-1">
                                      ({h.change_diff > 0 ? `+€${h.change_diff}M` : `€${h.change_diff}M`})
                                    </span>
                                  )}
                                </span>
                              ) : (
                                <span className="text-text-muted">—</span>
                              )}
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

        {/* Modal Footer */}
        <div className="flex items-center justify-between border-t border-border bg-background-primary px-5 py-4">
          <span className="text-xs text-text-tertiary flex items-center gap-1.5">
            <Coins className="w-3.5 h-3.5 text-text-muted" />
            Transfermarkt resmi piyasa değerleme arşivi
          </span>
          <button
            type="button"
            onClick={onClose}
            className="rounded border border-border bg-background-primary px-4 py-2 text-xs font-medium text-text-primary hover:bg-background-secondary transition-colors cursor-pointer"
          >
            Kapat
          </button>
        </div>
      </section>
    </div>
  );
}
