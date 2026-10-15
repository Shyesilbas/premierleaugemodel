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
  AlertCircle,
  List,
  LayoutGrid,
  ChevronDown
} from 'lucide-react';
import { getTeam } from '../data/teams';
import MatchDetailModal from './MatchDetailModal';
import { getCachedTeamData, setCachedTeamData, clearTeamCache } from '../utils/teamProfileCache';

export default function FixturesTab({ selectedSeason, setSelectedSeason, onSelectMatch, onSelectTeam }) {
  const [data, setData] = useState({ gameweeks: [], total_matches: 0, current_gameweek: 6 });
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [currentGameweek, setCurrentGameweek] = useState(6);
  const [selectedGameweek, setSelectedGameweek] = useState('6'); // Default to current gameweek
  const [isGameweekMenuOpen, setIsGameweekMenuOpen] = useState(false);
  const [activeModalMatch, setActiveModalMatch] = useState(null);
  const [teamManagers, setTeamManagers] = useState({});
  const [syncStatus, setSyncStatus] = useState('idle');
  const [syncMessage, setSyncMessage] = useState('');
  const [dataRefreshVersion, setDataRefreshVersion] = useState(0);

  // Display Mode: 'list' (Kompakt Liste) | 'cards' (Detaylı Kartlar)
  const [displayMode, setDisplayMode] = useState(() => {
    try {
      return localStorage.getItem('fixtures_display_mode') || 'list';
    } catch {
      return 'list';
    }
  });

  const handleDisplayModeChange = (mode) => {
    setDisplayMode(mode);
    try {
      localStorage.setItem('fixtures_display_mode', mode);
    } catch {}
  };

  // Standings View State
  const [activeView, setActiveView] = useState('fixtures'); // 'fixtures' | 'table'
  const [standingsData, setStandingsData] = useState([]);
  const [loadingStandings, setLoadingStandings] = useState(false);
  const [standingsType, setStandingsType] = useState('all'); // 'all' | 'home' | 'away'

  useEffect(() => {
    const seasonParam = selectedSeason || '2026_27';

    if (dataRefreshVersion === 0) {
      const cached = getCachedTeamData('fixtures_grouped', 'all', seasonParam);
      if (cached?.data) {
        const curGw = cached.data?.current_gameweek || (cached.data?.gameweeks?.length ? cached.data.gameweeks[0].gameweek : 1);
        setData(cached.data);
        setCurrentGameweek(curGw);
        setSelectedGameweek(String(curGw));
        setLoading(false);
        return;
      }
    }

    setLoading(true);
    fetch(`/api/fixtures/grouped?season=${seasonParam}`)
      .then(res => res.json())
      .then(resData => {
        const curGw = resData?.current_gameweek || (resData?.gameweeks?.length ? resData.gameweeks[0].gameweek : 1);
        setData(resData || { gameweeks: [], total_matches: 0 });
        setCurrentGameweek(curGw);
        setSelectedGameweek(String(curGw));
        const { expiresAt, label } = calculateTeamExpiry(resData?.next_match, seasonParam);
        setCachedTeamData('fixtures_grouped', 'all', seasonParam, resData, expiresAt, label);
        setLoading(false);
      })
      .catch(err => {
        console.error('Error fetching grouped fixtures:', err);
        setLoading(false);
      });
  }, [selectedSeason, dataRefreshVersion]);

  useEffect(() => {
    const seasonParam = selectedSeason || '2026_27';

    if (dataRefreshVersion === 0) {
      const cached = getCachedTeamData('staff', 'all', seasonParam);
      if (cached?.data) {
        setTeamManagers(cached.data.managers || {});
        return;
      }
    }

    fetch(`/api/teams/staff?season=${seasonParam}`)
      .then(res => res.ok ? res.json() : { managers: {} })
      .then(data => {
        setTeamManagers(data.managers || {});
        const { expiresAt, label } = calculateTeamExpiry(null, seasonParam);
        setCachedTeamData('staff', 'all', seasonParam, data, expiresAt, label);
      })
      .catch(err => {
        console.error('Error fetching team managers:', err);
        setTeamManagers({});
      });
  }, [selectedSeason, dataRefreshVersion]);

  // Fetch Standings data on season change
  useEffect(() => {
    const seasonParam = selectedSeason || '2026_27';

    if (dataRefreshVersion === 0) {
      const cached = getCachedTeamData('standings', 'all', seasonParam);
      if (cached?.data) {
        setStandingsData(cached.data.standings || []);
        setLoadingStandings(false);
        return;
      }
    }

    setLoadingStandings(true);
    fetch(`/api/standings?season=${seasonParam}`)
      .then(res => res.json())
      .then(resData => {
        setStandingsData(resData?.standings || []);
        const { expiresAt, label } = calculateTeamExpiry(data?.next_match, seasonParam);
        setCachedTeamData('standings', 'all', seasonParam, resData, expiresAt, label);
        setLoadingStandings(false);
      })
      .catch(err => {
        console.error('Error fetching standings:', err);
        setLoadingStandings(false);
      });
  }, [selectedSeason, dataRefreshVersion, data?.next_match]);

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
          clearTeamCache('all', selectedSeason || '2026_27');
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
      
      {/* Consolidated Ultra-Compact Control Bar */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-3 shadow-sm">
        <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-2.5">
          
          {/* Left: View Tabs (Fikstür / Puan Tablosu) + Gameweek Stepper */}
          <div className="flex flex-wrap items-center gap-2">
            
            {/* View Mode: Fikstür vs Puan Tablosu */}
            <div className="flex items-center bg-slate-100 p-0.5 rounded-xl border border-slate-200 shrink-0">
              <button
                type="button"
                onClick={() => setActiveView('fixtures')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  activeView === 'fixtures'
                    ? 'bg-[#38003c] text-white shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Calendar className="w-3.5 h-3.5" />
                <span>Fikstür</span>
              </button>
              <button
                type="button"
                onClick={() => setActiveView('table')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  activeView === 'table'
                    ? 'bg-[#38003c] text-white shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Trophy className="w-3.5 h-3.5 text-amber-500" />
                <span>Puan Tablosu</span>
              </button>
            </div>

            {/* Gameweek Stepper (Only in fixtures view) */}
            {activeView === 'fixtures' && (
              <div className="flex items-center gap-1 bg-slate-50 border border-slate-200 p-0.5 rounded-xl shrink-0">
                <button
                  type="button"
                  onClick={() => {
                    const currentNum = selectedGameweek === 'all' ? currentGameweek : Number(selectedGameweek);
                    const prev = Math.max(1, currentNum - 1);
                    setSelectedGameweek(String(prev));
                  }}
                  disabled={selectedGameweek !== 'all' && Number(selectedGameweek) <= 1}
                  className="p-1 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-200/70 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                  title="Önceki Hafta"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>

                {/* Gameweek Dropdown */}
                <div className="relative">
                  <button
                    type="button"
                    onClick={() => setIsGameweekMenuOpen(open => !open)}
                    className="flex items-center gap-1 px-2 py-0.5 text-xs font-mono font-bold text-slate-800 hover:text-[#38003c] transition-colors"
                  >
                    <span>{selectedGameweek === 'all' ? 'Tüm Haftalar' : `Hafta ${selectedGameweek}`}</span>
                    {String(selectedGameweek) === String(currentGameweek) && (
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" title="Mevcut Hafta" />
                    )}
                    <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition-transform ${isGameweekMenuOpen ? 'rotate-180' : ''}`} />
                  </button>

                  {/* Dropdown Menu */}
                  {isGameweekMenuOpen && (
                    <div className="absolute left-0 top-full z-50 mt-1.5 max-h-64 w-48 overflow-y-auto rounded-xl border border-slate-200 bg-white p-1.5 shadow-xl scrollbar-thin">
                      <button
                        type="button"
                        onClick={() => { setSelectedGameweek('all'); setIsGameweekMenuOpen(false); }}
                        className={`w-full rounded-lg px-2.5 py-1.5 text-left text-xs font-bold transition-all ${
                          selectedGameweek === 'all' ? 'bg-[#38003c] text-white' : 'text-slate-700 hover:bg-slate-100'
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
                            type="button"
                            onClick={() => { setSelectedGameweek(String(gw)); setIsGameweekMenuOpen(false); }}
                            className={`mt-0.5 flex w-full items-center justify-between rounded-lg px-2.5 py-1.5 text-left text-xs font-bold transition-all ${
                              isSelected ? 'bg-[#38003c] text-white' : 'text-slate-700 hover:bg-slate-100'
                            }`}
                          >
                            <span>Hafta {gw}</span>
                            {isCurrent && (
                              <span className={`rounded px-1.5 py-0.2 text-[9px] uppercase font-sans font-black ${
                                isSelected ? 'bg-emerald-500 text-white' : 'bg-emerald-100 text-emerald-800'
                              }`}>
                                Mevcut
                              </span>
                            )}
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>

                <button
                  type="button"
                  onClick={() => {
                    const currentNum = selectedGameweek === 'all' ? currentGameweek : Number(selectedGameweek);
                    const maxGw = allGwNumbers.length ? Math.max(...allGwNumbers) : 38;
                    const next = Math.min(maxGw, currentNum + 1);
                    setSelectedGameweek(String(next));
                  }}
                  disabled={selectedGameweek !== 'all' && Number(selectedGameweek) >= (allGwNumbers.length ? Math.max(...allGwNumbers) : 38)}
                  className="p-1 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-200/70 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                  title="Sonraki Hafta"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            )}

            {/* Quick jump to current week if viewing another week */}
            {activeView === 'fixtures' && String(selectedGameweek) !== String(currentGameweek) && (
              <button
                type="button"
                onClick={() => setSelectedGameweek(String(currentGameweek))}
                className="px-2 py-1 rounded-lg text-[11px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-200 hover:bg-emerald-100 transition-all flex items-center gap-1 shrink-0"
                title="Şu anki haftaya dön"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                <span>H{currentGameweek}'e Dön</span>
              </button>
            )}

            {activeView === 'table' && (
              <div className="flex items-center gap-2.5 text-[11px] font-medium text-slate-500 ml-1">
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

          {/* Right: Search + View Mode (List/Card) + Season Select + Sync Button */}
          <div className="flex flex-wrap items-center gap-2">
            
            {/* Search Input (Only for fixtures view) */}
            {activeView === 'fixtures' && (
              <div className="relative min-w-[170px] sm:min-w-[210px] flex-1 sm:flex-initial">
                <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Takım / stadyum ara..."
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl pl-8 pr-7 py-1.5 text-xs font-medium text-slate-900 placeholder-slate-400 outline-none focus:border-[#38003c] focus:bg-white transition-all"
                />
                {search && (
                  <button
                    type="button"
                    onClick={() => setSearch('')}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 text-xs font-bold px-1"
                    title="Aramayı temizle"
                  >
                    ✕
                  </button>
                )}
              </div>
            )}

            {/* View Mode Toggle: List ↔ Cards */}
            {activeView === 'fixtures' && (
              <div className="flex items-center bg-slate-100 p-0.5 rounded-xl border border-slate-200 shrink-0">
                <button
                  type="button"
                  onClick={() => handleDisplayModeChange('list')}
                  className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                    displayMode === 'list'
                      ? 'bg-[#38003c] text-white shadow-xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                  title="Kompakt Liste"
                >
                  <List className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Liste</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleDisplayModeChange('cards')}
                  className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                    displayMode === 'cards'
                      ? 'bg-[#38003c] text-white shadow-xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                  title="Detaylı Kartlar"
                >
                  <LayoutGrid className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Kart</span>
                </button>
              </div>
            )}

            {/* Season Selector Dropdown */}
            <div className="relative shrink-0">
              <label htmlFor="fixtures-season-select" className="sr-only">Sezon seç</label>
              <select
                id="fixtures-season-select"
                value={selectedSeason}
                onChange={(event) => setSelectedSeason(event.target.value)}
                className="appearance-none rounded-xl border border-slate-200 bg-slate-50 py-1.5 pl-2.5 pr-7 text-xs font-bold text-slate-700 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-[#38003c]/30 cursor-pointer"
              >
                {['2026_27', '2025_26', '2024_25', '2023_24', '2022_23'].map(season => (
                  <option key={season} value={season}>
                    {season === '2026_27' ? '2026-27' : season.replace('_', '-')}
                  </option>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-500" />
            </div>

            {/* Sync Season Button */}
            <button
              type="button"
              onClick={triggerSeasonSync}
              disabled={syncStatus === 'starting' || syncStatus === 'running'}
              title={syncStatus === 'starting' || syncStatus === 'running' ? 'Veriler eşitleniyor' : 'Sezon verisini eşitle'}
              className="p-1.5 rounded-xl border border-violet-200 bg-violet-50 text-violet-800 hover:bg-violet-100 transition-all shrink-0 disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${syncStatus === 'starting' || syncStatus === 'running' ? 'animate-spin' : ''}`} />
            </button>
          </div>

        </div>

        {/* Sync message if active */}
        {syncMessage && (
          <p className={`flex items-center gap-1 text-[10px] font-semibold ${syncStatus === 'failed' ? 'text-rose-700' : syncStatus === 'completed' ? 'text-emerald-700' : 'text-slate-500'}`}>
            {syncStatus === 'completed' && <CheckCircle2 className="h-3 w-3" />}
            {syncStatus === 'failed' && <AlertCircle className="h-3 w-3" />}
            <span>{syncMessage}</span>
          </p>
        )}
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
                            <button
                              type="button"
                              onClick={() => onSelectTeam?.(t.id)}
                              className="font-bold text-slate-900 truncate text-left hover:text-[#38003c] hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#38003c]"
                              aria-label={`${t.name} takım profiline git`}
                            >
                              {t.name}
                            </button>
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
              
              {/* Day Groups inside Gameweek */}
              <div className="space-y-5">
                {gwObj.days.map((dayObj, dayIdx) => (
                  <div key={dayIdx} className="space-y-2.5">
                    
                    {/* Day Subheader */}
                    <div className="flex items-center gap-2 text-xs font-bold text-slate-700 px-1">
                      <Calendar className="w-3.5 h-3.5 text-[#38003c]" />
                      <span>{dayObj.day}</span>
                    </div>

                    {/* Matches List or Grid for that Day */}
                    {displayMode === 'list' ? (
                      <div className="border border-slate-200 rounded-xl divide-y divide-slate-100 bg-white shadow-2xs overflow-hidden">
                        {dayObj.matches.map(m => {
                          const home = getTeam(m.home_id, m.home_name);
                          const away = getTeam(m.away_id, m.away_name);
                          const homeManager = teamManagers[String(m.home_id)];
                          const awayManager = teamManagers[String(m.away_id)];
                          const isCompleted = m.status === 'COMPLETED' && m.home_score !== null;

                          return (
                            <div
                              key={m.match_id}
                              onClick={() => {
                                if (onSelectMatch) {
                                  onSelectMatch({
                                    ...m,
                                    home_manager: homeManager || null,
                                    away_manager: awayManager || null,
                                  }, currentGameweek);
                                } else {
                                  setActiveModalMatch(m);
                                }
                              }}
                              className="px-3.5 py-2.5 sm:px-4 sm:py-3 hover:bg-slate-50/90 transition-all cursor-pointer group flex items-center justify-between gap-2 sm:gap-4 text-xs"
                            >
                              {/* 1. Status / Kickoff Time */}
                              <div className="w-14 sm:w-20 shrink-0 text-left">
                                {isCompleted ? (
                                  <span className="font-mono font-bold text-slate-500 text-[11px] block">
                                    MS
                                  </span>
                                ) : (
                                  <div className="flex items-center gap-1 text-slate-700 font-semibold text-[11px] sm:text-xs">
                                    <Clock className="w-3 h-3 text-slate-400 shrink-0 hidden sm:inline" />
                                    <span className="truncate">{m.time_label || 'vs'}</span>
                                  </div>
                                )}
                              </div>

                              {/* 2. Teams & Score (Center) */}
                              <div className="flex items-center justify-center gap-2 sm:gap-4 flex-1 min-w-0">
                                {/* Home Team */}
                                <div className="flex items-center gap-2 justify-end flex-1 min-w-0 text-right">
                                  <button
                                    type="button"
                                    onClick={(event) => { event.stopPropagation(); onSelectTeam?.(home.id); }}
                                    className="font-bold text-xs sm:text-sm text-slate-900 hover:text-[#38003c] hover:underline transition-colors truncate"
                                    aria-label={`${home.name} takım profiline git`}
                                  >
                                    {home.short || home.name}
                                  </button>
                                  <img 
                                    src={home.badge} 
                                    alt={home.name} 
                                    className="w-5 h-5 sm:w-6 sm:h-6 object-contain shrink-0"
                                    onError={(e) => { e.target.src = '/badges/1.svg'; }}
                                  />
                                </div>

                                {/* Score / VS Badge */}
                                <div className="shrink-0 flex items-center justify-center min-w-[55px] sm:min-w-[65px]">
                                  {isCompleted ? (
                                    <span className="px-2.5 py-1 rounded-lg bg-slate-900 text-white font-mono font-black text-xs sm:text-sm tracking-wider shadow-2xs">
                                      {m.home_score} - {m.away_score}
                                    </span>
                                  ) : (
                                    <span className="px-2.5 py-1 rounded-lg bg-slate-100 text-slate-600 font-mono text-xs font-bold border border-slate-200">
                                      VS
                                    </span>
                                  )}
                                </div>

                                {/* Away Team */}
                                <div className="flex items-center gap-2 justify-start flex-1 min-w-0 text-left">
                                  <img 
                                    src={away.badge} 
                                    alt={away.name} 
                                    className="w-5 h-5 sm:w-6 sm:h-6 object-contain shrink-0"
                                    onError={(e) => { e.target.src = '/badges/1.svg'; }}
                                  />
                                  <button
                                    type="button"
                                    onClick={(event) => { event.stopPropagation(); onSelectTeam?.(away.id); }}
                                    className="font-bold text-xs sm:text-sm text-slate-900 hover:text-[#38003c] hover:underline transition-colors truncate"
                                    aria-label={`${away.name} takım profiline git`}
                                  >
                                    {away.short || away.name}
                                  </button>
                                </div>
                              </div>

                              {/* 3. Prediction / Meta Badge & Chevron */}
                              <div className="flex items-center gap-2 shrink-0 min-w-[70px] sm:min-w-[120px] justify-end">
                                {m.prediction?.favorite_label ? (
                                  <span className="hidden sm:inline-flex items-center gap-1 text-[10px] font-bold text-[#38003c] bg-purple-50 border border-purple-200 px-2 py-0.5 rounded-full truncate max-w-[110px]">
                                    <Sparkles className="w-2.5 h-2.5 text-[#38003c] shrink-0" />
                                    <span className="truncate">{m.prediction.favorite_label}</span>
                                  </span>
                                ) : isCompleted && (m.home_xg != null || m.away_xg != null) ? (
                                  <span className="hidden sm:inline-block text-[10px] font-mono text-slate-400 bg-slate-50 px-1.5 py-0.5 rounded border border-slate-200">
                                    xG {Number(m.home_xg).toFixed(1)}-{Number(m.away_xg).toFixed(1)}
                                  </span>
                                ) : null}
                                <span className="text-[11px] font-bold text-[#38003c] group-hover:text-purple-700 group-hover:translate-x-0.5 transition-all flex items-center gap-0.5 bg-slate-50 group-hover:bg-purple-50 p-1.5 rounded-lg border border-slate-200/80">
                                  <ChevronRight className="w-3.5 h-3.5" />
                                </span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      /* Matches Grid for that Day (Detaylı Kartlar) */
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
                              onClick={() => {
                                if (onSelectMatch) {
                                  onSelectMatch({
                                    ...m,
                                    home_manager: homeManager || null,
                                    away_manager: awayManager || null,
                                  }, currentGameweek);
                                } else {
                                  setActiveModalMatch(m);
                                }
                              }}
                              className="bg-white border border-slate-200 hover:border-purple-300 rounded-2xl p-4 shadow-xs hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 cursor-pointer group flex flex-col justify-between gap-3 relative overflow-hidden"
                            >
                            
                            {/* Top Card Bar: Kickoff time & Ground */}
                            <div className="flex items-center justify-between text-[11px] text-slate-500 pb-2 border-b border-slate-100">
                              <div className="flex items-center gap-1.5 font-medium truncate max-w-[200px]">
                                <Clock className="w-3 h-3 text-slate-400 shrink-0" />
                                <span className="truncate">{m.time_label || m.kickoff_label}</span>
                              </div>

                              <span className="text-[11px] font-bold text-[#38003c] group-hover:text-purple-700 group-hover:translate-x-0.5 transition-all flex items-center gap-1 bg-purple-50 group-hover:bg-purple-100 px-2.5 py-0.5 rounded-lg border border-purple-200/60 shadow-2xs">
                                {isCompleted 
                                  ? 'Maç Sayfası' 
                                  : (Number(m.gameweek) === Number(currentGameweek) ? 'Model Analizi & Sayfa' : 'Maç Detayı')} 
                                <ChevronRight className="w-3.5 h-3.5" />
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
                                <button
                                  type="button"
                                  onClick={(event) => { event.stopPropagation(); onSelectTeam?.(home.id); }}
                                  className="font-bold text-xs text-slate-900 hover:text-[#38003c] hover:underline transition-colors truncate text-left"
                                  aria-label={`${home.name} takım profiline git`}
                                >
                                  {home.name}
                                </button>
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
                                <button
                                  type="button"
                                  onClick={(event) => { event.stopPropagation(); onSelectTeam?.(away.id); }}
                                  className="font-bold text-xs text-slate-900 hover:text-[#38003c] hover:underline transition-colors truncate text-right"
                                  aria-label={`${away.name} takım profiline git`}
                                >
                                  {away.name}
                                </button>
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

                                <div className="grid grid-cols-5 gap-1.5 text-[10px] font-mono text-center">
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
                                  <div className="bg-slate-50 py-1 px-1 rounded-lg border border-slate-100">
                                    <span className="text-[9px] text-rose-700 font-sans font-bold block">TheStatsAPI xG</span>
                                    {(m.home_xg != null || m.away_xg != null) ? (
                                      <strong className="text-rose-600 font-bold">
                                        {m.home_xg != null ? Number(m.home_xg).toFixed(2) : '-'} - {m.away_xg != null ? Number(m.away_xg).toFixed(2) : '-'}
                                      </strong>
                                    ) : (
                                      <span className="text-slate-400 font-normal italic text-[8.5px] block leading-[15px]">
                                        Not Found
                                      </span>
                                    )}
                                  </div>
                                </div>
                              </div>
                            ) : (
                              <div className="pt-2.5 border-t border-slate-100/90 space-y-2">
                                {/* Stadium & Favorite / Gameweek Meta Header */}
                                <div className="flex items-center justify-between text-[11px] text-slate-500 gap-2 px-0.5">
                                  <span className="flex items-center gap-1.5 truncate text-slate-500 font-medium">
                                    <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                                    <span className="truncate">{m.ground_name || 'Premier League Stadı'}</span>
                                  </span>
                                  {Number(m.gameweek) === Number(currentGameweek) && m.prediction?.favorite_label ? (
                                    <span className="inline-flex items-center gap-1 text-[10px] font-extrabold text-[#38003c] bg-purple-50/90 border border-purple-200/80 px-2 py-0.5 rounded-full shrink-0 shadow-2xs">
                                      <Sparkles className="w-2.5 h-2.5 text-[#38003c]" />
                                      {m.prediction.favorite_label}
                                    </span>
                                  ) : (
                                    <span className="text-[10px] font-semibold text-slate-500 bg-slate-100 border border-slate-200/60 px-2 py-0.5 rounded-full shrink-0">
                                      {Number(m.gameweek) === Number(currentGameweek) ? 'Mevcut Hafta' : `${m.gameweek}. Hafta`}
                                    </span>
                                  )}
                                </div>

                                {/* Current Gameweek: Unified Harmonious Prediction & Referee Card */}
                                {Number(m.gameweek) === Number(currentGameweek) && m.prediction ? (
                                  <div className="bg-slate-50/80 border border-slate-200/80 rounded-xl p-2 transition-all">
                                    {/* 3 Unified Metric Columns with subtle dividers */}
                                    <div className="grid grid-cols-3 divide-x divide-slate-200/80 text-center py-0.5">
                                      <div className="px-1">
                                        <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider block leading-tight">
                                          KORNER
                                        </span>
                                        <span className="text-xs font-mono font-black text-slate-800">
                                          ~{m.prediction.expected_corners}
                                        </span>
                                      </div>
                                      <div className="px-1">
                                        <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider block leading-tight">
                                          KART (+3.5)
                                        </span>
                                        <span className="text-xs font-mono font-black text-slate-800">
                                          %{m.prediction.prob_over_3_5_cards}
                                        </span>
                                      </div>
                                      <div className="px-1">
                                        <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider block leading-tight">
                                          2.5 ÜST GOL
                                        </span>
                                        <span className="text-xs font-mono font-black text-slate-800">
                                          %{m.prediction.over_2_5_goals_pct}
                                        </span>
                                      </div>
                                    </div>

                                    {/* Subtle Referee sub-line */}
                                    <div className="mt-1.5 pt-1.5 border-t border-slate-200/60 flex items-center justify-between text-[10px] text-slate-600 px-1">
                                      <span className="truncate">
                                        <span className="text-slate-400">Hakem: </span>
                                        <strong className="text-slate-700 font-semibold truncate">
                                          {m.referee_name && m.referee_name !== 'Atanmadı' && m.referee_name !== 'Unknown' 
                                            ? m.referee_name 
                                            : (m.prediction?.referee_name && m.prediction.referee_name !== 'Unknown' ? m.prediction.referee_name : 'Atanmadı')}
                                        </strong>
                                      </span>
                                      {(m.ref_avg_cards || m.prediction?.expected_cards) && (
                                        <span className="text-slate-500 font-mono text-[9.5px] font-medium shrink-0">
                                          Ort. {m.ref_avg_cards || m.prediction?.expected_cards} kart
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                ) : (
                                  /* Future Gameweeks: Simple, clean schedule bar without prediction noise */
                                  <div className="bg-slate-50/60 border border-slate-100 rounded-xl px-2.5 py-1.5 flex items-center justify-between text-[10px] text-slate-500">
                                    <span className="truncate">
                                      <span className="text-slate-400">Hakem: </span>
                                      <span className="font-medium text-slate-600">
                                        {m.referee_name && m.referee_name !== 'Atanmadı' && m.referee_name !== 'Unknown' 
                                          ? m.referee_name 
                                          : 'Henüz Atanmadı'}
                                      </span>
                                    </span>
                                    <span className="text-[9.5px] font-medium text-slate-400 shrink-0">
                                      Fikstür Programı
                                    </span>
                                  </div>
                                )}
                              </div>
                            )}

                          </div>
                        );
                      })}
                    </div>
                  )}

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
          currentGameweek={currentGameweek}
          onClose={() => setActiveModalMatch(null)}
        />
      )}

    </div>
  );
}
