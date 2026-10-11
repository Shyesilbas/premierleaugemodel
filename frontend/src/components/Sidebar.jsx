import React, { useState } from 'react';
import { 
  Sparkles, 
  Calendar, 
  Shield, 
  User, 
  Menu, 
  X, 
  ChevronDown,
  Layers,
  Database,
  Trophy
} from 'lucide-react';

export default function Sidebar({ 
  activeTab, 
  setActiveTab, 
  selectedSeason, 
  setSelectedSeason 
}) {
  const [mobileOpen, setMobileOpen] = useState(false);

  const navItems = [
    { id: 'predictor', label: 'Tahmin Motoru', icon: Sparkles, badge: 'ML' },
    { id: 'fixtures', label: 'Fikstür & Günler', icon: Calendar, badge: 'Haftalık' },
    { id: 'teams', label: 'Takım Profilleri', icon: Shield, badge: '20 Kulüp' },
    { id: 'players', label: 'Oyuncu Profilleri', icon: User, badge: '756 Oyuncu' },
  ];

  const seasons = [
    { value: '2026_27', label: '2026-27 (Güncel Fikstür)', note: 'Fikstür' },
    { value: '2025_26', label: '2025-26 (Tam Sezon)', note: '380 Maç' },
    { value: '2024_25', label: '2024-25 (Tam Sezon)', note: '380 Maç' },
    { value: 'all', label: 'Tüm Sezonlar', note: '760+ Maç' },
  ];

  const handleNavClick = (tabId) => {
    setActiveTab(tabId);
    setMobileOpen(false);
  };

  return (
    <>
      {/* Mobile Top Header */}
      <div className="lg:hidden fixed top-0 left-0 right-0 h-16 bg-white/95 backdrop-blur-md border-b border-slate-200 z-40 px-4 flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-[#38003c] text-white flex items-center justify-center shadow-sm">
            <Trophy className="w-4 h-4 text-[#00ff87]" />
          </div>
          <div>
            <h1 className="text-sm font-black text-slate-900 leading-tight">Premier League</h1>
          </div>
        </div>

        <button 
          onClick={() => setMobileOpen(!mobileOpen)}
          className="p-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 transition-colors"
          aria-label="Toggle Navigation"
        >
          {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Mobile Backdrop */}
      {mobileOpen && (
        <div 
          className="lg:hidden fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-40"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Main Sidebar (Desktop fixed left, mobile drawer) */}
      <aside 
        className={`fixed top-0 bottom-0 left-0 w-72 bg-white border-r border-slate-200 z-50 flex flex-col justify-between transition-transform duration-300 ease-in-out shadow-sm lg:translate-x-0 ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="p-5 flex flex-col h-full overflow-y-auto">
          
          {/* Logo & Branding */}
          <div className="flex items-center gap-3.5 pb-6 border-b border-slate-100">
            <div className="w-10 h-10 rounded-2xl bg-[#38003c] text-white flex items-center justify-center shadow-md shadow-[#38003c]/20">
              <Trophy className="w-5 h-5 text-[#00ff87]" />
            </div>
            <div>
              <h1 className="font-black text-base tracking-tight text-slate-900">Premier League</h1>
            </div>
          </div>

          {/* Season Selector */}
          <div className="py-5 border-b border-slate-100">
            <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600 block mb-2 flex items-center justify-between">
              <span>Sezon Filtresi</span>
              <Database className="w-3.5 h-3.5 text-slate-400" />
            </label>
            <div className="relative">
              <select
                value={selectedSeason}
                onChange={(e) => setSelectedSeason(e.target.value)}
                className="w-full appearance-none bg-slate-50 hover:bg-slate-100/80 border border-slate-200 rounded-xl px-3.5 py-2.5 text-xs font-bold text-slate-800 outline-none focus:border-[#38003c] focus:ring-2 focus:ring-[#38003c]/10 transition-all cursor-pointer"
              >
                {seasons.map(s => (
                  <option key={s.value} value={s.value} className="text-slate-900">
                    {s.label}
                  </option>
                ))}
              </select>
              <ChevronDown className="w-4 h-4 text-slate-400 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>
            <div className="flex items-center justify-between text-[10px] text-slate-600 mt-2 px-1">
              <span>Aktif Veri Kümesi:</span>
              <span className="font-mono font-bold text-slate-700">
                {selectedSeason === '2026_27' ? '380 Fikstür' : selectedSeason === 'all' ? '760 Maç' : '380 Maç'}
              </span>
            </div>
          </div>

          {/* Navigation Links */}
          <div className="py-5 flex-1">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-600 block mb-3 px-2">
              Ana Menü
            </span>
            <nav className="space-y-1.5">
              {navItems.map(item => {
                const Icon = item.icon;
                const isActive = activeTab === item.id;

                return (
                  <button
                    key={item.id}
                    onClick={() => handleNavClick(item.id)}
                    className={`w-full flex items-center justify-between px-3.5 py-3 rounded-xl text-xs font-bold transition-all duration-200 group ${
                      isActive
                        ? 'bg-[#38003c] text-white shadow-md shadow-[#38003c]/20'
                        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <Icon className={`w-4 h-4 transition-transform group-hover:scale-110 ${
                        isActive ? 'text-[#00ff87]' : 'text-slate-500 group-hover:text-slate-800'
                      }`} />
                      <span>{item.label}</span>
                    </div>

                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full font-bold ${
                      isActive 
                        ? 'bg-white/20 text-white' 
                        : 'bg-slate-100 text-slate-600 group-hover:bg-slate-200'
                    }`}>
                      {item.badge}
                    </span>
                  </button>
                );
              })}
            </nav>
          </div>

        </div>
      </aside>
    </>
  );
}
