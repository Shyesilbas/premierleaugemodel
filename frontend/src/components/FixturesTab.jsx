import React, { useState, useEffect, useMemo } from 'react';
import { 
  Search, 
  Calendar, 
  ChevronRight, 
  ChevronLeft,
  Layers, 
  Clock, 
  MapPin, 
  Activity, 
  Target, 
  Flag, 
  Shield,
  Compass,
  Trophy,
  TrendingUp,
  Sparkles,
  RefreshCw,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';
import { getTeam } from '../data/teams';
import MatchDetailModal from './MatchDetailModal';

export default function FixturesTab({ selectedSeason, setSelectedSeason }) {
  const [data, setData] = useState({ gameweeks: [], total_matches: 0, current_gameweek: 6 });
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [currentGameweek, setCurrentGameweek] = useState(6);
  const [selectedGameweek, setSelectedGameweek] = useState('6'); // Default to current gameweek
  const [activeModalMatch, setActiveModalMatch] = useState(null);
  const [teamManagers, setTeamManagers] = useState({});
  const [syncStatus, setSyncStatus] = useState('idle');
  const [syncMessage, setSyncMessage] = useState('');
  const [dataRefreshVersion, setDataRefreshVersion] = useState(0);

  // Standings View State
  const [activeView, setActiveView] = useState('fixtures'); // 'fixtures' | 'table'
  const [standingsData, setStandingsData] = useState([]);
  const [loadingStandings, setLoadingStandings] = useState(false);
  const [standingsType, setStandingsType] = useState('all'); // 'all' | 'home' | 'away'

  useEffect(() => {
    setLoading(true);
    const seasonParam = selectedSeason || '2025_26';
    fetch(`/api/fixtures/grouped?season=${seasonParam}`)
      .then(res => res.json())
      .then(resData => {
        const curGw = resData?.current_gameweek || (resData?.gameweeks?.length ? resData.gameweeks[0].gameweek : 1);
        setData(resData || { gameweeks: [], total_matches: 0 });
        setCurrentGameweek(curGw);
        setSelectedGameweek(String(curGw));
        setLoading(false);
      })
      .catch(err => {
        console.error('Error fetching grouped fixtures:', err);
        setLoading(false);
      });
  }, [selectedSeason, dataRefreshVersion]);

  useEffect(() => {
    const seasonParam = selectedSeason || '2025_26';
    fetch(`/api/teams/staff?season=${seasonParam}`)
      .then(res => res.ok ? res.json() : { managers: {} })
      .then(data => setTeamManagers(data.managers || {}))
      .catch(err => {
        console.error('Error fetching team managers:', err);
        setTeamManagers({});
      });
  }, [selectedSeason]);

  // Fetch Standings data on season change
  useEffect(() => {
    setLoadingStandings(true);
    const seasonParam = selectedSeason || '2025_26';
    fetch(`/api/standings?season=${seasonParam}`)
      .then(res => res.json())
      .then(resData => {
        setStandingsData(resData?.standings || []);
        setLoadingStandings(false);
      })
      .catch(err => {
        console.error('Error fetching standings:', err);
        setLoadingStandings(false);
      });
  }, [selectedSeason, dataRefreshVersion]);

  useEffect(() => {
    if (syncStatus !== 'running') return undefined;
    let cancelled = false;
    let timer;
    const pollStatus = async () => {
      try {
        const response = await fetch('/api/admin/sync-season');
        if (!response.ok) throw new Error('Güncelleme durumu alınamadı.');
        const job = await response.json();
        if (cancelled) return;
        if (job.status === 'completed') {
          setSyncStatus('completed');
          setSyncMessage(job.message || 'Veriler güncellendi.');
          setDataRefreshVersion(version => version + 1);
          return;
        }
        if (job.status === 'failed') {
          setSyncStatus('failed');
          setSyncMessage(job.message || 'Veri güncellemesi tamamlanamadı.');
          return;
        }
        timer = setTimeout(pollStatus, 2000);
      } catch (error) {
        if (cancelled) return;
        setSyncStatus('failed');
        setSyncMessage(error.message || 'Güncelleme durumu alınamadı.');
      }
    };
    pollStatus();
    return () => { cancelled = true; clearTimeout(timer); };
  }, [syncStatus]);

  const triggerSeasonSync = async () => {
    setSyncStatus('starting');
    setSyncMessage('Sezon fikstürü kontrol ediliyor...');
    try {
      const season = selectedSeason && selectedSeason !== 'all' ? selectedSeason : '2026_27';
      const response = await fetch(`/api/admin/sync-season?season=${encodeURIComponent(season)}`, { method: 'POST' });
      const job = await response.json();
      if (!response.ok) throw new Error(job.detail || job.message || 'Güncelleme başlatılamadı.');
      setSyncStatus(job.status === 'completed' ? 'completed' : 'running');
      setSyncMessage(job.message || (job.already_running ? 'Başka bir güncelleme devam ediyor...' : 'Sezon verileri kontrol ediliyor...'));
    } catch (error) {
      setSyncStatus('failed');
      setSyncMessage(error.message || 'Güncelleme başlatılamadı.');
    }
  };

  // Sorted standings based on overall/home/away
  const displayedStandings = useMemo(() => {
    if (!standingsData.length) return [];
    if (standingsType === 'all') return standingsData;

    return [...standingsData].sort((a, b) => {
      const aData = a[standingsType] || a;
      const bData = b[standingsType] || b;
      if (bData.points !== aData.points) return bData.points - aData.points;
      if (bData.gd !== aData.gd) return bData.gd - aData.gd;
      return bData.gf - aData.gf;
    });
  }, [standingsData, standingsType]);

  const teamForms = useMemo(() => new Map(
    standingsData.map(team => [Number(team.id), team.form || []])
  ), [standingsData]);

  const renderTeamForm = (teamId) => (teamForms.get(Number(teamId)) || []).map((result, index) => {
    const colors = result === 'W'
      ? 'bg-emerald-500 text-white'
      : result === 'D'
      ? 'bg-slate-400 text-white'
      : 'bg-rose-500 text-white';
    const label = result === 'W' ? 'G' : result === 'D' ? 'B' : 'M';

    return (
      <span
        key={`${teamId}-${index}`}
        className={`w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-black ${colors}`}
        title={result === 'W' ? 'Galibiyet' : result === 'D' ? 'Beraberlik' : 'Mağlubiyet'}
      >
        {label}
      </span>
    );
  });

  // Filter gameweeks and matches based on search and selectedGameweek
  const filteredGameweeks = useMemo(() => {
    if (!data.gameweeks) return [];

    return data.gameweeks
      .filter(gwObj => {
        if (selectedGameweek === 'all') return true;
        return String(gwObj.gameweek) === String(selectedGameweek);
      })
      .map(gwObj => {
        if (!search.trim()) return gwObj;
        const q = search.toLowerCase();

        const filteredDays = gwObj.days
          .map(dayObj => {
            const matchedMatches = dayObj.matches.filter(m => 
              (m.home_name && m.home_name.toLowerCase().includes(q)) ||
              (m.away_name && m.away_name.toLowerCase().includes(q)) ||
              (m.ground_name && m.ground_name.toLowerCase().includes(q))
            );
            return { ...dayObj, matches: matchedMatches };
          })
          .filter(dayObj => dayObj.matches.length > 0);

        return { ...gwObj, days: filteredDays };
      })
      .filter(gwObj => gwObj.days.length > 0);
  }, [data.gameweeks, selectedGameweek, search]);

  const allGwNumbers = (data.gameweeks || []).map(g => g.gameweek);

  return (
    <div className="space-y-6">
      
      {/* Top Banner & Season Info */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-sm space-y-4">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              {activeView === 'fixtures' ? (
                <Calendar className="w-5 h-5 text-[#38003c]" />
              ) : (
                <Trophy className="w-5 h-5 text-amber-500" />
              )}
              <h2 className="text-lg font-black text-slate-900 tracking-tight">
                {activeView === 'fixtures' ? 'Premier League Fikstürü' : 'Premier League Puan Tablosu'}
              </h2>
              <span className="text-xs font-mono font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
                {selectedSeason === '2026_27' ? '2026-27 (Güncel Sezon)' : selectedSeason.replace('_', '-')}
              </span>
            </div>
            <p className="text-xs text-slate-500 font-medium">
              {activeView === 'fixtures' 
                ? 'Hafta hafta ve günlere ayrılmış fikstür akışı. Maç kartına tıklayarak kadroları ve detayları inceleyebilirsiniz.' 
                : 'Canlı puan durumu, averajlar, iç/dış saha performansı ve son 5 maç formu.'}
            </p>
          </div>

          {/* Season Quick Toggle */}
          <div className="flex flex-col items-stretch gap-2 self-stretch md:items-end md:self-auto">
          <div className="flex items-center bg-slate-100 p-1 rounded-xl border border-slate-200 gap-1 justify-center">
            <button
              onClick={() => setSelectedSeason('2026_27')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                selectedSeason === '2026_27'
                  ? 'bg-[#38003c] text-white shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              2026-27 (Güncel)
            </button>
            <button
              onClick={() => setSelectedSeason('2025_26')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                selectedSeason === '2025_26'
                  ? 'bg-[#38003c] text-white shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              2025-26
            </button>
            <button
              onClick={() => setSelectedSeason('2024_25')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                selectedSeason === '2024_25'
                  ? 'bg-[#38003c] text-white shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              2024-25
            </button>
            <button
              onClick={() => setSelectedSeason('2023_24')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                selectedSeason === '2023_24'
                  ? 'bg-[#38003c] text-white shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              2023-24
            </button>
            <button
              onClick={() => setSelectedSeason('2022_23')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                selectedSeason === '2022_23'
                  ? 'bg-[#38003c] text-white shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              2022-23
            </button>
          </div>
          <div className="flex flex-col items-end gap-1.5">
            <button
              type="button"
              onClick={triggerSeasonSync}
              disabled={syncStatus === 'starting' || syncStatus === 'running'}
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-violet-200 bg-violet-50 px-3.5 py-2 text-xs font-bold text-violet-900 transition hover:border-violet-300 hover:bg-violet-100 disabled:cursor-wait disabled:opacity-70"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${syncStatus === 'starting' || syncStatus === 'running' ? 'animate-spin' : ''}`} />
              {syncStatus === 'starting' || syncStatus === 'running' ? 'Veriler eşitleniyor…' : 'Sezon verisini eşitle'}
            </button>
            {syncMessage && <p className={`flex items-center gap-1 text-[10px] ${syncStatus === 'failed' ? 'text-rose-700' : syncStatus === 'completed' ? 'text-emerald-700' : 'text-slate-500'}`}>
              {syncStatus === 'completed' && <CheckCircle2 className="h-3 w-3" />}
              {syncStatus === 'failed' && <AlertCircle className="h-3 w-3" />}
              <span>{syncMessage}</span>
            </p>}
          </div>
          </div>
        </div>

        {/* View Mode Switcher: Fikstür vs Puan Tablosu */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-3 border-t border-slate-100">
          <div className="flex items-center bg-slate-100 p-1 rounded-xl border border-slate-200 gap-1">
            <button
              onClick={() => setActiveView('fixtures')}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                activeView === 'fixtures'
                  ? 'bg-[#38003c] text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Calendar className="w-3.5 h-3.5" />
              <span>Maç Fikstürü</span>
            </button>
            <button
              onClick={() => setActiveView('table')}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                activeView === 'table'
                  ? 'bg-[#38003c] text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Trophy className="w-3.5 h-3.5 text-amber-500" />
              <span>Puan Tablosu</span>
            </button>
          </div>

          {activeView === 'table' && (
            <div className="flex items-center gap-2.5 text-[11px] font-medium text-slate-500">
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-xs bg-blue-500" />
                <span>UCL (1-4)</span>
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-xs bg-orange-500" />
                <span>UEL (5)</span>
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-xs bg-rose-500" />
                <span>Düşme (18-20)</span>
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Conditional View: Puan Tablosu vs Fikstür */}
      {activeView === 'table' ? (
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-4">
          {/* Table Header: Title + Overall/Home/Away toggle */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <Trophy className="w-5 h-5 text-amber-500" />
              <div>
                <h3 className="text-sm font-black text-slate-900">
                  Premier League Puan Durumu
                </h3>
                <p className="text-[11px] text-slate-500">
                  {selectedSeason === '2026_27' ? '2026-27 Güncel Sezon Sıralaması' : `${selectedSeason.replace('_', '-')} Sezon Sonu Tablosu`}
                </p>
              </div>
            </div>

            {/* Genel / İç Saha / Deplasman Filtresi */}
            <div className="flex items-center bg-slate-100 p-1 rounded-xl border border-slate-200 gap-1 self-stretch sm:self-auto justify-center">
              <button
                onClick={() => setStandingsType('all')}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  standingsType === 'all'
                    ? 'bg-[#38003c] text-white shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Genel
              </button>
              <button
                onClick={() => setStandingsType('home')}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  standingsType === 'home'
                    ? 'bg-[#38003c] text-white shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                İç Saha
              </button>
              <button
                onClick={() => setStandingsType('away')}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  standingsType === 'away'
                    ? 'bg-[#38003c] text-white shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Deplasman
              </button>
            </div>
          </div>

          {/* Table Content */}
          {loadingStandings ? (
            <div className="py-20 text-center">
              <div className="w-8 h-8 border-3 border-[#38003c] border-t-transparent rounded-full animate-spin mx-auto mb-3" />
              <p className="text-xs font-bold text-slate-700">Puan tablosu hesaplanıyor...</p>
            </div>
          ) : displayedStandings.length === 0 ? (
            <div className="py-12 text-center text-xs text-slate-500">
              Puan tablosu verisi bulunamadı.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider bg-slate-50/50">
                    <th className="py-2.5 px-3 w-12 text-center">#</th>
                    <th className="py-2.5 px-3 min-w-[180px]">Kulüp</th>
                    <th className="py-2.5 px-2 text-center w-10" title="Oynanan Maç">O</th>
                    <th className="py-2.5 px-2 text-center w-10" title="Galibiyet">G</th>
                    <th className="py-2.5 px-2 text-center w-10" title="Beraberlik">B</th>
                    <th className="py-2.5 px-2 text-center w-10" title="Mağlubiyet">M</th>
                    <th className="py-2.5 px-2 text-center w-12 hidden md:table-cell" title="Attığı Gol">AG</th>
                    <th className="py-2.5 px-2 text-center w-12 hidden md:table-cell" title="Yediği Gol">YG</th>
                    <th className="py-2.5 px-2 text-center w-12" title="Averaj">AV</th>
                    <th className="py-2.5 px-3 text-center w-14 font-black text-slate-900" title="Puan">P</th>
                    <th className="py-2.5 px-3 text-center w-36 hidden sm:table-cell" title="Son 5 Maç">Form</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono">
                  {displayedStandings.map((t, idx) => {
                    const rank = idx + 1;
                    const stats = standingsType === 'all' ? t : (t[standingsType] || t);
                    const isUcl = rank <= 4;
                    const isUel = rank === 5;
                    const isRelegation = rank >= 18;

                    const borderClass = isUcl 
                      ? 'border-l-4 border-l-blue-500' 
                      : isUel 
                      ? 'border-l-4 border-l-orange-500' 
                      : isRelegation 
                      ? 'border-l-4 border-l-rose-500' 
                      : 'border-l-4 border-l-transparent';

                    const gdFormatted = stats.gd > 0 ? `+${stats.gd}` : `${stats.gd}`;

                    return (
                      <tr 
                        key={t.id}
                        className={`hover:bg-slate-50 transition-colors ${borderClass}`}
                      >
                        <td className="py-2.5 px-3 text-center font-bold text-slate-700">
                          <span className={`inline-flex items-center justify-center w-6 h-6 rounded-md text-[11px] font-black ${
                            rank === 1 ? 'bg-amber-100 text-amber-900 border border-amber-300' : 'text-slate-600'
                          }`}>
                            {rank}
                          </span>
                        </td>

                        <td className="py-2.5 px-3 font-sans">
                          <div className="flex items-center gap-2.5">
                            <img 
                              src={t.badge} 
                              alt={t.name} 
                              className="w-5 h-5 object-contain shrink-0"
                              onError={(e) => { e.target.src = '/badges/1.svg'; }}
                            />
                            <span className="font-bold text-slate-900 truncate">
                              {t.name}
                            </span>
                            {t.abbr && (
                              <span className="text-[10px] font-mono font-bold text-slate-400 hidden lg:inline">
                                {t.abbr}
                              </span>
                            )}
                          </div>
                        </td>

                        <td className="py-2.5 px-2 text-center font-semibold text-slate-800">{stats.played}</td>
                        <td className="py-2.5 px-2 text-center text-slate-600">{stats.won}</td>
                        <td className="py-2.5 px-2 text-center text-slate-600">{stats.drawn}</td>
                        <td className="py-2.5 px-2 text-center text-slate-600">{stats.lost}</td>

                        <td className="py-2.5 px-2 text-center text-slate-500 hidden md:table-cell">{stats.gf}</td>
                        <td className="py-2.5 px-2 text-center text-slate-500 hidden md:table-cell">{stats.ga}</td>

                        <td className={`py-2.5 px-2 text-center font-bold ${
                          stats.gd > 0 ? 'text-emerald-700' : stats.gd < 0 ? 'text-rose-700' : 'text-slate-500'
                        }`}>
                          {gdFormatted}
                        </td>

                        <td className="py-2.5 px-3 text-center">
                          <span className="inline-block px-2 py-0.5 rounded-md bg-slate-900 text-white font-black text-xs">
                            {stats.points}
                          </span>
                        </td>

                        <td className="py-2.5 px-3 text-center hidden sm:table-cell">
                          <div className="flex items-center justify-center gap-1">
                            {(t.form || []).map((res, fIdx) => {
                              const bg = res === 'W' 
                                ? 'bg-emerald-500 text-white' 
                                : res === 'D' 
                                ? 'bg-slate-400 text-white' 
                                : 'bg-rose-500 text-white';
                              const label = res === 'W' ? 'G' : res === 'D' ? 'B' : 'M';
                              return (
                                <span
                                  key={fIdx}
                                  className={`w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-black ${bg}`}
                                  title={res === 'W' ? 'Galibiyet' : res === 'D' ? 'Beraberlik' : 'Mağlubiyet'}
                                >
                                  {label}
                                </span>
                              );
                            })}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* Legend Footer */}
          <div className="pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3 text-[11px] text-slate-500 font-medium">
            <div className="flex flex-wrap items-center gap-4">
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-xs bg-blue-500" />
                <span>Şampiyonlar Ligi (1-4)</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-xs bg-orange-500" />
                <span>Avrupa Ligi (5)</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-xs bg-rose-500" />
                <span>Küme Düşme Hattı (18-20)</span>
              </div>
            </div>
            <div className="font-mono text-[10px] text-slate-400">
              O: Oynanan • G: Galibiyet • B: Beraberlik • M: Mağlubiyet • AV: Averaj • P: Puan
            </div>
          </div>
        </div>
      ) : (
        <>
          {/* Filter and Search Bar */}
          <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm flex flex-col gap-4">
        
        {/* Search Input */}
        <div className="relative w-full">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Takım veya stadyum ara (örn: Arsenal, Anfield, Chelsea)..."
            className="w-full bg-slate-50 border border-slate-200 rounded-xl pl-10 pr-4 py-2.5 text-xs font-medium text-slate-900 placeholder-slate-400 outline-none focus:border-[#38003c] focus:bg-white transition-all"
          />
        </div>

        {/* Navigation Controls & Gameweek Selector */}
        <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3 pt-2 border-t border-slate-100">
          
          {/* Quick Prev / Next Step Buttons */}
          <div className="flex items-center gap-1.5 shrink-0">
            <button
              onClick={() => {
                const currentNum = selectedGameweek === 'all' ? currentGameweek : Number(selectedGameweek);
                const prev = Math.max(1, currentNum - 1);
                setSelectedGameweek(String(prev));
              }}
              disabled={selectedGameweek !== 'all' && Number(selectedGameweek) <= 1}
              className="flex items-center gap-1 px-3 py-1.5 rounded-xl text-xs font-bold bg-slate-100 text-slate-700 hover:bg-slate-200 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
              <span>Önceki Hafta</span>
            </button>

            <button
              onClick={() => setSelectedGameweek(String(currentGameweek))}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${
                String(selectedGameweek) === String(currentGameweek)
                  ? 'bg-emerald-600 text-white shadow-xs'
                  : 'bg-emerald-50 text-emerald-800 border border-emerald-200 hover:bg-emerald-100'
              }`}
              title="Mevcut oynanan / yaklaşan haftaya git"
            >
              <span className={`w-2 h-2 rounded-full ${String(selectedGameweek) === String(currentGameweek) ? 'bg-white' : 'bg-emerald-500 animate-pulse'}`} />
              <span>Mevcut Hafta ({currentGameweek})</span>
            </button>

            <button
              onClick={() => {
                const currentNum = selectedGameweek === 'all' ? currentGameweek : Number(selectedGameweek);
                const maxGw = allGwNumbers.length ? Math.max(...allGwNumbers) : 38;
                const next = Math.min(maxGw, currentNum + 1);
                setSelectedGameweek(String(next));
              }}
              disabled={selectedGameweek !== 'all' && Number(selectedGameweek) >= (allGwNumbers.length ? Math.max(...allGwNumbers) : 38)}
              className="flex items-center gap-1 px-3 py-1.5 rounded-xl text-xs font-bold bg-slate-100 text-slate-700 hover:bg-slate-200 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
            >
              <span>Sonraki Hafta</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Gameweek Horizontal Selector */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 pt-1 scrollbar-thin">
            <button
              onClick={() => setSelectedGameweek('all')}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all whitespace-nowrap ${
                selectedGameweek === 'all'
                  ? 'bg-[#38003c] text-white shadow-sm'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              Tüm Haftalar
            </button>
            {allGwNumbers.map(gw => {
              const isSelected = String(selectedGameweek) === String(gw);
              const isCurrent = Number(gw) === Number(currentGameweek);
              return (
                <button
                  key={gw}
                  onClick={() => setSelectedGameweek(String(gw))}
                  className={`px-3 py-1.5 rounded-xl text-xs font-mono font-bold transition-all whitespace-nowrap flex items-center gap-1.5 ${
                    isSelected
                      ? 'bg-[#38003c] text-white shadow-sm'
                      : isCurrent
                      ? 'bg-emerald-50 text-emerald-800 border border-emerald-300 hover:bg-emerald-100'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200 hover:text-slate-900'
                  }`}
                >
                  <span>Hafta {gw}</span>
                  {isCurrent && (
                    <span className={`text-[9px] px-1.5 py-0.2 rounded font-sans font-bold uppercase tracking-wider ${
                      isSelected ? 'bg-emerald-500 text-white' : 'bg-emerald-200 text-emerald-900'
                    }`}>
                      Mevcut
                    </span>
                  )}
                </button>
              );
            })}
          </div>

        </div>

      </div>

      {/* Gameweeks & Days Grouped View */}
      {loading ? (
        <div className="py-20 text-center bg-white border border-slate-200 rounded-2xl shadow-sm">
          <div className="w-8 h-8 border-3 border-[#38003c] border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-xs font-bold text-slate-700">Fikstür ve maç verileri yükleniyor...</p>
        </div>
      ) : filteredGameweeks.length === 0 ? (
        <div className="py-16 text-center bg-white border border-slate-200 rounded-2xl shadow-sm">
          <p className="text-sm font-bold text-slate-800">Aramanızla eşleşen maç bulunamadı.</p>
          <p className="text-xs text-slate-500 mt-1">Filtreleri temizleyip tekrar deneyin.</p>
        </div>
      ) : (
        <div className="space-y-8">
          {filteredGameweeks.map(gwObj => (
            <div key={gwObj.gameweek} className="space-y-4">
              
              {/* Gameweek Badge Header */}
              <div className="flex items-center justify-between bg-slate-200/70 border border-slate-300/80 px-4 py-2.5 rounded-xl">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#38003c]" />
                  <h3 className="text-sm font-black text-slate-900 tracking-tight">
                    Hafta {gwObj.gameweek}
                  </h3>
                </div>
                <span className="text-[11px] font-mono font-bold text-slate-600">
                  {gwObj.days.reduce((acc, d) => acc + d.matches.length, 0)} Karşılaşma
                </span>
              </div>

              {/* Day Groups inside Gameweek */}
              <div className="space-y-5 pl-1 md:pl-2">
                {gwObj.days.map((dayObj, dayIdx) => (
                  <div key={dayIdx} className="space-y-2.5">
                    
                    {/* Day Subheader */}
                    <div className="flex items-center gap-2 text-xs font-bold text-slate-700 px-1">
                      <Calendar className="w-3.5 h-3.5 text-[#38003c]" />
                      <span>{dayObj.day}</span>
                    </div>

                    {/* Matches Grid for that Day */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-3.5">
                      {dayObj.matches.map(m => {
                        const home = getTeam(m.home_id, m.home_name);
                        const away = getTeam(m.away_id, m.away_name);
                        const homeManager = teamManagers[String(m.home_id)];
                        const awayManager = teamManagers[String(m.away_id)];
                        const isCompleted = m.status === 'COMPLETED' && m.home_score !== null;

                        return (
                          <div
                            key={m.match_id}
                            onClick={() => setActiveModalMatch(m)}
                            className="bg-white border border-slate-200 hover:border-slate-400 rounded-2xl p-4 shadow-sm hover:shadow-md transition-all duration-200 cursor-pointer group flex flex-col justify-between gap-3"
                          >
                            
                            {/* Top Card Bar: Kickoff time & Ground */}
                            <div className="flex items-center justify-between text-[11px] text-slate-500 pb-2 border-b border-slate-100">
                              <div className="flex items-center gap-1.5 font-medium truncate max-w-[200px]">
                                <Clock className="w-3 h-3 text-slate-400 shrink-0" />
                                <span className="truncate">{m.time_label || m.kickoff_label}</span>
                              </div>

                              <span className="text-[11px] font-bold text-[#38003c] group-hover:translate-x-0.5 transition-transform flex items-center gap-1">
                                {isCompleted ? 'Kadrolar & Detay' : 'Model Maç Tahmini'} <ChevronRight className="w-3.5 h-3.5" />
                              </span>
                            </div>

                            {/* Teams & Score / Time */}
                            <div className="flex items-center justify-between gap-2 py-1">
                              
                              {/* Home Team */}
                              <div className="flex items-center gap-2.5 flex-1 min-w-0">
                                <img 
                                  src={home.badge} 
                                  alt={home.name} 
                                  className="w-7 h-7 object-contain shrink-0"
                                  onError={(e) => { e.target.src = '/badges/1.svg'; }}
                                />
                                <span className="font-bold text-xs text-slate-900 group-hover:text-[#38003c] transition-colors truncate">
                                  {home.name}
                                </span>
                              </div>

                              {/* Center: Score or Kickoff Time */}
                              <div className="shrink-0 px-3 py-1 rounded-xl bg-slate-100 border border-slate-200 font-mono font-black text-sm text-slate-900 text-center min-w-[64px]">
                                {isCompleted ? (
                                  <span>{m.home_score} - {m.away_score}</span>
                                ) : (
                                  <span className="text-xs font-bold text-slate-600">VS</span>
                                )}
                              </div>

                              {/* Away Team */}
                              <div className="flex items-center gap-2.5 flex-1 min-w-0 justify-end text-right">
                                <span className="font-bold text-xs text-slate-900 group-hover:text-[#38003c] transition-colors truncate">
                                  {away.name}
                                </span>
                                <img 
                                  src={away.badge} 
                                  alt={away.name} 
                                  className="w-7 h-7 object-contain shrink-0"
                                  onError={(e) => { e.target.src = '/badges/1.svg'; }}
                                />
                              </div>

                            </div>

                            {(homeManager || awayManager) && (
                              <div className="grid grid-cols-2 gap-2 text-[10px] text-slate-500">
                                <span className="truncate" title={homeManager ? `Teknik Direktör: ${homeManager}` : undefined}>
                                  {homeManager ? <><span className="text-slate-400">TD:</span> <strong className="font-semibold text-slate-700">{homeManager}</strong></> : ''}
                                </span>
                                <span className="truncate text-right" title={awayManager ? `Teknik Direktör: ${awayManager}` : undefined}>
                                  {awayManager ? <><span className="text-slate-400">TD:</span> <strong className="font-semibold text-slate-700">{awayManager}</strong></> : ''}
                                </span>
                              </div>
                            )}

                            {/* Recent form, using the same W/D/L markers as the standings table */}
                            <div className="flex items-center justify-between gap-2 text-[9px] text-slate-400">
                              <div className="flex items-center gap-1" aria-label={`${home.name} son 5 maç formu`}>
                                {renderTeamForm(m.home_id)}
                              </div>
                              <span className="shrink-0 font-bold tracking-wide">SON 5</span>
                              <div className="flex items-center gap-1" aria-label={`${away.name} son 5 maç formu`}>
                                {renderTeamForm(m.away_id)}
                              </div>
                            </div>

                            {/* Bottom Bar: Completed Micro-stats OR Ground/Status */}
                            {isCompleted ? (
                              <div className="pt-2 border-t border-slate-100 space-y-1.5">
                                <div className="flex items-center justify-between text-[11px] text-slate-500">
                                  <span className="flex items-center gap-1 truncate text-slate-600">
                                    <span className="text-slate-400">👨‍⚖️ Hakem:</span>
                                    <strong className="text-slate-800 font-semibold truncate">{m.referee_name || 'Bilinmiyor'}</strong>
                                  </span>
                                  {m.total_yellow_cards !== null && m.total_yellow_cards !== undefined ? (
                                    <div className="flex items-center gap-1 shrink-0 font-mono text-[10px]">
                                      <span className="px-1.5 py-0.5 rounded bg-amber-50 border border-amber-200 text-amber-900 font-bold">
                                        {m.total_yellow_cards} 🟨
                                      </span>
                                      {m.total_red_cards > 0 && (
                                        <span className="px-1.5 py-0.5 rounded bg-rose-50 border border-rose-200 text-rose-900 font-bold">
                                          {m.total_red_cards} 🟥
                                        </span>
                                      )}
                                    </div>
                                  ) : (
                                    <span className="text-[10px] text-slate-400 font-mono">
                                      {m.ref_avg_cards ? `Ort. ${m.ref_avg_cards} Kart` : ''}
                                    </span>
                                  )}
                                </div>

                                <div className="grid grid-cols-4 gap-1.5 text-[10px] font-mono text-center">
                                  <div className="bg-slate-50 py-1 px-1 rounded-lg">
                                    <span className="text-[9px] text-slate-500 font-sans block">KORNER</span>
                                    <strong className="text-emerald-700 font-bold">{m.home_won_corners ?? '-'} - {m.away_won_corners ?? '-'}</strong>
                                  </div>
                                  <div className="bg-slate-50 py-1 px-1 rounded-lg">
                                    <span className="text-[9px] text-slate-500 font-sans block">TAÇ</span>
                                    <strong className="text-sky-700 font-bold">{m.home_total_throws ?? '-'} - {m.away_total_throws ?? '-'}</strong>
                                  </div>
                                  <div className="bg-slate-50 py-1 px-1 rounded-lg">
                                    <span className="text-[9px] text-slate-500 font-sans block">ŞUT</span>
                                    <strong className="text-slate-800 font-bold">{m.home_total_shots ?? '-'} - {m.away_total_shots ?? '-'}</strong>
                                  </div>
                                  <div className="bg-slate-50 py-1 px-1 rounded-lg">
                                    <span className="text-[9px] text-slate-500 font-sans block">KURTARIŞ</span>
                                    <strong className="text-purple-700 font-bold">{m.total_saves ?? '-'}</strong>
                                  </div>
                                </div>
                              </div>
                            ) : (
                              <div className="pt-2 border-t border-slate-100 space-y-1.5">
                                <div className="flex items-center justify-between text-[11px] text-slate-500 gap-2">
                                  <span className="flex items-center gap-1 truncate text-slate-400">
                                    <MapPin className="w-3 h-3 shrink-0" />
                                    <span className="truncate">{m.ground_name || 'Premier League Stadı'}</span>
                                  </span>
                                  {m.prediction?.favorite_label ? (
                                    <span className="text-[10px] font-bold text-[#38003c] bg-purple-50 border border-purple-200 px-2 py-0.5 rounded-md shrink-0 flex items-center gap-1">
                                      <Sparkles className="w-2.5 h-2.5 text-purple-600" />
                                      {m.prediction.favorite_label}
                                    </span>
                                  ) : (
                                    <span className="text-[10px] font-bold text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-md shrink-0">
                                      Yaklaşan Maç
                                    </span>
                                  )}
                                </div>

                                <div className="flex items-center justify-between text-[10px] text-slate-600 bg-slate-50/70 border border-slate-100 px-2 py-1 rounded-lg">
                                  <span className="flex items-center gap-1 truncate">
                                    <span className="text-slate-400">👨‍⚖️ Hakem:</span>
                                    <strong className="text-slate-800 font-semibold truncate">
                                      {m.referee_name && m.referee_name !== 'Atanmadı' && m.referee_name !== 'Unknown' 
                                        ? m.referee_name 
                                        : (m.prediction?.referee_name && m.prediction.referee_name !== 'Unknown' ? m.prediction.referee_name : 'PGMOL Heyeti')}
                                    </strong>
                                  </span>
                                  <span className="text-amber-800 font-mono font-bold shrink-0">
                                    Ort. {m.ref_avg_cards || m.prediction?.expected_cards || '4.2'} Kart/maç
                                  </span>
                                </div>

                                {m.prediction && (
                                  <div className="grid grid-cols-3 gap-1.5 text-[10px] font-mono text-center">
                                    <div className="bg-emerald-50/70 border border-emerald-100/80 py-1 px-1 rounded-lg">
                                      <span className="text-[8px] text-emerald-600 font-sans font-bold block">KORNER</span>
                                      <strong className="text-emerald-900 font-bold">~{m.prediction.expected_corners}</strong>
                                      {m.prediction.corners_model_skill === 'baseline' && (
                                        <span className="block text-[7px] leading-tight text-amber-700 font-sans font-semibold">Veri ortalaması</span>
                                      )}
                                    </div>
                                    <div className="bg-amber-50/70 border border-amber-100/80 py-1 px-1 rounded-lg">
                                      <span className="text-[8px] text-amber-600 font-sans font-bold block">KART (+3.5)</span>
                                      <strong className="text-amber-900 font-bold">%{m.prediction.prob_over_3_5_cards}</strong>
                                      {m.prediction.cards_model_skill === 'baseline' && (
                                        <span className="block text-[7px] leading-tight text-amber-700 font-sans font-semibold">Veri ortalaması</span>
                                      )}
                                    </div>
                                    <div className="bg-slate-50 border border-slate-200 py-1 px-1 rounded-lg">
                                      <span className="text-[8px] text-slate-500 font-sans font-bold block">2.5 ÜST GOL</span>
                                      <strong className="text-slate-800 font-bold">%{m.prediction.over_2_5_goals_pct}</strong>
                                      {m.prediction.over_2_5_source === 'baseline' && (
                                        <span className="block text-[7px] leading-tight text-amber-700 font-sans font-semibold">
                                          Taban oran (sinyal zayıf)
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                )}
                              </div>
                            )}

                          </div>
                        );
                      })}
                    </div>

                  </div>
                ))}
              </div>

            </div>
          ))}
        </div>
      )}
    </>
  )}

      {/* Match Detail & Lineup Modal */}
      {activeModalMatch && (
        <MatchDetailModal
          match={activeModalMatch}
          onClose={() => setActiveModalMatch(null)}
        />
      )}

    </div>
  );
}
