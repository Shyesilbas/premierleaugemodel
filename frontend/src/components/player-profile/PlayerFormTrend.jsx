import React, { useMemo, useState } from 'react';
import { Activity, TrendingDown, TrendingUp } from 'lucide-react';
import { getTeam } from '../../data/teams';
import { kickoffSortKey, parseKickoff } from '../../utils/dateFormatters';
import { Badge } from '../common/Badge';
import { Card } from '../common/Card';

const METRICS = [
  { key: 'rating', label: 'Reyting', decimals: 1 },
  { key: 'goals', label: 'Gol', decimals: 0 },
  { key: 'assists', label: 'Asist', decimals: 0 },
  { key: 'ga', label: 'G+A', decimals: 0 },
  { key: 'minutes', label: 'Dakika', decimals: 0 },
];

function extractValue(match, key) {
  if (key === 'rating') return match.rating != null ? Number(match.rating) : null;
  if (key === 'goals') return Number(match.goals || 0);
  if (key === 'assists') return Number(match.assists || 0);
  if (key === 'ga') return Number(match.goals || 0) + Number(match.assists || 0);
  return Number(match.minutes_played || 0);
}

function formatMetric(value, decimals) {
  if (value == null || Number.isNaN(value)) return '—';
  return Number(value).toFixed(decimals);
}

export default function PlayerFormTrend({ matches = [] }) {
  const [metric, setMetric] = useState('rating');
  const [hoverIdx, setHoverIdx] = useState(null);

  const ordered = useMemo(
    () => [...matches].sort((a, b) => kickoffSortKey(a.kickoff) - kickoffSortKey(b.kickoff)),
    [matches],
  );

  const hasRatings = useMemo(() => ordered.some((m) => m.rating != null), [ordered]);
  const activeMetric = metric === 'rating' && !hasRatings ? 'goals' : metric;
  const activeMeta = METRICS.find((m) => m.key === activeMetric) || METRICS[0];

  const series = useMemo(() => {
    const valid = ordered
      .map((m) => {
        const value = extractValue(m, activeMetric);
        if (value == null) return null;
        const opp = getTeam(m.opponent_id, m.opponent_name);
        const kickoff = parseKickoff(m.kickoff);
        const label = m.round_label || (m.gameweek ? `H${Math.round(Number(m.gameweek))}` : kickoff.date);
        return {
          matchId: m.match_id,
          value,
          label,
          date: kickoff.date,
          opponent: opp?.short || opp?.name || m.opponent_name || 'Rakip',
          score: m.team_score != null && m.opp_score != null ? `${m.team_score}-${m.opp_score}` : '',
        };
      })
      .filter(Boolean);
    return valid;
  }, [ordered, activeMetric]);

  if (ordered.length < 2 || series.length < 2) {
    return null;
  }

  const recent = series.slice(-24);
  const seasonAvg = series.reduce((acc, s) => acc + s.value, 0) / series.length;
  const last5 = series.slice(-5);
  const last5Avg = last5.reduce((acc, s) => acc + s.value, 0) / last5.length;
  const last10 = series.slice(-10);
  const last10Avg = last10.reduce((acc, s) => acc + s.value, 0) / last10.length;
  const delta = last5Avg - seasonAvg;
  const avgDecimals = activeMeta.decimals === 0 ? 2 : 2;

  const width = 640;
  const height = 148;
  const padX = 24;
  const padY = 18;
  const innerW = width - padX * 2;
  const innerH = height - padY * 2;

  const values = recent.map((p) => p.value);
  const rawMin = Math.min(...values, seasonAvg);
  const rawMax = Math.max(...values, seasonAvg);
  const minVal = activeMetric === 'rating' ? Math.max(0, Math.floor(rawMin - 0.5)) : 0;
  const maxVal = activeMetric === 'rating'
    ? Math.min(10, Math.max(minVal + 2, Math.ceil(rawMax + 0.5)))
    : Math.max(rawMax * 1.15, minVal + 1);
  const span = Math.max(0.01, maxVal - minVal);

  const toX = (i) => (recent.length === 1 ? padX + innerW / 2 : padX + (i / (recent.length - 1)) * innerW);
  const toY = (v) => padY + innerH - ((v - minVal) / span) * innerH;

  const pointsAttr = recent.map((p, i) => `${toX(i).toFixed(1)},${toY(p.value).toFixed(1)}`).join(' ');
  const avgY = toY(seasonAvg);
  const activePoint = hoverIdx != null && recent[hoverIdx] ? recent[hoverIdx] : recent[recent.length - 1];

  return (
    <Card padding="md" className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-text-secondary shrink-0" strokeWidth={1.5} aria-hidden="true" />
          <div>
            <h2 className="text-base font-semibold text-text-primary">Form ve trend</h2>
            <p className="text-xs text-text-secondary tabular-nums">
              Son {recent.length} maçlık {activeMeta.label.toLowerCase()} seyri · kesikli çizgi sezon ortalaması ({formatMetric(seasonAvg, avgDecimals)})
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-1" role="group" aria-label="Trend metriği">
          {METRICS.filter((m) => m.key !== 'rating' || hasRatings).map((m) => {
            const selected = m.key === activeMetric;
            return (
              <button
                key={m.key}
                type="button"
                aria-pressed={selected}
                onClick={() => {
                  setMetric(m.key);
                  setHoverIdx(null);
                }}
                className={`h-8 rounded border px-2.5 text-xs font-medium transition-colors cursor-pointer ${
                  selected
                    ? 'border-primary bg-primary text-white'
                    : 'border-border bg-background-primary text-text-secondary hover:text-text-primary hover:border-card-border-hover'
                }`}
              >
                {m.label}
              </button>
            );
          })}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-px overflow-hidden rounded border border-border bg-border">
        <div className="bg-background-primary p-3">
          <span className="block text-xs text-text-secondary">Son {last5.length} maç ort.</span>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <span className="text-lg font-semibold text-text-primary tabular-nums">
              {formatMetric(last5Avg, avgDecimals)}
            </span>
            {Math.abs(delta) >= 0.05 && (
              <Badge variant={delta > 0 ? 'success' : 'error'} size="sm">
                {delta > 0 ? (
                  <TrendingUp className="h-3 w-3" aria-hidden="true" />
                ) : (
                  <TrendingDown className="h-3 w-3" aria-hidden="true" />
                )}
                <span className="tabular-nums">
                  {delta > 0 ? '+' : ''}
                  {delta.toFixed(2)}
                </span>
              </Badge>
            )}
          </div>
        </div>

        <div className="bg-background-primary p-3">
          <span className="block text-xs text-text-secondary">Son {last10.length} maç ort.</span>
          <span className="mt-1 block text-lg font-semibold text-text-primary tabular-nums">
            {formatMetric(last10Avg, avgDecimals)}
          </span>
        </div>

        <div className="bg-background-primary p-3">
          <span className="block text-xs text-text-secondary">Sezon ortalaması ({series.length} maç)</span>
          <span className="mt-1 block text-lg font-semibold text-text-primary tabular-nums">
            {formatMetric(seasonAvg, avgDecimals)}
          </span>
        </div>
      </div>

      <div className="rounded border border-border-light bg-background-secondary p-3">
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-xs text-text-secondary tabular-nums">
          <span>
            {activePoint.label} · {activePoint.opponent}
            {activePoint.score ? ` (${activePoint.score})` : ''}
          </span>
          <span className="font-semibold text-text-primary">
            {activeMeta.label}: {formatMetric(activePoint.value, activeMeta.decimals)}
          </span>
        </div>

        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="h-36 w-full overflow-visible"
          role="img"
          aria-label={`${activeMeta.label} form grafiği`}
        >
          <line
            x1={padX}
            x2={width - padX}
            y1={avgY}
            y2={avgY}
            className="stroke-text-muted"
            strokeWidth="1"
            strokeDasharray="4 4"
          />
          <polyline
            fill="none"
            className="stroke-primary"
            strokeWidth="2"
            strokeLinejoin="round"
            strokeLinecap="round"
            points={pointsAttr}
          />
          {recent.map((point, idx) => {
            const cx = toX(idx);
            const cy = toY(point.value);
            const isActive = idx === (hoverIdx ?? recent.length - 1);
            const aboveAvg = point.value >= seasonAvg;
            return (
              <g key={`${point.matchId}-${idx}`}>
                <circle
                  cx={cx}
                  cy={cy}
                  r={isActive ? 4.5 : 3}
                  className={aboveAvg ? 'fill-status-success stroke-background-primary' : 'fill-primary stroke-background-primary'}
                  strokeWidth="1.5"
                />
                <circle
                  cx={cx}
                  cy={cy}
                  r={12}
                  fill="transparent"
                  className="cursor-pointer"
                  onMouseEnter={() => setHoverIdx(idx)}
                  onFocus={() => setHoverIdx(idx)}
                />
              </g>
            );
          })}
        </svg>
      </div>
    </Card>
  );
}
