import React, { useState, useEffect, useMemo } from 'react';
import { TEAMS, TEAM_MAP } from '../data/teams';
import { Trophy, Target, Flag, Shield, Activity, ArrowRightLeft, Eye, CreditCard, Scale } from 'lucide-react';

export default function PredictorTab({ selectedSeason }) {
  // Season team ID memberships
  const teams2324Ids = [1, 2, 4, 6, 7, 10, 11, 12, 15, 18, 21, 23, 25, 34, 38, 43, 127, 130, 131, 163];
  const teams2425Ids = [1, 2, 4, 6, 7, 8, 10, 11, 12, 15, 20, 21, 23, 25, 26, 34, 38, 127, 130, 131];
  const teams2526Ids = [1, 2, 4, 6, 7, 9, 10, 11, 12, 15, 21, 23, 25, 29, 34, 38, 43, 127, 130, 131];

  const availableTeams = useMemo(() => {
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
      const seasonParam = season && season !== '2026_27' ? `&season=${season}` : '';
      const res = await fetch(`/api/predict?home_id=${hId}&away_id=${aId}${seasonParam}`);
      if (res.ok) {
        const data = await res.json();
        setPrediction(data);
      }
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
      <div className="bg-white border border-slate-200 rounded-3xl p-6 md:p-8 shadow-sm relative overflow-hidden">
        
        {/* Top Control Bar: Season indicator & Quick Derbies */}
        <div className="flex flex-wrap items-center justify-between gap-3 mb-6 pb-4 border-b border-slate-100">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold text-slate-500">Hızlı seçim</span>
            {derbies.map(d => (
              <button
                key={d.name}
                onClick={() => { setHomeId(d.h); setAwayId(d.a); }}
                className="px-3 py-1 text-xs font-bold rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200 transition-all whitespace-nowrap"
              >
                {d.name}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-1.5 text-xs text-slate-500 font-medium">
            <span>Sezon</span>
            <strong className="text-slate-800 font-mono">{selectedSeason === 'all' ? 'Tüm sezonlar' : selectedSeason.replace('_', '-')}</strong>
          </div>
        </div>

        {/* Teams Matchup Center */}
        <div className="grid grid-cols-1 md:grid-cols-5 items-center gap-6">
          
          {/* Home Team */}
          <div className="md:col-span-2 flex flex-col items-center md:items-end text-center md:text-right space-y-3">
            <div className="relative group">
              <div className="w-24 h-24 md:w-28 md:h-28 rounded-2xl bg-slate-50 p-4 border border-slate-200 flex items-center justify-center transition-transform duration-200 group-hover:scale-105 shadow-inner">
                <img 
                  src={homeTeam.badge} 
                  alt={homeTeam.name} 
                  className="w-full h-full object-contain filter drop-shadow-sm"
                  onError={(e) => { e.target.src = '/badges/1.svg'; }}
                />
              </div>
              <span className="absolute -bottom-2.5 left-1/2 -translate-x-1/2 px-2.5 py-0.5 rounded-full text-[10px] font-extrabold uppercase tracking-wider bg-slate-100 text-slate-700 border border-slate-300 shadow-sm">
                Ev Sahibi
              </span>
            </div>

            <div className="pt-2 w-full max-w-xs">
              <select
                value={homeId}
                onChange={(e) => setHomeId(Number(e.target.value))}
                className="w-full bg-white border border-slate-200 text-slate-900 font-bold text-base md:text-lg rounded-xl px-4 py-2.5 outline-none focus:border-slate-400 transition-all cursor-pointer text-center md:text-right"
              >
                {availableTeams.map(t => (
                  <option key={t.id} value={t.id} disabled={t.id === awayId}>
                    {t.name}
                  </option>
                ))}
              </select>
              <p className="text-xs text-slate-500 mt-1 font-medium">{homeTeam.stadium}</p>
            </div>
          </div>

          {/* Center VS & Swap */}
          <div className="md:col-span-1 flex flex-col items-center justify-center space-y-2">
            <div className="w-12 h-12 rounded-full bg-white border border-slate-200 flex items-center justify-center font-black text-xs text-slate-500">
              VS
            </div>
            <button
              onClick={swapTeams}
              title="Ev sahibi / Deplasman değiştir"
              className="p-2.5 rounded-xl bg-white hover:bg-slate-50 text-slate-500 hover:text-slate-900 border border-slate-200 transition-all hover:rotate-180 duration-300"
            >
              <ArrowRightLeft className="w-4 h-4" />
            </button>
            {loading && (
              <span className="text-[11px] font-semibold text-slate-500 animate-pulse">
                Hesaplanıyor...
              </span>
            )}
          </div>

          {/* Away Team */}
          <div className="md:col-span-2 flex flex-col items-center md:items-start text-center md:text-left space-y-3">
            <div className="relative group">
              <div className="w-24 h-24 md:w-28 md:h-28 rounded-2xl bg-slate-50 p-4 border border-slate-200 flex items-center justify-center transition-transform duration-200 group-hover:scale-105 shadow-inner">
                <img 
                  src={awayTeam.badge} 
                  alt={awayTeam.name} 
                  className="w-full h-full object-contain filter drop-shadow-sm"
                  onError={(e) => { e.target.src = '/badges/1.svg'; }}
                />
              </div>
              <span className="absolute -bottom-2.5 left-1/2 -translate-x-1/2 px-2.5 py-0.5 rounded-full text-[10px] font-extrabold uppercase tracking-wider bg-slate-100 text-slate-700 border border-slate-300 shadow-sm">
                Deplasman
              </span>
            </div>

            <div className="pt-2 w-full max-w-xs">
              <select
                value={awayId}
                onChange={(e) => setAwayId(Number(e.target.value))}
                className="w-full bg-white border border-slate-200 text-slate-900 font-bold text-base md:text-lg rounded-xl px-4 py-2.5 outline-none focus:border-slate-400 transition-all cursor-pointer text-center md:text-left"
              >
                {availableTeams.map(t => (
                  <option key={t.id} value={t.id} disabled={t.id === homeId}>
                    {t.name}
                  </option>
                ))}
              </select>
              <p className="text-xs text-slate-500 mt-1 font-medium">{awayTeam.stadium}</p>
            </div>
          </div>

        </div>

        {/* 1X2 Probabilities Bar */}
        {prediction && (
          <div className="mt-8 pt-6 border-t border-slate-100 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2 min-w-0">
                  <Trophy className="w-4 h-4 text-slate-400 shrink-0" />
                <span className="text-xs font-bold uppercase tracking-wider text-slate-700 truncate">
                  Maç sonucu olasılığı
                </span>
              </div>
              <span className="text-xs font-semibold text-slate-700 bg-slate-100 px-3 py-1 rounded-full border border-slate-200 shrink-0">
                {prediction.favorite_label}
              </span>
            </div>

            {/* Segmented Trio Bar */}
            <div className="h-4 rounded-full overflow-hidden flex bg-slate-100 p-0.5 border border-slate-200 gap-0.5">
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
              <div className="bg-white border border-slate-200 rounded-xl p-2.5 flex flex-col items-center">
                <span className="text-[11px] text-slate-500 font-sans font-medium truncate max-w-full">
                  1 ({homeTeam.abbr || homeTeam.short || 'EV'})
                </span>
                <span className="text-base sm:text-lg font-black text-slate-900 font-mono">
                  %{prediction.outcome.home_win_pct}
                </span>
                <span className="text-[10px] text-slate-400 font-sans font-medium">
                  Oran: {(100 / Math.max(1, prediction.outcome.home_win_pct)).toFixed(2)}
                </span>
              </div>
              <div className="bg-white border border-slate-200 rounded-xl p-2.5 flex flex-col items-center">
                <span className="text-[11px] text-slate-500 font-sans font-medium truncate max-w-full">
                  X (Beraberlik)
                </span>
                <span className="text-base sm:text-lg font-black text-slate-700 font-mono">
                  %{prediction.outcome.draw_pct}
                </span>
                <span className="text-[10px] text-slate-400 font-sans font-medium">
                  Oran: {(100 / Math.max(1, prediction.outcome.draw_pct)).toFixed(2)}
                </span>
              </div>
              <div className="bg-white border border-slate-200 rounded-xl p-2.5 flex flex-col items-center">
                <span className="text-[11px] text-slate-500 font-sans font-medium truncate max-w-full">
                  2 ({awayTeam.abbr || awayTeam.short || 'DEP'})
                </span>
                <span className="text-base sm:text-lg font-black text-slate-500 font-mono">
                  %{prediction.outcome.away_win_pct}
                </span>
                <span className="text-[10px] text-slate-400 font-sans font-medium">
                  Oran: {(100 / Math.max(1, prediction.outcome.away_win_pct)).toFixed(2)}
                </span>
              </div>
            </div>

          </div>
        )}

      </div>

      {/* 5 Micro-Metric Prediction Cards Grid */}
      {prediction && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          
          {/* Corners */}
          <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm hover:border-slate-300 transition-all flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between gap-2 mb-3">
                <div className="flex items-center gap-2 text-slate-600 min-w-0">
                  <Flag className="w-4 h-4 shrink-0" />
                  <span className="text-xs font-bold uppercase tracking-wider truncate">Toplam Korner</span>
                </div>
              </div>

              <div className="flex items-baseline gap-2 mb-2">
                <span className="text-3xl sm:text-4xl font-black tracking-tight font-mono text-slate-900">
                  {prediction.corners.expected_total}
                </span>
                <span className="text-xs font-semibold text-slate-500">beklenen korner</span>
              </div>

              {/* Team split pill */}
              <div className="flex items-center justify-between text-xs text-slate-600 font-medium bg-slate-50 px-3 py-1.5 rounded-xl border border-slate-100 mb-4">
                <div className="flex items-center gap-1.5 truncate">
                  <span className="text-slate-500">{homeTeam.abbr || homeTeam.short}:</span>
                  <strong className="text-slate-900 font-mono font-bold">{prediction.corners.expected_home}</strong>
                </div>
                <span className="text-slate-300">•</span>
                <div className="flex items-center gap-1.5 truncate">
                  <span className="text-slate-500">{awayTeam.abbr || awayTeam.short}:</span>
                  <strong className="text-slate-900 font-mono font-bold">{prediction.corners.expected_away}</strong>
                </div>
              </div>
            </div>

            <div className="space-y-2.5 pt-3 border-t border-slate-100">
              <div>
                <div className="flex justify-between items-center text-xs mb-1">
                  <span className="text-slate-600 font-medium">9.5 Üst Olasılığı</span>
                  <span className="font-mono font-bold text-slate-700 bg-slate-100 px-1.5 py-0.5 rounded text-[11px]">
                    %{prediction.corners.prob_over_9_5_pct}
                  </span>
                </div>
                <div className="h-1.5 rounded-full bg-slate-100 overflow-hidden">
                  <div 
                    style={{ width: `${Math.min(100, Math.max(0, prediction.corners.prob_over_9_5_pct))}%` }}
                    className="h-full bg-slate-700 rounded-full"
                  />
                </div>
              </div>
              <div>
                <div className="flex justify-between items-center text-xs mb-1">
                  <span className="text-slate-600 font-medium">10.5 Üst Olasılığı</span>
                  <span className="font-mono font-bold text-slate-700 bg-slate-100 px-1.5 py-0.5 rounded text-[11px]">
                    %{prediction.corners.prob_over_10_5_pct}
                  </span>
                </div>
                <div className="h-1.5 rounded-full bg-slate-100 overflow-hidden">
                  <div 
                    style={{ width: `${Math.min(100, Math.max(0, prediction.corners.prob_over_10_5_pct))}%` }}
                    className="h-full bg-slate-500 rounded-full"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Throws / Taç */}
          <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm hover:border-slate-300 transition-all flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between gap-2 mb-3">
                <div className="flex items-center gap-2 text-slate-600 min-w-0">
                  <Activity className="w-4 h-4 shrink-0" />
                  <span className="text-xs font-bold uppercase tracking-wider truncate">Toplam Taç</span>
                </div>
              </div>

              <div className="flex items-baseline gap-2 mb-2">
                <span className="text-3xl sm:text-4xl font-black tracking-tight font-mono text-slate-900">
                  {prediction.throws.expected_total}
                </span>
                <span className="text-xs font-semibold text-slate-500">beklenen taç atışı</span>
              </div>

              {/* Team split pill */}
              <div className="flex items-center justify-between text-xs text-slate-600 font-medium bg-slate-50 px-3 py-1.5 rounded-xl border border-slate-100 mb-4">
                <div className="flex items-center gap-1.5 truncate">
                  <span className="text-slate-500">{homeTeam.abbr || homeTeam.short}:</span>
                  <strong className="text-slate-900 font-mono font-bold">{prediction.throws.expected_home}</strong>
                </div>
                <span className="text-slate-300">•</span>
                <div className="flex items-center gap-1.5 truncate">
                  <span className="text-slate-500">{awayTeam.abbr || awayTeam.short}:</span>
                  <strong className="text-slate-900 font-mono font-bold">{prediction.throws.expected_away}</strong>
                </div>
              </div>
            </div>

            <div className="space-y-2.5 pt-3 border-t border-slate-100">
              <div>
                <div className="flex justify-between items-center text-xs mb-1">
                  <span className="text-slate-600 font-medium">33.5 Üst Olasılığı</span>
                  <span className="font-mono font-bold text-slate-700 bg-slate-100 px-1.5 py-0.5 rounded text-[11px]">
                    %{prediction.throws.prob_over_33_5_pct}
                  </span>
                </div>
                <div className="h-1.5 rounded-full bg-slate-100 overflow-hidden">
                  <div 
                    style={{ width: `${Math.min(100, Math.max(0, prediction.throws.prob_over_33_5_pct))}%` }}
                    className="h-full bg-slate-700 rounded-full"
                  />
                </div>
              </div>
              <div>
                <div className="flex justify-between items-center text-xs mb-1">
                  <span className="text-slate-600 font-medium">36.5 Üst Olasılığı</span>
                  <span className="font-mono font-bold text-slate-700 bg-slate-100 px-1.5 py-0.5 rounded text-[11px]">
                    %{prediction.throws.prob_over_36_5_pct}
                  </span>
                </div>
                <div className="h-1.5 rounded-full bg-slate-100 overflow-hidden">
                  <div 
                    style={{ width: `${Math.min(100, Math.max(0, prediction.throws.prob_over_36_5_pct))}%` }}
                    className="h-full bg-slate-500 rounded-full"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Saves */}
          <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm hover:border-slate-300 transition-all flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between gap-2 mb-3">
                <div className="flex items-center gap-2 text-slate-600 min-w-0">
                  <Shield className="w-4 h-4 shrink-0" />
                  <span className="text-xs font-bold uppercase tracking-wider truncate">Kaleci Kurtarışları</span>
                </div>
              </div>

              <div className="flex items-baseline gap-2 mb-2">
                <span className="text-3xl sm:text-4xl font-black tracking-tight font-mono text-slate-900">
                  {prediction.saves.expected_total}
                </span>
                <span className="text-xs font-semibold text-slate-500">toplam kurtarış</span>
              </div>

              {/* Team split pill */}
              <div className="flex items-center justify-between text-xs text-slate-600 font-medium bg-slate-50 px-3 py-1.5 rounded-xl border border-slate-100 mb-4">
                <div className="flex items-center gap-1.5 truncate">
                  <span className="text-slate-500">Ev GK:</span>
                  <strong className="text-slate-900 font-mono font-bold">{prediction.saves.expected_home}</strong>
                </div>
                <span className="text-slate-300">•</span>
                <div className="flex items-center gap-1.5 truncate">
                  <span className="text-slate-500">Dep GK:</span>
                  <strong className="text-slate-900 font-mono font-bold">{prediction.saves.expected_away}</strong>
                </div>
              </div>
            </div>

            <div className="space-y-2 pt-3 border-t border-slate-100">
              <div className="flex items-center justify-between text-xs p-2.5 rounded-xl bg-slate-50 border border-slate-100 gap-2">
                <span className="text-slate-500 font-medium shrink-0">Kurtarış Baskısı</span>
                <span className="font-bold text-slate-700 truncate text-right">
                  {prediction.saves.expected_away > prediction.saves.expected_home ? `${awayTeam.abbr || awayTeam.short} GK Yoğun` : `${homeTeam.abbr || homeTeam.short} GK Yoğun`}
                </span>
              </div>
              <div className="flex items-center justify-between text-xs p-2.5 rounded-xl bg-slate-50 border border-slate-100 gap-2">
                <span className="text-slate-500 font-medium shrink-0">Ceza Sahası Tehdidi</span>
                <span className="font-mono font-bold text-slate-700 truncate text-right">Yüksek Hacim</span>
              </div>
            </div>
          </div>

          {/* Offsides */}
          <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm hover:border-slate-300 transition-all flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between gap-2 mb-3">
                <div className="flex items-center gap-2 text-slate-600 min-w-0">
                  <Eye className="w-4 h-4 shrink-0" />
                  <span className="text-xs font-bold uppercase tracking-wider truncate">Yakalanılan Ofsayt</span>
                </div>
              </div>

              <div className="flex items-baseline gap-2 mb-2">
                <span className="text-3xl sm:text-4xl font-black tracking-tight font-mono text-slate-900">
                  {prediction.offsides?.expected_total || '3.3'}
                </span>
                <span className="text-xs font-semibold text-slate-500">beklenen ofsayt</span>
              </div>

              {/* Team split pill */}
              <div className="flex items-center justify-between text-xs text-slate-600 font-medium bg-slate-50 px-3 py-1.5 rounded-xl border border-slate-100 mb-4">
                <div className="flex items-center gap-1.5 truncate">
                  <span className="text-slate-500">{homeTeam.abbr || homeTeam.short}:</span>
                  <strong className="text-slate-900 font-mono font-bold">{prediction.offsides?.expected_home || '1.7'}</strong>
                </div>
                <span className="text-slate-300">•</span>
                <div className="flex items-center gap-1.5 truncate">
                  <span className="text-slate-500">{awayTeam.abbr || awayTeam.short}:</span>
                  <strong className="text-slate-900 font-mono font-bold">{prediction.offsides?.expected_away || '1.6'}</strong>
                </div>
              </div>
            </div>

            <div className="space-y-2.5 pt-3 border-t border-slate-100">
              <div>
                <div className="flex justify-between items-center text-xs mb-1">
                  <span className="text-slate-600 font-medium">3.5 Üst Olasılığı</span>
                  <span className="font-mono font-bold text-slate-700 bg-slate-100 px-1.5 py-0.5 rounded text-[11px]">
                    %{prediction.offsides?.prob_over_3_5_pct || '45.0'}
                  </span>
                </div>
                <div className="h-1.5 rounded-full bg-slate-100 overflow-hidden">
                  <div 
                    style={{ width: `${Math.min(100, Math.max(0, prediction.offsides?.prob_over_3_5_pct || 45))}%` }}
                    className="h-full bg-slate-700 rounded-full"
                  />
                </div>
              </div>

              <div className="flex items-center justify-between text-xs p-2.5 rounded-xl bg-slate-50 border border-slate-100 gap-2">
                <span className="text-slate-500 font-medium shrink-0">Taktiksel Çizgi</span>
                <span className="font-bold text-slate-700 truncate text-right">
                  {(prediction.offsides?.expected_total || 3.3) >= 3.6 ? 'Yüksek Hat / Tuzak' : 'Derin Blok Savunma'}
                </span>
              </div>
            </div>
          </div>

          {/* Cards & discipline */}
          <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm hover:border-slate-300 transition-all flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between gap-2 mb-3">
                <div className="flex items-center gap-2 text-slate-600 min-w-0">
                  <CreditCard className="w-4 h-4 shrink-0" />
                  <span className="text-xs font-bold uppercase tracking-wider truncate">Kartlar & Disiplin</span>
                </div>
              </div>

              <div className="flex items-baseline gap-2 mb-2">
                <span className="text-3xl sm:text-4xl font-black tracking-tight font-mono text-slate-900">
                  {prediction.cards?.expected_total || '4.2'}
                </span>
                <span className="text-xs font-semibold text-slate-500">beklenen kart</span>
              </div>

              {/* Team split pill */}
              <div className="flex items-center justify-between text-xs text-slate-600 font-medium bg-slate-50 px-3 py-1.5 rounded-xl border border-slate-100 mb-4">
                <div className="flex items-center gap-1.5 truncate">
                  <span className="text-slate-500">{homeTeam.abbr || homeTeam.short}:</span>
                  <strong className="text-slate-900 font-mono font-bold">{prediction.cards?.expected_home || '2.1'}</strong>
                </div>
                <span className="text-slate-300">•</span>
                <div className="flex items-center gap-1.5 truncate">
                  <span className="text-slate-500">{awayTeam.abbr || awayTeam.short}:</span>
                  <strong className="text-slate-900 font-mono font-bold">{prediction.cards?.expected_away || '2.1'}</strong>
                </div>
              </div>
            </div>

            <div className="space-y-2.5 pt-3 border-t border-slate-100">
              <div>
                <div className="flex justify-between items-center text-xs mb-1">
                  <span className="text-slate-600 font-medium">3.5 Üst Olasılığı</span>
                  <span className="font-mono font-bold text-slate-700 bg-slate-100 px-1.5 py-0.5 rounded text-[11px]">
                    %{prediction.cards?.prob_over_3_5_pct || '62.0'}
                  </span>
                </div>
                <div className="h-1.5 rounded-full bg-slate-100 overflow-hidden">
                  <div 
                    style={{ width: `${Math.min(100, Math.max(0, prediction.cards?.prob_over_3_5_pct || 62))}%` }}
                    className="h-full bg-slate-700 rounded-full"
                  />
                </div>
              </div>

              <div className="flex items-center justify-between text-xs p-2.5 rounded-xl bg-slate-50 border border-slate-100 gap-2">
                <span className="text-slate-500 font-medium shrink-0 flex items-center gap-1">
                  <Scale className="w-3.5 h-3.5 text-slate-400" />
                  <span>Hakem:</span>
                </span>
                <span className="font-bold text-slate-800 truncate text-right">
                  {prediction.referee?.name || 'Premier League Hakem Heyeti'} ({prediction.referee?.avg_cards || '4.2'} k/m)
                </span>
              </div>
            </div>
          </div>

          {/* Expected goals and shots */}
          <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm hover:border-slate-300 transition-all flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between gap-2 mb-3">
                <div className="flex items-center gap-2 text-slate-600 min-w-0">
                  <Target className="w-4 h-4 shrink-0" />
                  <span className="text-xs font-bold uppercase tracking-wider truncate">Gol Tahmini · Şut İstatistikleri</span>
                </div>
              </div>

              <div className="flex items-baseline gap-2 mb-2">
                <span className="text-3xl sm:text-4xl font-black tracking-tight font-mono text-slate-900">
                  {prediction.xg?.expected_total || '2.90'}
                </span>
                <span className="text-xs font-semibold text-slate-500">tahmini gol · istatistik proxy'si</span>
              </div>

              {/* Team split pill */}
              <div className="flex items-center justify-between text-xs text-slate-600 font-medium bg-slate-50 px-3 py-1.5 rounded-xl border border-slate-100 mb-4">
                <div className="flex items-center gap-1.5 truncate">
                  <span className="text-slate-500">{homeTeam.abbr || homeTeam.short}:</span>
                  <strong className="text-slate-900 font-mono font-bold">{prediction.xg?.expected_home || '1.45'} gol</strong>
                </div>
                <span className="text-slate-300">•</span>
                <div className="flex items-center gap-1.5 truncate">
                  <span className="text-slate-500">{awayTeam.abbr || awayTeam.short}:</span>
                  <strong className="text-slate-900 font-mono font-bold">{prediction.xg?.expected_away || '1.45'} gol</strong>
                </div>
              </div>
            </div>

            <div className="space-y-2.5 pt-3 border-t border-slate-100">
              <div>
                <div className="flex justify-between items-center text-xs mb-1">
                  <span className="text-slate-600 font-medium">2.5 Gol Üst Olasılığı</span>
                  <span className="font-mono font-bold text-slate-700 bg-slate-100 px-1.5 py-0.5 rounded text-[11px]">
                    %{prediction.outcome.over_2_5_goals_pct}
                  </span>
                </div>
                <div className="h-1.5 rounded-full bg-slate-100 overflow-hidden">
                  <div 
                    style={{ width: `${Math.min(100, Math.max(0, prediction.outcome.over_2_5_goals_pct))}%` }}
                    className="h-full bg-slate-700 rounded-full"
                  />
                </div>
              </div>

              <div className="flex items-center justify-between text-xs p-2.5 rounded-xl bg-slate-50 border border-slate-100 gap-2">
                <span className="text-slate-500 font-medium shrink-0">Şut Beklentisi</span>
                <span className="font-mono font-bold text-slate-800 truncate text-right">
                  {prediction.shots.expected_total} Toplam Şut (~9 isabet)
                </span>
              </div>
            </div>
          </div>

        </div>
      )}

    </div>
  );
}
