import React, { useState, useEffect } from 'react';
import { X, TrendingUp, TrendingDown, Coins, Calendar, Award, Shield, User, Loader2 } from 'lucide-react';
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
      className="fixed inset-0 z-[120] flex items-center justify-center bg-slate-950/75 p-3 backdrop-blur-md sm:p-6 animate-fadeIn"
      onMouseDown={e => { if (e.target === e.currentTarget) onClose(); }}
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-label="Oyuncu piyasa değeri kariyer değişim grafiği"
        className="w-full max-w-3xl max-h-[92dvh] overflow-y-auto rounded-3xl bg-white shadow-2xl border border-slate-200"
      >
        {/* Header */}
        <div className="relative overflow-hidden bg-gradient-to-br from-[#38003c] via-[#240027] to-[#120014] px-6 py-6 text-white sm:px-8 sm:py-7">
          <div className="absolute -right-10 -top-16 h-52 w-52 rounded-full bg-amber-400/20 blur-3xl pointer-events-none" />
          <div className="absolute -left-10 -bottom-16 h-40 w-40 rounded-full bg-purple-600/20 blur-2xl pointer-events-none" />
          <div className="absolute bottom-0 left-0 h-px w-full bg-gradient-to-r from-transparent via-amber-400/30 to-transparent" />

          <div className="relative flex items-start justify-between gap-4">
            <div className="flex items-center gap-4 min-w-0">
              <div className="relative shrink-0">
                <PlayerAvatar
                  player={player}
                  photoUrl={effectivePhoto}
                  name={effectiveName}
                  size="xl"
                  shape="rounded"
                  fallback="shirt"
                  className="w-14 h-14 sm:w-16 sm:h-16 rounded-2xl bg-white/10 border-2 border-white/20 shadow-lg object-cover"
                />
                {effectiveBadge && (
                  <div className="absolute -bottom-1 -right-1 w-6 h-6 rounded-full bg-white p-0.5 shadow-md border border-slate-200">
                    <img src={effectiveBadge} alt="" className="w-full h-full object-contain" onError={e => { e.target.style.display = 'none'; }} />
                  </div>
                )}
              </div>

              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-[10px] font-black uppercase tracking-wider text-amber-300 flex items-center gap-1">
                    <Coins className="w-3 h-3 text-amber-300" /> Transfermarkt Verileri
                  </span>
                  <span className="text-xs text-purple-200">• Kariyer Değer Gelişimi</span>
                </div>
                <h3 className="text-xl sm:text-2xl font-black text-white tracking-tight truncate mt-0.5">
                  {effectiveName}
                </h3>
                <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-purple-200">
                  {effectiveTeamName && (
                    <span className="font-semibold text-white/90">{effectiveTeamName}</span>
                  )}
                  {effectivePos && (
                    <span className="rounded bg-white/15 px-2 py-0.5 text-[11px] font-medium text-purple-100">
                      {effectivePos}
                    </span>
                  )}
                  {data?.tm_id && (
                    <span className="text-[10px] font-mono text-purple-300/80">
                      ID: #{data.tm_id}
                    </span>
                  )}
                </div>
              </div>
            </div>

            <button
              onClick={onClose}
              className="rounded-xl border border-white/15 bg-white/10 hover:bg-white/20 p-2 text-white transition cursor-pointer"
              title="Kapat"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="p-6 sm:p-8 space-y-6">
          {loading && (
            <div className="flex flex-col items-center justify-center py-16 text-slate-400 space-y-3">
              <Loader2 className="w-8 h-8 animate-spin text-amber-500" />
              <p className="text-sm font-semibold text-slate-600">
                {effectiveName} için piyasa değeri geçmişi yükleniyor...
              </p>
            </div>
          )}

          {error && !loading && (
            <div className="rounded-2xl border border-red-200 bg-red-50 p-6 text-center text-red-700 space-y-2">
              <p className="font-bold text-sm">{error}</p>
              <button
                onClick={() => {
                  setData(null);
                  setError(null);
                  setLoading(true);
                }}
                className="text-xs font-semibold underline hover:text-red-800 cursor-pointer"
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
                <div className="bg-amber-50/70 border border-amber-200/80 rounded-2xl p-3.5 space-y-1">
                  <span className="text-[10px] font-extrabold uppercase tracking-wider text-amber-800 block">
                    Güncel Değer
                  </span>
                  <strong className="text-xl sm:text-2xl font-black font-mono text-amber-950 block">
                    {currentVal?.formatted || '—'}
                  </strong>
                  <span className="text-[11px] text-amber-800/80 font-mono font-medium block truncate">
                    {currentVal?.date_formatted || 'Son kayıt'}
                  </span>
                </div>

                {/* Kariyer Zirvesi */}
                <div className="bg-indigo-50/70 border border-indigo-200/80 rounded-2xl p-3.5 space-y-1">
                  <span className="text-[10px] font-extrabold uppercase tracking-wider text-indigo-800 flex items-center justify-between">
                    <span>Kariyer Zirvesi</span>
                    <Award className="w-3 h-3 text-indigo-600" />
                  </span>
                  <strong className="text-xl sm:text-2xl font-black font-mono text-indigo-950 block">
                    {peakVal?.formatted || '—'}
                  </strong>
                  <span className="text-[11px] text-indigo-800/80 font-mono font-medium block truncate">
                    {peakVal ? `${peakVal.age ? `${peakVal.age} Yaş · ` : ''}${peakVal.date_formatted}` : '—'}
                  </span>
                </div>

                {/* Toplam Büyüme */}
                <div className="bg-emerald-50/70 border border-emerald-200/80 rounded-2xl p-3.5 space-y-1">
                  <span className="text-[10px] font-extrabold uppercase tracking-wider text-emerald-800 block">
                    Kariyer Büyümesi
                  </span>
                  <div className="flex items-baseline gap-1 text-emerald-700">
                    <strong className="text-xl sm:text-2xl font-black font-mono">
                      {totalGrowthPct != null ? (totalGrowthPct >= 0 ? `+${totalGrowthPct}%` : `${totalGrowthPct}%`) : '—'}
                    </strong>
                    {totalGrowthPct != null && totalGrowthPct >= 0 ? (
                      <TrendingUp className="w-4 h-4 text-emerald-600 shrink-0 self-center" />
                    ) : totalGrowthPct != null ? (
                      <TrendingDown className="w-4 h-4 text-rose-600 shrink-0 self-center" />
                    ) : null}
                  </div>
                  <span className="text-[11px] text-emerald-800/80 font-mono font-medium block">
                    {totalGrowthDiff != null ? (totalGrowthDiff >= 0 ? `+€${totalGrowthDiff}M` : `€${totalGrowthDiff}M`) : '—'}
                  </span>
                </div>

                {/* Değerleme Sayısı & İlk Değer */}
                <div className="bg-purple-50/70 border border-purple-200/80 rounded-2xl p-3.5 space-y-1">
                  <span className="text-[10px] font-extrabold uppercase tracking-wider text-purple-800 block">
                    Değerleme Sayısı
                  </span>
                  <strong className="text-xl sm:text-2xl font-black font-mono text-purple-950 block">
                    {history.length} Kayıt
                  </strong>
                  <span className="text-[11px] text-purple-700 font-medium block truncate">
                    {firstVal ? `İlk: ${firstVal.formatted} (${firstVal.year})` : 'Kayıt bulunamadı'}
                  </span>
                </div>
              </div>

              {/* Interactive SVG Trend Chart */}
              <div className="bg-slate-900 rounded-2xl p-4 sm:p-6 border border-slate-800 text-white shadow-inner space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-slate-300 flex items-center gap-1.5">
                    <Coins className="w-3.5 h-3.5 text-amber-400" />
                    Kariyer Piyasa Değeri Gelişimi (€ Milyon)
                  </span>
                  <div className="flex items-center gap-3">
                    {peakVal && (
                      <span className="flex items-center gap-1 text-[11px] text-amber-300 font-medium">
                        <span className="w-2.5 h-2.5 rounded-full bg-amber-400 border border-amber-200" />
                        Zirve: {peakVal.formatted}
                      </span>
                    )}
                    <span className="text-[10px] text-slate-400 bg-slate-800 px-2 py-0.5 rounded font-mono">
                      Transfermarkt Doğrulanmış
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
                        <stop offset="0%" stopColor="#f59e0b" stopOpacity="0.45" />
                        <stop offset="100%" stopColor="#f59e0b" stopOpacity="0.0" />
                      </linearGradient>
                      <linearGradient id="playerLineGrad" x1="0" y1="0" x2="1" y2="0">
                        <stop offset="0%" stopColor="#fbbf24" />
                        <stop offset="100%" stopColor="#f59e0b" />
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
                            stroke="#334155"
                            strokeWidth="1"
                            strokeDasharray="4 4"
                            strokeOpacity="0.6"
                          />
                          <text
                            x={paddingX - 8}
                            y={y + 3}
                            textAnchor="end"
                            fontSize="9"
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
                        stroke="url(#playerLineGrad)"
                        strokeWidth="3"
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
                          className="cursor-pointer transition-transform"
                          onMouseEnter={() => setHoveredPoint(p)}
                        >
                          {/* Outer pulse ring on peak or hovered */}
                          {(isPeak || isHovered) && (
                            <circle
                              cx={p.x}
                              cy={p.y}
                              r={isHovered ? 9 : 7.5}
                              fill="none"
                              stroke={isPeak ? '#fbbf24' : '#60a5fa'}
                              strokeWidth="2"
                              strokeOpacity="0.6"
                              className={isPeak ? 'animate-pulse' : ''}
                            />
                          )}

                          {/* Center point circle */}
                          <circle
                            cx={p.x}
                            cy={p.y}
                            r={isPeak ? 5.5 : isHovered ? 5 : isLatest ? 4.5 : 3.5}
                            fill={isPeak ? '#fef08a' : isHovered ? '#93c5fd' : '#fbbf24'}
                            stroke="#0f172a"
                            strokeWidth="1.5"
                          />

                          {/* Show Year labels on select points (first, last, and every few points) */}
                          {(p.idx === 0 || p.idx === points.length - 1 || (points.length > 6 && p.idx % Math.ceil(points.length / 5) === 0)) && (
                            <text
                              x={p.x}
                              y={svgHeight - 12}
                              textAnchor="middle"
                              fontSize="10"
                              fontWeight={isLatest ? "bold" : "normal"}
                              fill={isLatest ? '#fbbf24' : '#94a3b8'}
                            >
                              {p.year}
                            </text>
                          )}
                        </g>
                      );
                    })}

                    {/* Interactive Tooltip on hover */}
                    {hoveredPoint && (
                      <g>
                        {/* Tooltip Background */}
                        <rect
                          x={Math.max(10, Math.min(svgWidth - 150, hoveredPoint.x - 70))}
                          y={Math.max(8, hoveredPoint.y - 52)}
                          width="140"
                          height="44"
                          rx="8"
                          fill="#0f172a"
                          stroke="#38bdf8"
                          strokeWidth="1.5"
                          filter="drop-shadow(0 4px 6px rgba(0,0,0,0.5))"
                        />
                        {/* Tooltip Content */}
                        <text
                          x={Math.max(10, Math.min(svgWidth - 150, hoveredPoint.x - 70)) + 70}
                          y={Math.max(8, hoveredPoint.y - 52) + 16}
                          textAnchor="middle"
                          fontSize="11"
                          fontWeight="bold"
                          fill="#f8fafc"
                          fontFamily="monospace"
                        >
                          {hoveredPoint.formatted}
                          {hoveredPoint.change_pct != null && (
                            <tspan fill={hoveredPoint.change_pct >= 0 ? '#4ade80' : '#f87171'} fontSize="10">
                              {' '}({hoveredPoint.change_pct >= 0 ? `+${hoveredPoint.change_pct}%` : `${hoveredPoint.change_pct}%`})
                            </tspan>
                          )}
                        </text>
                        <text
                          x={Math.max(10, Math.min(svgWidth - 150, hoveredPoint.x - 70)) + 70}
                          y={Math.max(8, hoveredPoint.y - 52) + 32}
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
                  <h4 className="text-xs font-black uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                    <Calendar className="w-3.5 h-3.5 text-slate-500" />
                    Kariyer Değerleme Kayıtları ({reversedHistory.length})
                  </h4>
                  <span className="text-[11px] text-slate-500 font-medium">
                    En son değerlemeden eskiye doğru
                  </span>
                </div>

                <div className="overflow-hidden rounded-2xl border border-slate-200 shadow-2xs max-h-[300px] overflow-y-auto">
                  <table className="w-full text-xs text-left">
                    <thead className="bg-slate-50 text-[10px] font-bold uppercase tracking-wider text-slate-500 border-b border-slate-200 sticky top-0 z-10">
                      <tr>
                        <th className="py-2.5 px-3.5">Tarih</th>
                        <th className="py-2.5 px-3.5">Kulüp</th>
                        <th className="py-2.5 px-2.5 text-center">Yaş</th>
                        <th className="py-2.5 px-3.5 text-right">Piyasa Değeri</th>
                        <th className="py-2.5 px-3.5 text-right">Değişim</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {reversedHistory.map((h, idx) => {
                        const isPeak = peakVal && h.date === peakVal.date && h.market_value_eur === peakVal.market_value_eur;
                        const isLatest = idx === 0;

                        return (
                          <tr
                            key={idx}
                            className={`transition hover:bg-slate-50 ${isLatest ? 'bg-amber-50/30' : ''} ${isPeak ? 'font-medium' : ''}`}
                          >
                            <td className="py-2.5 px-3.5 font-medium text-slate-900 whitespace-nowrap">
                              <div className="flex items-center gap-1.5">
                                <span>{h.date_formatted}</span>
                                {isLatest && (
                                  <span className="px-1.5 py-0.2 rounded bg-amber-100 text-amber-900 text-[9px] font-black font-mono border border-amber-300">
                                    GÜNCEL
                                  </span>
                                )}
                                {isPeak && !isLatest && (
                                  <span className="px-1.5 py-0.2 rounded bg-indigo-100 text-indigo-900 text-[9px] font-black font-mono border border-indigo-200">
                                    ZİRVE
                                  </span>
                                )}
                              </div>
                            </td>
                            <td className="py-2.5 px-3.5 text-slate-700 whitespace-nowrap">
                              {h.club_name || '—'}
                            </td>
                            <td className="py-2.5 px-2.5 text-center font-mono text-slate-600">
                              {h.age || '—'}
                            </td>
                            <td className="py-2.5 px-3.5 text-right font-mono font-bold text-slate-900 whitespace-nowrap">
                              {h.formatted}
                            </td>
                            <td className="py-2.5 px-3.5 text-right font-mono whitespace-nowrap">
                              {h.change_pct != null ? (
                                <span className={`inline-flex items-center gap-0.5 font-bold ${h.change_pct > 0 ? 'text-emerald-600' : h.change_pct < 0 ? 'text-rose-600' : 'text-slate-500'}`}>
                                  {h.change_pct > 0 ? '+' : ''}{h.change_pct}%
                                  {h.change_diff != null && (
                                    <span className="text-[10px] font-normal text-slate-400 ml-1">
                                      ({h.change_diff > 0 ? `+€${h.change_diff}M` : `€${h.change_diff}M`})
                                    </span>
                                  )}
                                </span>
                              ) : (
                                <span className="text-slate-400">—</span>
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
        <div className="flex items-center justify-between border-t border-slate-100 bg-slate-50 px-6 py-4 rounded-b-3xl">
          <span className="text-[11px] text-slate-500 flex items-center gap-1.5">
            <Coins className="w-3.5 h-3.5 text-amber-600" />
            Tüm değerler Transfermarkt resmi piyasa değerleme arşivinden derlenmiştir.
          </span>
          <button
            onClick={onClose}
            className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs font-bold text-slate-700 hover:bg-slate-100 transition shadow-2xs cursor-pointer"
          >
            Kapat
          </button>
        </div>
      </section>
    </div>
  );
}
