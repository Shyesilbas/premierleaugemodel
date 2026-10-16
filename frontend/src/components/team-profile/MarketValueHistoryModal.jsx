import { Coins, TrendingUp, X } from 'lucide-react';
import { getTeam } from '../../data/teams';
import { formatSeasonLabel } from '../../utils/dateFormatters';

export default function MarketValueHistoryModal({ isOpen, onClose, profile, selectedSeason }) {
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

  const maxVal = history.length > 0 ? Math.max(...history.map(h => h.market_value_eur)) * 1.15 : 1000;
  const minVal = history.length > 0 ? Math.max(0, Math.min(...history.map(h => h.market_value_eur)) * 0.8) : 0;

  const svgWidth = 560;
  const svgHeight = 200;
  const paddingX = 50;
  const paddingY = 35;
  const chartWidth = svgWidth - paddingX * 2;
  const chartHeight = svgHeight - paddingY * 2;

  const points = history.map((item, idx) => {
    const x = history.length > 1 ? paddingX + (idx / (history.length - 1)) * chartWidth : svgWidth / 2;
    const yRange = maxVal - minVal || 1;
    const y = svgHeight - paddingY - ((item.market_value_eur - minVal) / yRange) * chartHeight;
    return { ...item, x, y };
  });

  const linePath = points.length > 1
    ? points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ')
    : '';

  const areaPath = points.length > 1
    ? `${linePath} L ${points[points.length - 1].x.toFixed(1)} ${svgHeight - paddingY} L ${points[0].x.toFixed(1)} ${svgHeight - paddingY} Z`
    : '';

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/70 p-3 backdrop-blur-md sm:p-6 animate-fadeIn"
      onMouseDown={e => { if (e.target === e.currentTarget) onClose(); }}
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-label="Kadro piyasa değeri değişim grafiği"
        className="w-full max-w-2xl max-h-[92dvh] overflow-y-auto rounded-3xl bg-white shadow-2xl border border-slate-200"
      >
        {/* Header */}
        <div className="relative overflow-hidden bg-gradient-to-br from-[#38003c] via-[#240027] to-[#120014] px-6 py-6 text-white sm:px-8 sm:py-7">
          <div className="absolute -right-8 -top-16 h-48 w-48 rounded-full bg-amber-400/20 blur-3xl pointer-events-none" />
          <div className="absolute bottom-0 left-0 h-px w-full bg-gradient-to-r from-transparent via-amber-400/30 to-transparent" />
          
          <div className="relative flex items-start justify-between gap-4">
            <div className="flex items-center gap-3.5 min-w-0">
              <div className="w-12 h-12 rounded-2xl bg-white/10 p-2 border border-white/15 backdrop-blur-sm shrink-0 flex items-center justify-center">
                <img src={teamBadge} alt={teamName} className="w-full h-full object-contain drop-shadow" />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-black uppercase tracking-wider text-amber-300 flex items-center gap-1">
                    <Coins className="w-3 h-3 text-amber-300" /> Transfermarkt Verileri
                  </span>
                  <span className="text-xs text-purple-200">• 5 Yıllık Trend</span>
                </div>
                <h3 className="text-xl sm:text-2xl font-black text-white tracking-tight truncate mt-0.5">
                  {teamName} Kadro Piyasa Değeri
                </h3>
              </div>
            </div>

            <button
              onClick={onClose}
              className="rounded-xl border border-white/15 bg-white/10 hover:bg-white/20 p-2 text-white transition cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="p-6 sm:p-8 space-y-6">
          
          {/* Top KPI row */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="bg-amber-50/70 border border-amber-200/80 rounded-2xl p-3.5 space-y-1">
              <span className="text-[10px] font-extrabold uppercase tracking-wider text-amber-800 block">
                Mevcut Değer ({formatSeasonLabel(mv.season, '/')})
              </span>
              <strong className="text-xl sm:text-2xl font-black font-mono text-amber-950 block">
                {mv.formatted}
              </strong>
              <span className="text-[11px] text-amber-800/80 font-mono font-medium block">
                Ort. {mv.avg_formatted || '-'}
              </span>
            </div>

            <div className="bg-emerald-50/70 border border-emerald-200/80 rounded-2xl p-3.5 space-y-1">
              <span className="text-[10px] font-extrabold uppercase tracking-wider text-emerald-800 block">
                5 Yıllık Büyüme
              </span>
              <div className="flex items-baseline gap-1 text-emerald-700">
                <strong className="text-xl sm:text-2xl font-black font-mono">
                  {totalChangePct ? (Number(totalChangePct) >= 0 ? `+${totalChangePct}%` : `${totalChangePct}%`) : '-'}
                </strong>
                <TrendingUp className="w-4 h-4 text-emerald-600 shrink-0 self-center" />
              </div>
              <span className="text-[11px] text-emerald-800/80 font-mono font-medium block">
                {totalChangeDiff ? (Number(totalChangeDiff) >= 0 ? `+€${totalChangeDiff}M` : `€${totalChangeDiff}M`) : '-'}
              </span>
            </div>

            <div className="bg-slate-50 border border-slate-200 rounded-2xl p-3.5 space-y-1">
              <span className="text-[10px] font-extrabold uppercase tracking-wider text-slate-500 block">
                Kadro Genişliği
              </span>
              <strong className="text-xl sm:text-2xl font-black font-mono text-slate-900 block">
                {mv.squad_size ? `${mv.squad_size} Oyuncu` : '-'}
              </strong>
              <span className="text-[11px] text-slate-500 font-medium block">
                Kayıtlı Roster
              </span>
            </div>

            <div className="bg-purple-50/70 border border-purple-200/80 rounded-2xl p-3.5 space-y-1">
              <span className="text-[10px] font-extrabold uppercase tracking-wider text-purple-800 block">
                İlk Sezon ({firstSeason?.season_label})
              </span>
              <strong className="text-xl sm:text-2xl font-black font-mono text-purple-950 block">
                {firstSeason?.formatted || '-'}
              </strong>
              <span className="text-[11px] text-purple-700 font-medium block">
                Referans Bazı
              </span>
            </div>
          </div>

          {/* SVG Chart */}
          <div className="bg-slate-900 rounded-2xl p-4 sm:p-6 border border-slate-800 text-white shadow-inner space-y-3">
            <div className="flex items-center justify-between text-xs">
              <span className="font-bold text-slate-300 flex items-center gap-1.5">
                <Coins className="w-3.5 h-3.5 text-amber-400" />
                Sezonluk Piyasa Değeri Eğrisi (€ Milyar)
              </span>
              <span className="text-[10px] text-slate-400 bg-slate-800 px-2 py-0.5 rounded font-mono">
                Transfermarkt Doğrulanmış
              </span>
            </div>

            <div className="relative w-full overflow-x-auto">
              <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} className="w-full h-auto min-w-[360px] select-none">
                <defs>
                  <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#f59e0b" stopOpacity="0.45" />
                    <stop offset="100%" stopColor="#f59e0b" stopOpacity="0.0" />
                  </linearGradient>
                  <linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#fbbf24" stopOpacity="0.85" />
                    <stop offset="100%" stopColor="#b45309" stopOpacity="0.25" />
                  </linearGradient>
                </defs>

                {[0.25, 0.5, 0.75, 1.0].map((ratio, idx) => {
                  const y = svgHeight - paddingY - ratio * chartHeight;
                  return (
                    <line
                      key={idx}
                      x1={paddingX}
                      y1={y}
                      x2={svgWidth - paddingX}
                      y2={y}
                      stroke="#334155"
                      strokeWidth="1"
                      strokeDasharray="4 4"
                      strokeOpacity="0.6"
                    />
                  );
                })}

                {areaPath && (
                  <path d={areaPath} fill="url(#areaGrad)" />
                )}

                {linePath && (
                  <path
                    d={linePath}
                    fill="none"
                    stroke="#fbbf24"
                    strokeWidth="3"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                )}

                {points.map((p) => {
                  const isCurrent = p.season === selectedSeason;
                  const barWidth = 22;
                  const barY = p.y;
                  const barHeight = svgHeight - paddingY - barY;

                  return (
                    <g key={p.season} className="transition-all">
                      <rect
                        x={p.x - barWidth / 2}
                        y={barY}
                        width={barWidth}
                        height={Math.max(barHeight, 4)}
                        rx="4"
                        fill="url(#barGrad)"
                        stroke={isCurrent ? '#fef08a' : '#f59e0b'}
                        strokeWidth={isCurrent ? '2' : '0.5'}
                        opacity={isCurrent ? '1' : '0.75'}
                      />

                      <circle
                        cx={p.x}
                        cy={p.y}
                        r={isCurrent ? 6 : 4.5}
                        fill={isCurrent ? '#fef08a' : '#fbbf24'}
                        stroke="#1e293b"
                        strokeWidth="2"
                      />

                      <text
                        x={p.x}
                        y={p.y - 10}
                        textAnchor="middle"
                        fontSize={isCurrent ? "12" : "10"}
                        fontWeight="bold"
                        fill={isCurrent ? '#fef08a' : '#f1f5f9'}
                        fontFamily="monospace"
                      >
                        {p.formatted}
                      </text>

                      <text
                        x={p.x}
                        y={svgHeight - 12}
                        textAnchor="middle"
                        fontSize="10"
                        fontWeight={isCurrent ? "bold" : "normal"}
                        fill={isCurrent ? '#fbbf24' : '#94a3b8'}
                      >
                        {p.season_label}
                      </text>
                    </g>
                  );
                })}
              </svg>
            </div>
          </div>

          {/* Breakdown Table */}
          <div className="space-y-2">
            <h4 className="text-xs font-black uppercase tracking-wider text-slate-700">
              Sezon Bazlı Değişim Detayları
            </h4>
            <div className="overflow-hidden rounded-2xl border border-slate-200 shadow-2xs">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-50 text-[10px] font-bold uppercase tracking-wider text-slate-500 border-b border-slate-200">
                  <tr>
                    <th className="py-2.5 px-3">Sezon</th>
                    <th className="py-2.5 px-3 text-right">Kadro Değeri</th>
                    <th className="py-2.5 px-3 text-right">Oyuncu Başı Ort.</th>
                    <th className="py-2.5 px-3 text-right">Kadro</th>
                    <th className="py-2.5 px-3 text-right">Yıllık Değişim (YoY)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {history.map((row, idx) => {
                    const prevRow = idx > 0 ? history[idx - 1] : null;
                    const diffPct = prevRow && prevRow.market_value_eur > 0
                      ? (((row.market_value_eur - prevRow.market_value_eur) / prevRow.market_value_eur) * 100).toFixed(1)
                      : null;
                    const isSelected = row.season === selectedSeason;

                    return (
                      <tr key={row.season} className={isSelected ? 'bg-amber-50/70 font-semibold' : 'hover:bg-slate-50/70'}>
                        <td className="py-2.5 px-3 font-bold text-slate-800 flex items-center gap-1.5">
                          {row.season_label}
                          {isSelected && (
                            <span className="text-[9px] px-1.5 py-0.2 rounded bg-amber-200 text-amber-900 font-sans font-bold">
                              Seçili Sezon
                            </span>
                          )}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono font-bold text-slate-900">
                          {row.formatted}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono text-slate-600">
                          {row.avg_formatted}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono text-slate-600">
                          {row.squad_size}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono">
                          {diffPct === null ? (
                            <span className="text-slate-400">-</span>
                          ) : Number(diffPct) > 0 ? (
                            <span className="text-emerald-700 font-bold bg-emerald-100/70 px-1.5 py-0.5 rounded">
                              +{diffPct}%
                            </span>
                          ) : Number(diffPct) < 0 ? (
                            <span className="text-rose-700 font-bold bg-rose-100/70 px-1.5 py-0.5 rounded">
                              {diffPct}%
                            </span>
                          ) : (
                            <span className="text-slate-500">0.0%</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

        </div>
      </section>
    </div>
  );
}
