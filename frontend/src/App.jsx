import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import PredictorTab from './components/PredictorTab';
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
          {activeTab === 'predictor' && (
            <PredictorTab selectedSeason={selectedSeason} />
          )}

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

        {/* Clean Light Footer */}
        <footer className="w-full bg-white border-t border-slate-200 mt-12 py-5 px-6">
          <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-500 font-medium">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              <span>Premier League Model Engine • Çoklu Sezon Veri Tabanı (2024-25, 2025-26 & 2026-27)</span>
            </div>
            <div className="flex items-center gap-3 font-mono text-[11px] text-slate-400">
              <span>Poisson (Goller)</span>
              <span>•</span>
              <span>XGBoost (Korner)</span>
              <span>•</span>
              <span>LightGBM (Taç)</span>
            </div>
          </div>
        </footer>

      </div>

    </div>
  );
}
