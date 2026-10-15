import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import FixturesTab from './components/FixturesTab';
import TeamProfilesTab from './components/TeamProfilesTab';
import PlayerProfilesTab from './components/PlayerProfilesTab';
import RefereesTab from './components/RefereesTab';
import MatchDetailPage from './components/MatchDetailPage';
import ModelAuditTab from './components/ModelAuditTab';

export default function App() {
  const [activeTab, setActiveTab] = useState('fixtures'); // Default to fixtures per user request
  const [selectedSeason, setSelectedSeason] = useState('2026_27'); // Default to current season
  const [selectedTeamId, setSelectedTeamId] = useState(1);
  const [selectedMatch, setSelectedMatch] = useState(null);
  const [currentGameweek, setCurrentGameweek] = useState(6);

  const handleSelectMatch = (match, gw = null) => {
    setSelectedMatch(match);
    if (gw) setCurrentGameweek(gw);
    if (match) {
      try {
        window.history.pushState({ matchId: match.match_id }, '', `#match-${match.match_id}`);
      } catch {}
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const handleBackToFixtures = () => {
    setSelectedMatch(null);
    if (window.location.hash.startsWith('#match-')) {
      try {
        window.history.back();
      } catch {
        window.location.hash = '';
      }
    }
  };

  useEffect(() => {
    const handlePopState = () => {
      if (!window.location.hash.startsWith('#match-')) {
        setSelectedMatch(null);
      }
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const handleTabChange = (tab) => {
    setSelectedMatch(null);
    setActiveTab(tab);
    if (window.location.hash.startsWith('#match-')) {
      window.location.hash = '';
    }
  };

  return (
    <div className="min-h-screen bg-[#f1f5f9] text-slate-900 flex">
      
      {/* Left Vertical Sticky Sidebar */}
      <Sidebar 
        activeTab={activeTab} 
        setActiveTab={handleTabChange} 
        selectedSeason={selectedSeason}
        setSelectedSeason={setSelectedSeason}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col justify-between min-h-screen lg:pl-72 w-full">
        
        {/* Main Content Body */}
        <main className="p-4 sm:p-6 lg:p-8 pt-20 lg:pt-8 max-w-7xl w-full mx-auto space-y-6">
          {selectedMatch ? (
            <MatchDetailPage 
              match={selectedMatch} 
              onBack={handleBackToFixtures}
              currentGameweek={currentGameweek}
              selectedSeason={selectedSeason}
            />
          ) : (
            <>
              {activeTab === 'fixtures' && (
                <FixturesTab 
                  selectedSeason={selectedSeason} 
                  setSelectedSeason={setSelectedSeason}
                  onSelectMatch={handleSelectMatch}
                  onSelectTeam={(teamId) => {
                    setSelectedTeamId(Number(teamId));
                    handleTabChange('teams');
                  }}
                />
              )}

              {activeTab === 'teams' && (
                <TeamProfilesTab 
                  selectedSeason={selectedSeason} 
                  onSelectMatch={handleSelectMatch}
                  selectedTeamId={selectedTeamId}
                  onSelectTeam={setSelectedTeamId}
                />
              )}

              {activeTab === 'players' && (
                <PlayerProfilesTab 
                  selectedSeason={selectedSeason} 
                  onSelectMatch={handleSelectMatch}
                />
              )}

              {activeTab === 'referees' && (
                <RefereesTab 
                  selectedSeason={selectedSeason} 
                  onSelectMatch={handleSelectMatch}
                />
              )}

              {activeTab === 'audit' && (
                <ModelAuditTab 
                  selectedSeason={selectedSeason} 
                  onSelectMatch={handleSelectMatch}
                />
              )}
            </>
          )}
        </main>

      </div>

    </div>
  );
}

