import FixturesGameweeksView from './fixtures/FixturesGameweeksView';
import FixturesStandingsView from './fixtures/FixturesStandingsView';
import { formatSeasonLabel } from '../utils/dateFormatters';
import React, { useState, useEffect, useMemo } from 'react';
import { 
  Search, 
  Calendar, 
  ChevronRight, 
  ChevronLeft,
  Trophy,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  List,
  LayoutGrid,
  ChevronDown,
  X
} from 'lucide-react';
import MatchDetailModal from './MatchDetailModal';
import { getCachedTeamData, setCachedTeamData, clearAllCaches, calculateTeamExpiry, syncDataVersion } from '../utils/teamProfileCache';
import { getGroupedFixtures, getSeasonSyncStatus, getStandings, startSeasonSync } from '../services/competitionService';
import { getTeamManagers } from '../services/teamService';

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
  const [syncKind, setSyncKind] = useState('matches');
  const [syncMatches, setSyncMatches] = useState([]);
  const [isSyncMenuOpen, setIsSyncMenuOpen] = useState(false);
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
    getGroupedFixtures(seasonParam)
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

    getTeamManagers(seasonParam)
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
    getStandings(seasonParam)
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
        const job = await getSeasonSyncStatus();
        if (cancelled) return;
        if (job.status === 'completed') {
          setSyncStatus('completed');
          setSyncMessage(job.message || 'Veriler güncellendi.');
          setSyncMatches(job.matches || []);
          clearAllCaches();
          await syncDataVersion();
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

  const triggerSeasonSync = async (kind = 'matches') => {
    setSyncKind(kind);
    setSyncMatches([]);
    setSyncStatus('starting');
    setSyncMessage('Başlandı...');
    try {
      const season = selectedSeason && selectedSeason !== 'all' ? selectedSeason : '2026_27';
      const job = await startSeasonSync(season, kind);
      setSyncStatus(job.status === 'completed' ? 'completed' : 'running');
      setSyncMessage(job.message || (job.already_running ? 'Başka bir güncelleme devam ediyor...' : 'Başlandı...'));
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

  const handleMatchClick = (match) => {
    const homeManager = teamManagers[String(match.home_id)];
    const awayManager = teamManagers[String(match.away_id)];
    if (onSelectMatch) {
      onSelectMatch({ ...match, home_manager: homeManager || null, away_manager: awayManager || null }, currentGameweek);
    } else {
      setActiveModalMatch(match);
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Consolidated Control Bar */}
      <div className="bg-background-primary border border-border rounded p-3">
        <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-2.5">
          
          {/* Left: View Tabs (Fikstür / Puan Tablosu) + Gameweek Stepper */}
          <div className="flex flex-wrap items-center gap-2">
            
            {/* View Mode: Fikstür vs Puan Tablosu */}
            <div className="flex items-center bg-background-tertiary p-0.5 rounded border border-border shrink-0">
              <button
                type="button"
                onClick={() => setActiveView('fixtures')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-sm text-xs font-medium transition-colors ${
                  activeView === 'fixtures'
                    ? 'bg-primary text-white'
                    : 'text-text-secondary hover:text-text-primary'
                }`}
              >
                <Calendar className="w-3.5 h-3.5" />
                <span>Fikstür</span>
              </button>
              <button
                type="button"
                onClick={() => setActiveView('table')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-sm text-xs font-medium transition-colors ${
                  activeView === 'table'
                    ? 'bg-primary text-white'
                    : 'text-text-secondary hover:text-text-primary'
                }`}
              >
                <Trophy className="w-3.5 h-3.5" />
                <span>Puan Tablosu</span>
              </button>
            </div>

            {/* Gameweek Stepper (Only in fixtures view) */}
            {activeView === 'fixtures' && (
              <div className="flex items-center gap-1 bg-background-tertiary border border-border p-0.5 rounded shrink-0">
                <button
                  type="button"
                  onClick={() => {
                    const currentNum = selectedGameweek === 'all' ? currentGameweek : Number(selectedGameweek);
                    const prev = Math.max(1, currentNum - 1);
                    setSelectedGameweek(String(prev));
                  }}
                  disabled={selectedGameweek !== 'all' && Number(selectedGameweek) <= 1}
                  className="p-1 rounded text-text-secondary hover:text-text-primary hover:bg-border-light disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  title="Önceki Hafta"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>

                {/* Gameweek Dropdown */}
                <div className="relative">
                  <button
                    type="button"
                    onClick={() => setIsGameweekMenuOpen(open => !open)}
                    className="flex items-center gap-1 px-2 py-0.5 text-xs font-mono font-medium text-text-primary transition-colors"
                  >
                    <span>{selectedGameweek === 'all' ? 'Tüm Haftalar' : `Hafta ${selectedGameweek}`}</span>
                    {String(selectedGameweek) === String(currentGameweek) && (
                      <span className="w-1.5 h-1.5 rounded-full bg-status-success" title="Mevcut Hafta" />
                    )}
                    <ChevronDown className={`w-3.5 h-3.5 text-text-muted transition-transform ${isGameweekMenuOpen ? 'rotate-180' : ''}`} />
                  </button>

                  {/* Dropdown Menu */}
                  {isGameweekMenuOpen && (
                    <div className="absolute left-0 top-full z-50 mt-1.5 max-h-64 w-48 overflow-y-auto rounded border border-border bg-background-primary p-1 shadow-md">
                      <button
                        type="button"
                        onClick={() => { setSelectedGameweek('all'); setIsGameweekMenuOpen(false); }}
                        className={`w-full rounded-sm px-2.5 py-1.5 text-left text-xs font-medium transition-colors ${
                          selectedGameweek === 'all' ? 'bg-primary text-white' : 'text-text-secondary hover:bg-background-tertiary'
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
                            className={`mt-0.5 flex w-full items-center justify-between rounded-sm px-2.5 py-1.5 text-left text-xs font-medium transition-colors ${
                              isSelected ? 'bg-primary text-white' : 'text-text-secondary hover:bg-background-tertiary'
                            }`}
                          >
                            <span>Hafta {gw}</span>
                            {isCurrent && (
                              <span className={`rounded-sm px-1.5 py-0.5 text-xs uppercase font-sans font-medium ${
                                isSelected ? 'bg-status-success text-white' : 'bg-background-tertiary text-status-success'
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
                  className="p-1 rounded text-text-secondary hover:text-text-primary hover:bg-border-light disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
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
                className="px-2 py-1 rounded text-xs font-medium bg-background-tertiary text-text-primary border border-border hover:bg-border-light transition-colors flex items-center gap-1 shrink-0"
                title="Şu anki haftaya dön"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-status-success" />
                <span>H{currentGameweek}'e Dön</span>
              </button>
            )}

            {activeView === 'table' && (
              <div className="flex items-center gap-2.5 text-xs font-medium text-text-secondary ml-1">
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-xs bg-status-info" />
                  <span>UCL (1-4)</span>
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-xs bg-status-warning" />
                  <span>UEL (5)</span>
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-xs bg-status-error" />
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
                <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Takım veya stadyum ara..."
                  className="w-full bg-background-primary border border-border rounded pl-8 pr-7 py-1.5 text-xs font-medium text-text-primary placeholder-text-muted outline-none focus:border-border-focus transition-colors"
                />
                {search && (
                  <button
                    type="button"
                    onClick={() => setSearch('')}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary text-xs p-1"
                    title="Aramayı temizle"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            )}

            {/* View Mode Toggle: List ↔ Cards */}
            {activeView === 'fixtures' && (
              <div className="flex items-center bg-background-tertiary p-0.5 rounded border border-border shrink-0">
                <button
                  type="button"
                  onClick={() => handleDisplayModeChange('list')}
                  className={`flex items-center gap-1 px-2.5 py-1.5 rounded-sm text-xs font-medium transition-colors ${
                    displayMode === 'list'
                      ? 'bg-primary text-white'
                      : 'text-text-secondary hover:text-text-primary'
                  }`}
                  title="Kompakt Liste"
                >
                  <List className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Liste</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleDisplayModeChange('cards')}
                  className={`flex items-center gap-1 px-2.5 py-1.5 rounded-sm text-xs font-medium transition-colors ${
                    displayMode === 'cards'
                      ? 'bg-primary text-white'
                      : 'text-text-secondary hover:text-text-primary'
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
                className="appearance-none rounded border border-border bg-background-primary py-1.5 pl-2.5 pr-7 text-xs font-medium text-text-primary hover:bg-background-tertiary focus:outline-none focus:border-border-focus cursor-pointer"
              >
                {['2026_27', '2025_26', '2024_25', '2023_24', '2022_23'].map(season => (
                  <option key={season} value={season}>
                    {formatSeasonLabel(season)}
                  </option>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-text-muted" />
            </div>

            {/* Sync Dropdown */}
            {(() => {
              const busy = syncStatus === 'starting' || syncStatus === 'running';
              return (
                <div className="relative shrink-0">
                  <button
                    type="button"
                    onClick={() => setIsSyncMenuOpen(open => !open)}
                    disabled={busy}
                    title={busy ? 'Veriler eşitleniyor' : 'Veri güncelle'}
                    className="flex items-center gap-1 px-2.5 py-1.5 rounded border border-border bg-background-tertiary text-text-primary text-xs font-medium hover:bg-border transition-colors disabled:opacity-50"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${busy ? 'animate-spin' : ''}`} />
                    <ChevronDown className={`w-3.5 h-3.5 transition-transform ${isSyncMenuOpen ? 'rotate-180' : ''}`} />
                  </button>
                  {isSyncMenuOpen && (
                    <>
                      <div className="fixed inset-0 z-40" onClick={() => setIsSyncMenuOpen(false)} />
                      <div className="absolute right-0 top-full z-50 mt-1.5 w-64 rounded border border-border bg-background-primary p-1 shadow-md">
                        {[
                          { kind: 'referees', label: 'Hakemler', hint: 'Atanan hakemleri çek' },
                          { kind: 'lineups', label: 'Kadrolar', hint: 'Önümüzdeki 2 saatteki maçların resmi kadroları' },
                          { kind: 'matches', label: 'Maç verisi', hint: 'Biten maçların istatistikleri' },
                        ].map(({ kind, label, hint }) => (
                          <button
                            key={kind}
                            type="button"
                            onClick={() => { setIsSyncMenuOpen(false); triggerSeasonSync(kind); }}
                            className="block w-full rounded-sm px-2.5 py-1.5 text-left transition-colors hover:bg-background-tertiary"
                          >
                            <span className="block text-xs font-medium text-text-primary">{label}</span>
                            <span className="block text-xs text-text-muted">{hint}</span>
                          </button>
                        ))}
                      </div>
                    </>
                  )}
                </div>
              );
            })()}
          </div>

        </div>

        {/* Sync message if active */}
        {syncMessage && (
          <p className={`flex items-center gap-1 text-xs font-medium mt-2 ${syncStatus === 'failed' ? 'text-status-error' : syncStatus === 'completed' ? 'text-status-success' : 'text-text-muted'}`}>
            {syncStatus === 'completed' && <CheckCircle2 className="h-3.5 w-3.5" />}
            {syncStatus === 'failed' && <AlertCircle className="h-3.5 w-3.5" />}
            <span>{syncMessage}</span>
          </p>
        )}
        {syncStatus === 'completed' && syncMatches.length > 0 && (
          <ul className="text-xs text-text-secondary space-y-0.5 mt-1">
            {syncMatches.map(name => <li key={name}>• {name}</li>)}
          </ul>
        )}
      </div>

      {/* Conditional View: Puan Tablosu vs Fikstür */}
      {activeView === 'table' ? (
        <FixturesStandingsView
          displayedStandings={displayedStandings}
          standingsType={standingsType}
          setStandingsType={setStandingsType}
          loadingStandings={loadingStandings}
          onSelectTeam={onSelectTeam}
        />
            ) : (
        <FixturesGameweeksView
          loading={loading}
          filteredGameweeks={filteredGameweeks}
          displayMode={displayMode}
          currentGameweek={currentGameweek}
          teamManagers={teamManagers}
          teamForms={teamForms}
          onMatchClick={handleMatchClick}
          onSelectTeam={onSelectTeam}
        />
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
