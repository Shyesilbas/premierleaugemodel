import React, { Suspense, lazy, useEffect, useState } from 'react';
import { Search } from 'lucide-react';
import Sidebar from './components/Sidebar';
import CommandPalette from './components/common/CommandPalette';
import CompetitionSelector from './components/common/CompetitionSelector';
import ErrorBoundary from './components/common/ErrorBoundary';
import Skeleton from './components/common/Skeleton';
import ThemeToggle from './components/common/ThemeToggle';
import { CompetitionProvider } from './context/CompetitionContext';
import { useCompetition } from './context/competitionState';
import { ThemeProvider } from './context/ThemeContext';
import { navigateTo, parseUrlRoute } from './utils/router';

const FixturesTab = lazy(() => import('./components/FixturesTab'));
const TeamProfilesTab = lazy(() => import('./components/TeamProfilesTab'));
const PlayerProfilesTab = lazy(() => import('./components/PlayerProfilesTab'));
const PlayerCompareTab = lazy(() => import('./components/PlayerCompareTab'));
const RefereesTab = lazy(() => import('./components/RefereesTab'));
const MatchDetailPage = lazy(() => import('./components/MatchDetailPage'));
const ModelAuditTab = lazy(() => import('./components/ModelAuditTab'));
const StatsTab = lazy(() => import('./components/StatsTab'));

function RouteSkeleton() {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="İçerik yükleniyor">
      <div className="flex items-center justify-between gap-4">
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-9 w-36" />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
      <Skeleton className="h-96 w-full" />
    </div>
  );
}

function AppInner() {
  const initialRoute = parseUrlRoute();
  const [activeTab, setActiveTab] = useState(() => initialRoute.tab || 'fixtures');
  const [selectedSeason, setSelectedSeason] = useState('2026_27');
  const [selectedTeamId, setSelectedTeamId] = useState(() => initialRoute.team || 1);
  const [selectedPlayerId, setSelectedPlayerId] = useState(() => initialRoute.playerId);
  const [comparePlayers, setComparePlayers] = useState(() => ({
    p1: initialRoute.compareP1,
    p2: initialRoute.compareP2,
  }));
  const [selectedMatch, setSelectedMatch] = useState(() => (
    initialRoute.matchId ? { match_id: Number(initialRoute.matchId) } : null
  ));
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    try {
      return localStorage.getItem('pl-sidebar-collapsed') === 'true';
    } catch {
      return false;
    }
  });
  const [currentGameweek, setCurrentGameweek] = useState(1);
  const [paletteOpen, setPaletteOpen] = useState(false);

  const { activeCompetition, hasAudit } = useCompetition();
  // The audit tab belongs to competitions whose model has an audit page (Premier League only).
  const visibleTab = !hasAudit && activeTab === 'audit' ? 'fixtures' : activeTab;

  const handleSetSidebarCollapsed = (next) => {
    setSidebarCollapsed(next);
    try {
      localStorage.setItem('pl-sidebar-collapsed', String(next));
    } catch {}
  };

  useEffect(() => {
    const syncFromUrl = () => {
      const route = parseUrlRoute();
      setActiveTab(route.tab || 'fixtures');
      if (route.team) setSelectedTeamId(route.team);
      setSelectedPlayerId(route.playerId || null);
      if (route.compareP1 || route.compareP2) {
        setComparePlayers({ p1: route.compareP1, p2: route.compareP2 });
      }
      if (route.matchId) {
        setSelectedMatch((prev) => (
          prev && String(prev.match_id) === String(route.matchId)
            ? prev
            : { match_id: Number(route.matchId) }
        ));
      } else {
        setSelectedMatch(null);
      }
    };
    window.addEventListener('popstate', syncFromUrl);
    return () => window.removeEventListener('popstate', syncFromUrl);
  }, []);

  useEffect(() => {
    const onKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setPaletteOpen((open) => !open);
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  const handleSelectMatch = (match, gw = null) => {
    setSelectedMatch(match);
    if (gw) setCurrentGameweek(gw);
    if (match) {
      navigateTo({ tab: 'fixtures', matchId: String(match.match_id) });
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const handleBackToFixtures = () => {
    setSelectedMatch(null);
    navigateTo({ tab: 'fixtures', matchId: null });
  };

  const handleTabChange = (tab) => {
    setSelectedMatch(null);
    if (tab === 'players') {
      setSelectedPlayerId(null);
    }
    setActiveTab(tab);
    navigateTo({ tab, matchId: null, ...(tab === 'players' ? { playerId: null } : {}) });
  };

  const handleSelectTeamGlobal = (teamId) => {
    const id = Number(teamId);
    setSelectedMatch(null);
    setSelectedTeamId(id);
    setActiveTab('teams');
    navigateTo({ tab: 'teams', team: id });
  };

  const handleSelectPlayerGlobal = (playerId) => {
    setSelectedMatch(null);
    if (playerId == null) {
      setSelectedPlayerId(null);
      setActiveTab('players');
      navigateTo({ tab: 'players', playerId: null });
      return;
    }
    setSelectedPlayerId(String(playerId));
    setActiveTab('players');
    navigateTo({ tab: 'players', playerId: String(playerId) });
  };

  const handleClearPlayer = () => {
    handleSelectPlayerGlobal(null);
  };

  const handleComparePlayer = (playerId) => {
    setSelectedMatch(null);
    setComparePlayers({ p1: String(playerId), p2: null });
    setActiveTab('player-compare');
    navigateTo({ tab: 'player-compare', compareP1: String(playerId), compareP2: null });
  };

  return (
    <div className="min-h-screen bg-background-secondary text-text-primary flex transition-colors duration-200">
      <a
        href="#main-content"
        className="visually-hidden focus:fixed focus:top-3 focus:left-3 focus:z-[60] focus:px-4 focus:py-2 focus:rounded focus:bg-primary focus:text-white focus:text-sm focus:font-medium"
      >
        Ana içeriğe atla
      </a>

      <Sidebar
        activeTab={visibleTab}
        setActiveTab={handleTabChange}
        collapsed={sidebarCollapsed}
        setCollapsed={handleSetSidebarCollapsed}
      />

      <div className={`flex-1 flex flex-col justify-between min-h-screen w-full transition-all duration-200 ease-out ${sidebarCollapsed ? 'lg:pl-16' : 'lg:pl-60'}`}>
        <main id="main-content" tabIndex={-1} className="p-4 sm:p-6 lg:p-8 pt-20 lg:pt-6 max-w-7xl w-full mx-auto space-y-6 outline-none">
          {/* Desktop Top Header Bar: Competition metadata, Tournament Selector, Global Cmd+K Search & ThemeToggle */}
          <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-border-light">
            <div className="hidden lg:flex items-center gap-2 text-xs text-text-secondary">
              <span className="font-semibold text-text-primary">{activeCompetition.name}</span>
              <span aria-hidden="true">·</span>
              <span>{activeCompetition.country}</span>
              {typeof activeCompetition.uefa_coefficient === 'number' && (
                <>
                  <span aria-hidden="true">·</span>
                  <span className="font-mono tabular-nums">UEFA Katsayısı: {activeCompetition.uefa_coefficient.toFixed(3)}</span>
                </>
              )}
            </div>

            <div className="flex flex-1 lg:flex-initial flex-wrap items-center justify-end gap-2.5">
              <button
                type="button"
                onClick={() => setPaletteOpen(true)}
                className="inline-flex h-9 items-center gap-2 rounded border border-border bg-background-primary hover:bg-background-tertiary px-3 text-xs font-medium text-text-secondary hover:text-text-primary transition-colors cursor-pointer"
                aria-label="Hızlı arama (Cmd+K)"
                title="Hızlı arama (Cmd+K)"
              >
                <Search className="w-3.5 h-3.5 text-text-muted" strokeWidth={1.5} aria-hidden="true" />
                <span className="hidden sm:inline">Ara...</span>
                <kbd className="hidden md:inline-block rounded-sm border border-border bg-background-tertiary px-1.5 py-0.5 text-xs font-mono text-text-muted">
                  Cmd+K
                </kbd>
              </button>

              <CompetitionSelector />
              <ThemeToggle />
            </div>
          </div>

          <ErrorBoundary key={selectedMatch ? `match-${selectedMatch.match_id}` : visibleTab}>
            <Suspense fallback={<RouteSkeleton />}>
              {selectedMatch ? (
                <MatchDetailPage
                  match={selectedMatch}
                  onBack={handleBackToFixtures}
                  currentGameweek={currentGameweek}
                  selectedSeason={selectedSeason}
                />
              ) : (
                <>
                  {visibleTab === 'fixtures' && (
                    <FixturesTab
                      selectedSeason={selectedSeason}
                      setSelectedSeason={setSelectedSeason}
                      onSelectMatch={handleSelectMatch}
                      onSelectTeam={handleSelectTeamGlobal}
                    />
                  )}

                  {visibleTab === 'teams' && (
                    <TeamProfilesTab
                      selectedSeason={selectedSeason}
                      setSelectedSeason={setSelectedSeason}
                      onSelectMatch={handleSelectMatch}
                      selectedTeamId={selectedTeamId}
                      onSelectTeam={setSelectedTeamId}
                    />
                  )}

                  {visibleTab === 'players' && (
                    <PlayerProfilesTab
                      key={`players-${selectedPlayerId || 'default'}`}
                      selectedSeason={selectedSeason}
                      setSelectedSeason={setSelectedSeason}
                      onSelectMatch={handleSelectMatch}
                      initialPlayerId={selectedPlayerId}
                      onSelectPlayer={handleSelectPlayerGlobal}
                      onBackToDiscovery={handleClearPlayer}
                      onComparePlayer={handleComparePlayer}
                    />
                  )}

                  {visibleTab === 'player-compare' && (
                    <PlayerCompareTab
                      selectedSeason={selectedSeason}
                      setSelectedSeason={setSelectedSeason}
                      initialP1Id={comparePlayers.p1}
                      initialP2Id={comparePlayers.p2}
                      onSelectPlayerProfile={handleSelectPlayerGlobal}
                    />
                  )}

                  {visibleTab === 'referees' && (
                    <RefereesTab
                      selectedSeason={selectedSeason}
                      onSelectMatch={handleSelectMatch}
                    />
                  )}

                  {visibleTab === 'stats' && (
                    <StatsTab
                      selectedSeason={selectedSeason}
                      setSelectedSeason={setSelectedSeason}
                      onSelectMatch={handleSelectMatch}
                    />
                  )}

                  {visibleTab === 'audit' && (
                    <ModelAuditTab
                      selectedSeason={selectedSeason}
                      onSelectMatch={handleSelectMatch}
                    />
                  )}
                </>
              )}
            </Suspense>
          </ErrorBoundary>
        </main>
      </div>

      <CommandPalette
        isOpen={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        onSelectTeam={handleSelectTeamGlobal}
        onSelectPlayer={handleSelectPlayerGlobal}
      />
    </div>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <CompetitionProvider>
        <AppInner />
      </CompetitionProvider>
    </ThemeProvider>
  );
}
