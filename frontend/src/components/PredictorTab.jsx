import PredictorMetricCards from './PredictorMetricCards';
import { handleTeamBadgeError } from '../utils/imageFallbacks';
import { formatSeasonLabel } from '../utils/dateFormatters';
import React, { useState, useEffect, useMemo } from 'react';
import { TEAMS, TEAM_MAP } from '../data/teams';
import { Trophy, ArrowRightLeft } from 'lucide-react';
import { getMatchPrediction } from '../services/matchService';

export default function PredictorTab({ selectedSeason }) {
  // Season team ID memberships
  const teams2223Ids = [1, 2, 4, 6, 7, 9, 10, 11, 12, 15, 20, 21, 23, 25, 26, 34, 38, 127, 130, 131];
  const teams2324Ids = [1, 2, 4, 6, 7, 10, 11, 12, 15, 18, 21, 23, 25, 34, 38, 43, 127, 130, 131, 163];
  const teams2425Ids = [1, 2, 4, 6, 7, 8, 10, 11, 12, 15, 20, 21, 23, 25, 26, 34, 38, 127, 130, 131];
  const teams2526Ids = [1, 2, 4, 6, 7, 9, 10, 11, 12, 15, 21, 23, 25, 29, 34, 38, 43, 127, 130, 131];

  const availableTeams = useMemo(() => {
    if (selectedSeason === '2022_23') {
      return TEAMS.filter(t => teams2223Ids.includes(t.id));
    }
    if (selectedSeason === '2023_24') {
      return TEAMS.filter(t => teams2324Ids.includes(t.id));
    }
    if (selectedSeason === '2024_25') {
      return TEAMS.filter(t => teams2425Ids.includes(t.id));
    }
    if (selectedSeason === '2025_26') {
      return TEAMS.filter(t => teams2526Ids.includes(t.id));
    }
    return TEAMS;
  }, [selectedSeason]);

  const [homeId, setHomeId] = useState(1);   // Arsenal
  const [awayId, setAwayId] = useState(4);   // Chelsea
  const [prediction, setPrediction] = useState(null);
  const [loading, setLoading] = useState(false);

  // Auto-adjust home/away if team is not in current season
  useEffect(() => {
    const isHomeValid = availableTeams.some(t => t.id === homeId);
    const isAwayValid = availableTeams.some(t => t.id === awayId);

    if (!isHomeValid && availableTeams.length > 0) {
      setHomeId(availableTeams[0].id);
    }
    if (!isAwayValid && availableTeams.length > 1) {
      setAwayId(availableTeams[1].id);
    }
  }, [availableTeams]);

  const homeTeam = TEAM_MAP[homeId] || availableTeams[0] || TEAMS[0];
  const awayTeam = TEAM_MAP[awayId] || availableTeams[1] || TEAMS[1];

  const fetchPrediction = async (hId, aId, season) => {
    if (hId === aId) return;
    setLoading(true);
    try {
      const data = await getMatchPrediction(hId, aId, undefined, season);
      setPrediction(data);
    } catch (err) {
      console.error('Prediction fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPrediction(homeId, awayId, selectedSeason);
  }, [homeId, awayId, selectedSeason]);

  const swapTeams = () => {
    const temp = homeId;
    setHomeId(awayId);
    setAwayId(temp);
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
      <div className="bg-background-primary border border-border rounded p-6 md:p-8  relative overflow-hidden">
        
        {/* Top Control Bar: Season indicator & Quick Derbies */}
        <div className="flex flex-wrap items-center justify-between gap-3 mb-6 pb-4 border-b border-border-light">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold text-text-secondary">Hızlı seçim</span>
            {derbies.map(d => (
              <button
                key={d.name}
                onClick={() => { setHomeId(d.h); setAwayId(d.a); }}
                className="px-3 py-1 text-xs font-bold rounded bg-background-tertiary hover:bg-slate-200 text-text-secondary border border-border transition-all whitespace-nowrap"
              >
                {d.name}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-1.5 text-xs text-text-secondary font-medium">
            <span>Sezon</span>
            <strong className="text-text-primary font-mono">{selectedSeason === 'all' ? 'Tüm sezonlar' : formatSeasonLabel(selectedSeason)}</strong>
          </div>
        </div>

        {/* Teams Matchup Center */}
        <div className="grid grid-cols-1 md:grid-cols-5 items-center gap-6">
          
          {/* Home Team */}
          <div className="md:col-span-2 flex flex-col items-center md:items-end text-center md:text-right space-y-3">
            <div className="relative group">
              <div className="w-24 h-24 md:w-28 md:h-28 rounded bg-background-tertiary p-4 border border-border flex items-center justify-center transition-transform duration-200 group-hover:scale-105 shadow-inner">
                <img 
                  src={homeTeam.badge} 
                  alt={homeTeam.name} 
                  className="w-full h-full object-contain filter drop-"
                  onError={handleTeamBadgeError}
                />
              </div>
              <span className="absolute -bottom-2.5 left-1/2 -translate-x-1/2 px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider bg-background-tertiary text-text-secondary border border-slate-300 ">
                Ev Sahibi
              </span>
            </div>

            <div className="pt-2 w-full max-w-xs">
              <select
                value={homeId}
                onChange={(e) => setHomeId(Number(e.target.value))}
                className="w-full bg-background-primary border border-border text-text-primary font-bold text-base md:text-lg rounded px-4 py-2.5 outline-none focus:border-slate-400 transition-all cursor-pointer text-center md:text-right"
              >
                {availableTeams.map(t => (
                  <option key={t.id} value={t.id} disabled={t.id === awayId}>
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
              onClick={swapTeams}
              title="Ev sahibi / Deplasman değiştir"
              className="p-2.5 rounded bg-background-primary hover:bg-background-tertiary text-text-secondary hover:text-text-primary border border-border transition-all hover:rotate-180 duration-300"
            >
              <ArrowRightLeft className="w-4 h-4" />
            </button>
            {loading && (
              <span className="text-xs font-semibold text-text-secondary animate-pulse">
                Hesaplanıyor...
              </span>
            )}
          </div>

          {/* Away Team */}
          <div className="md:col-span-2 flex flex-col items-center md:items-start text-center md:text-left space-y-3">
            <div className="relative group">
              <div className="w-24 h-24 md:w-28 md:h-28 rounded bg-background-tertiary p-4 border border-border flex items-center justify-center transition-transform duration-200 group-hover:scale-105 shadow-inner">
                <img 
                  src={awayTeam.badge} 
                  alt={awayTeam.name} 
                  className="w-full h-full object-contain filter drop-"
                  onError={handleTeamBadgeError}
                />
              </div>
              <span className="absolute -bottom-2.5 left-1/2 -translate-x-1/2 px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider bg-background-tertiary text-text-secondary border border-slate-300 ">
                Deplasman
              </span>
            </div>

            <div className="pt-2 w-full max-w-xs">
              <select
                value={awayId}
                onChange={(e) => setAwayId(Number(e.target.value))}
                className="w-full bg-background-primary border border-border text-text-primary font-bold text-base md:text-lg rounded px-4 py-2.5 outline-none focus:border-slate-400 transition-all cursor-pointer text-center md:text-left"
              >
                {availableTeams.map(t => (
                  <option key={t.id} value={t.id} disabled={t.id === homeId}>
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
                  <Trophy className="w-4 h-4 text-text-muted shrink-0" />
                <span className="text-xs font-bold uppercase tracking-wider text-text-secondary truncate">
                  Maç sonucu olasılığı
                </span>
              </div>
              <span className="text-xs font-semibold text-text-secondary bg-background-tertiary px-3 py-1 rounded-full border border-border shrink-0">
                {prediction.favorite_label}
              </span>
            </div>

            {/* Segmented Trio Bar */}
            <div className="h-4 rounded-full overflow-hidden flex bg-background-tertiary p-0.5 border border-border gap-0.5">
              <div 
                style={{ width: `${prediction.outcome.home_win_pct}%` }}
                className="h-full bg-slate-800 transition-all duration-700 rounded-l-full"
              />
              <div 
                style={{ width: `${prediction.outcome.draw_pct}%` }}
                className="h-full bg-slate-400 transition-all duration-700"
              />
              <div 
                style={{ width: `${prediction.outcome.away_win_pct}%` }}
                className="h-full bg-slate-200 transition-all duration-700 rounded-r-full"
              />
            </div>

            {/* Odds / Percent Labels */}
            <div className="grid grid-cols-3 text-center pt-2 font-mono gap-2 sm:gap-3">
              <div className="bg-background-primary border border-border rounded p-2.5 flex flex-col items-center">
                <span className="text-xs text-text-secondary font-sans font-medium truncate max-w-full">
                  1 ({homeTeam.abbr || homeTeam.short || 'EV'})
                </span>
                <span className="text-base sm:text-lg font-semibold text-text-primary font-mono">
                  %{prediction.outcome.home_win_pct}
                </span>
                <span className="text-xs text-text-muted font-sans font-medium">
                  Oran: {(100 / Math.max(1, prediction.outcome.home_win_pct)).toFixed(2)}
                </span>
              </div>
              <div className="bg-background-primary border border-border rounded p-2.5 flex flex-col items-center">
                <span className="text-xs text-text-secondary font-sans font-medium truncate max-w-full">
                  X (Beraberlik)
                </span>
                <span className="text-base sm:text-lg font-semibold text-text-secondary font-mono">
                  %{prediction.outcome.draw_pct}
                </span>
                <span className="text-xs text-text-muted font-sans font-medium">
                  Oran: {(100 / Math.max(1, prediction.outcome.draw_pct)).toFixed(2)}
                </span>
              </div>
              <div className="bg-background-primary border border-border rounded p-2.5 flex flex-col items-center">
                <span className="text-xs text-text-secondary font-sans font-medium truncate max-w-full">
                  2 ({awayTeam.abbr || awayTeam.short || 'DEP'})
                </span>
                <span className="text-base sm:text-lg font-semibold text-text-secondary font-mono">
                  %{prediction.outcome.away_win_pct}
                </span>
                <span className="text-xs text-text-muted font-sans font-medium">
                  Oran: {(100 / Math.max(1, prediction.outcome.away_win_pct)).toFixed(2)}
                </span>
              </div>
            </div>

            {/* Dynamic Lineup Impact Strip */}
            {prediction.lineup_analysis && (
              <div className="pt-3 border-t border-border-light flex flex-wrap items-center justify-between gap-2 text-xs">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-status-success" />
                  <span className="font-bold text-text-primary">
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
