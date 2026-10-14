import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import FixturesTab from './components/FixturesTab';
import TeamProfilesTab from './components/TeamProfilesTab';
import PlayerProfilesTab from './components/PlayerProfilesTab';
import RefereesTab from './components/RefereesTab';

export default function App() {
  const [activeTab, setActiveTab] = useState('fixtures'); // Default to fixtures per user request
  const [selectedSeason, setSelectedSeason] = useState('2026_27'); // Default to current season

  return (
    <div className="min-h-screen bg-[#f1f5f9] text-slate-900 flex">
      
      {/* Left Vertical Sticky Sidebar */}
      <Sidebar 
        activeTab={activeTab} 
        setActiveTab={setActiveTab} 
        selectedSeason={selectedSeason}
        setSelectedSeason={setSelectedSeason}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col justify-between min-h-screen lg:pl-72 w-full">
        
        {/* Main Content Body */}
        <main className="p-4 sm:p-6 lg:p-8 pt-20 lg:pt-8 max-w-7xl w-full mx-auto space-y-6">
          {activeTab === 'fixtures' && (
            <FixturesTab 
              selectedSeason={selectedSeason} 
              setSelectedSeason={setSelectedSeason} 
            />
          )}

          {activeTab === 'teams' && (
            <TeamProfilesTab selectedSeason={selectedSeason} />
          )}

          {activeTab === 'players' && (
            <PlayerProfilesTab selectedSeason={selectedSeason} />
          )}

          {activeTab === 'referees' && (
            <RefereesTab selectedSeason={selectedSeason} />
          )}
        </main>

      </div>

    </div>
  );
}
