import PredictorMetricCards from './PredictorMetricCards';
import { handleTeamBadgeError } from '../utils/imageFallbacks';
import { formatSeasonLabel } from '../utils/dateFormatters';
import React, { useEffect, useMemo, useState } from 'react';
import { TEAMS, TEAM_MAP } from '../data/teams';
import { ArrowRightLeft, Trophy } from 'lucide-react';
import { getMatchPrediction } from '../services/matchService';

const SEASON_TEAM_IDS = {
  '2022_23': [1, 2, 4, 6, 7, 9, 10, 11, 12, 15, 20, 21, 23, 25, 26, 34, 38, 127, 130, 131],
  '2023_24': [1, 2, 4, 6, 7, 10, 11, 12, 15, 18, 21, 23, 25, 34, 38, 43, 127, 130, 131, 163],
  '2024_25': [1, 2, 4, 6, 7, 8, 10, 11, 12, 15, 20, 21, 23, 25, 26, 34, 38, 127, 130, 131],
  '2025_26': [1, 2, 4, 6, 7, 9, 10, 11, 12, 15, 21, 23, 25, 29, 34, 38, 43, 127, 130, 131],
};

export default function PredictorTab({ selectedSeason }) {
  const availableTeams = useMemo(() => {
    const ids = SEASON_TEAM_IDS[selectedSeason];
    return ids ? TEAMS.filter(t => ids.includes(t.id)) : TEAMS;
  }, [selectedSeason]);

  const [homeId, setHomeId] = useState(1);
  const [awayId, setAwayId] = useState(4);
  const [predictionResult, setPredictionResult] = useState(null);

  const effectiveHomeId = availableTeams.some(t => t.id === homeId)
    ? homeId
    : (availableTeams[0]?.id ?? homeId);
  const effectiveAwayId = availableTeams.some(t => t.id === awayId && t.id !== effectiveHomeId)
    ? awayId
    : (availableTeams.find(t => t.id !== effectiveHomeId)?.id ?? awayId);

  const homeTeam = TEAM_MAP[effectiveHomeId] || availableTeams[0] || TEAMS[0];
  const awayTeam = TEAM_MAP[effectiveAwayId] || availableTeams[1] || TEAMS[1];

  const requestKey = `${effectiveHomeId}:${effectiveAwayId}:${selectedSeason || ''}`;

  useEffect(() => {
    if (effectiveHomeId === effectiveAwayId) return undefined;
    let cancelled = false;

    getMatchPrediction(effectiveHomeId, effectiveAwayId, undefined, selectedSeason)
      .then((data) => {
        if (!cancelled) setPredictionResult({ key: requestKey, data });
      })
      .catch((err) => {
        console.error('Prediction fetch error:', err);
        if (!cancelled) setPredictionResult(prev => ({ key: requestKey, data: prev?.data || null }));
      });

    return () => {
      cancelled = true;
    };
  }, [effectiveHomeId, effectiveAwayId, selectedSeason, requestKey]);

  const loading = effectiveHomeId !== effectiveAwayId && predictionResult?.key !== requestKey;
  const prediction = predictionResult?.data || null;

  const swapTeams = () => {
    setHomeId(effectiveAwayId);
    setAwayId(effectiveHomeId);
  };

  const derbies = [
    { name: 'Londra Derbisi', h: 1, a: 4 },
    { name: 'Zirve Maçı', h: 11, a: 10 },
    { name: 'Kuzey Londra', h: 1, a: 21 },
    { name: 'Kuzeybatı Derbisi', h: 12, a: 10 },
  ];

  return (
    <div className="space-y-6">
      {/* Matchup Header Card */}
      <div className="bg-background-primary border border-border rounded p-6 md:p-8 relative overflow-hidden">
        {/* Top Control Bar: Season indicator & Quick Derbies */}
        <div className="flex flex-wrap items-center justify-between gap-3 mb-6 pb-4 border-b border-border-light">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold text-text-secondary">Hızlı seçim</span>
            {derbies.map(d => (
              <button
                type="button"
                key={d.name}
                onClick={() => { setHomeId(d.h); setAwayId(d.a); }}
                className="px-3 py-1 text-xs font-semibold rounded bg-background-tertiary hover:bg-background-secondary text-text-secondary hover:text-text-primary border border-border transition-colors whitespace-nowrap cursor-pointer"
              >
                {d.name}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-1.5 text-xs text-text-secondary font-medium">
            <span>Sezon</span>
            <strong className="text-text-primary font-mono tabular-nums">
              {selectedSeason === 'all' ? 'Tüm sezonlar' : formatSeasonLabel(selectedSeason)}
            </strong>
          </div>
        </div>

        {/* Teams Matchup Center */}
        <div className="grid grid-cols-1 md:grid-cols-5 items-center gap-6">
          {/* Home Team */}
          <div className="md:col-span-2 flex flex-col items-center md:items-end text-center md:text-right space-y-3">
            <div className="relative">
              <div className="w-24 h-24 md:w-28 md:h-28 rounded bg-background-tertiary p-4 border border-border flex items-center justify-center">
                <img
                  src={homeTeam.badge}
                  alt={homeTeam.name}
                  className="w-full h-full object-contain"
                  onError={handleTeamBadgeError}
                />
              </div>
              <span className="absolute -bottom-2.5 left-1/2 -translate-x-1/2 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-background-primary text-text-secondary border border-border whitespace-nowrap">
                Ev Sahibi
              </span>
            </div>

            <div className="pt-2 w-full max-w-xs">
              <label htmlFor="predictor-home-select" className="visually-hidden">Ev sahibi takım</label>
              <select
                id="predictor-home-select"
                value={effectiveHomeId}
                onChange={(e) => setHomeId(Number(e.target.value))}
                className="w-full bg-background-primary border border-border text-text-primary font-semibold text-base md:text-lg rounded px-4 py-2.5 outline-none focus:border-border-focus transition-colors cursor-pointer text-center md:text-right"
              >
                {availableTeams.map(t => (
                  <option key={t.id} value={t.id} disabled={t.id === effectiveAwayId}>
                    {t.name}
                  </option>
                ))}
              </select>
              <p className="text-xs text-text-secondary mt-1 font-medium">{homeTeam.stadium}</p>
            </div>
          </div>

          {/* Center VS & Swap */}
          <div className="md:col-span-1 flex flex-col items-center justify-center space-y-2">
            <div className="w-12 h-12 rounded-full bg-background-primary border border-border flex items-center justify-center font-semibold text-xs text-text-secondary">
              VS
            </div>
            <button
              type="button"
              onClick={swapTeams}
              title="Ev sahibi / Deplasman değiştir"
              aria-label="Ev sahibi ve deplasman takımlarını değiştir"
              className="p-2.5 rounded bg-background-primary hover:bg-background-tertiary text-text-secondary hover:text-text-primary border border-border transition-colors cursor-pointer"
            >
              <ArrowRightLeft className="w-4 h-4" strokeWidth={1.5} aria-hidden="true" />
            </button>
            {loading && (
              <span className="text-xs font-semibold text-text-secondary">
                Hesaplanıyor...
              </span>
            )}
          </div>

          {/* Away Team */}
          <div className="md:col-span-2 flex flex-col items-center md:items-start text-center md:text-left space-y-3">
            <div className="relative">
              <div className="w-24 h-24 md:w-28 md:h-28 rounded bg-background-tertiary p-4 border border-border flex items-center justify-center">
                <img
                  src={awayTeam.badge}
                  alt={awayTeam.name}
                  className="w-full h-full object-contain"
                  onError={handleTeamBadgeError}
                />
              </div>
              <span className="absolute -bottom-2.5 left-1/2 -translate-x-1/2 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-background-primary text-text-secondary border border-border whitespace-nowrap">
                Deplasman
              </span>
            </div>

            <div className="pt-2 w-full max-w-xs">
              <label htmlFor="predictor-away-select" className="visually-hidden">Deplasman takımı</label>
              <select
                id="predictor-away-select"
                value={effectiveAwayId}
                onChange={(e) => setAwayId(Number(e.target.value))}
                className="w-full bg-background-primary border border-border text-text-primary font-semibold text-base md:text-lg rounded px-4 py-2.5 outline-none focus:border-border-focus transition-colors cursor-pointer text-center md:text-left"
              >
                {availableTeams.map(t => (
                  <option key={t.id} value={t.id} disabled={t.id === effectiveHomeId}>
                    {t.name}
                  </option>
                ))}
              </select>
              <p className="text-xs text-text-secondary mt-1 font-medium">{awayTeam.stadium}</p>
            </div>
          </div>
        </div>

        {/* 1X2 Probabilities Bar */}
        {prediction && (
          <div className="mt-8 pt-6 border-t border-border-light space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2 min-w-0">
                <Trophy className="w-4 h-4 text-text-muted shrink-0" strokeWidth={1.5} aria-hidden="true" />
                <span className="text-xs font-semibold text-text-secondary truncate">
                  Maç sonucu olasılığı
                </span>
              </div>
              <span className="text-xs font-semibold text-text-secondary bg-background-tertiary px-3 py-1 rounded-full border border-border shrink-0">
                {prediction.favorite_label}
              </span>
            </div>

            {/* Segmented Trio Bar */}
            <div className="h-3.5 rounded-full overflow-hidden flex bg-background-tertiary border border-border gap-0.5">
              <div
                style={{ width: `${prediction.outcome.home_win_pct}%` }}
                className="h-full bg-primary transition-all duration-300"
              />
              <div
                style={{ width: `${prediction.outcome.draw_pct}%` }}
                className="h-full bg-text-muted transition-all duration-300"
              />
              <div
                style={{ width: `${prediction.outcome.away_win_pct}%` }}
                className="h-full bg-card-border-hover transition-all duration-300"
              />
            </div>

            {/* Odds / Percent Labels */}
            <div className="grid grid-cols-3 text-center pt-2 font-mono gap-2 sm:gap-3">
              <div className="bg-background-primary border border-border rounded p-2.5 flex flex-col items-center">
                <span className="text-xs text-text-secondary font-sans font-medium truncate max-w-full">
                  1 ({homeTeam.abbr || homeTeam.short || 'EV'})
                </span>
                <span className="text-base sm:text-lg font-semibold text-text-primary font-mono tabular-nums">
                  %{prediction.outcome.home_win_pct}
                </span>
                <span className="text-xs text-text-tertiary font-sans font-medium tabular-nums">
                  Oran: {(100 / Math.max(1, prediction.outcome.home_win_pct)).toFixed(2)}
                </span>
              </div>
              <div className="bg-background-primary border border-border rounded p-2.5 flex flex-col items-center">
                <span className="text-xs text-text-secondary font-sans font-medium truncate max-w-full">
                  X (Beraberlik)
                </span>
                <span className="text-base sm:text-lg font-semibold text-text-secondary font-mono tabular-nums">
                  %{prediction.outcome.draw_pct}
                </span>
                <span className="text-xs text-text-tertiary font-sans font-medium tabular-nums">
                  Oran: {(100 / Math.max(1, prediction.outcome.draw_pct)).toFixed(2)}
                </span>
              </div>
              <div className="bg-background-primary border border-border rounded p-2.5 flex flex-col items-center">
                <span className="text-xs text-text-secondary font-sans font-medium truncate max-w-full">
                  2 ({awayTeam.abbr || awayTeam.short || 'DEP'})
                </span>
                <span className="text-base sm:text-lg font-semibold text-text-secondary font-mono tabular-nums">
                  %{prediction.outcome.away_win_pct}
                </span>
                <span className="text-xs text-text-tertiary font-sans font-medium tabular-nums">
                  Oran: {(100 / Math.max(1, prediction.outcome.away_win_pct)).toFixed(2)}
                </span>
              </div>
            </div>

            {/* Dynamic Lineup Impact Strip */}
            {prediction.lineup_analysis && (
              <div className="pt-3 border-t border-border-light flex flex-wrap items-center justify-between gap-2 text-xs">
                <div className="flex items-center gap-2">
                  <span aria-hidden="true" className="w-2 h-2 rounded-full bg-status-success" />
                  <span className="font-semibold text-text-primary tabular-nums">
                    İlk 11 Formu: {homeTeam.abbr || 'EV'} ({prediction.lineup_analysis.home_xi?.team_overall}) vs {awayTeam.abbr || 'DEP'} ({prediction.lineup_analysis.away_xi?.team_overall})
                  </span>
                  <span className="text-xs text-text-secondary font-medium">({prediction.lineup_analysis.status_label})</span>
                </div>
                {prediction.lineup_analysis.lineup_impact?.summary_text && (
                  <span className="text-xs font-mono text-text-secondary bg-background-tertiary border border-border px-2.5 py-0.5 rounded-full">
                    {prediction.lineup_analysis.lineup_impact.summary_text}
                  </span>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      <PredictorMetricCards
        prediction={prediction}
        homeTeam={homeTeam}
        awayTeam={awayTeam}
      />
    </div>
  );
}
