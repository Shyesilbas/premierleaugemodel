import React, { useState } from 'react';
import { 
  Calendar, 
  Shield, 
  User, 
  Menu, 
  X, 
  ChevronDown,
  ChevronLeft,
  Database,
  Trophy,
  Scale,
  ShieldCheck,
  BarChart3
} from 'lucide-react';

export default function Sidebar({
  activeTab,
  setActiveTab,
  selectedSeason,
  setSelectedSeason,
  collapsed,
  setCollapsed
}) {
  const [mobileOpen, setMobileOpen] = useState(false);

  const navItems = [
    { id: 'fixtures', label: 'Fikstür & Günler', icon: Calendar },
    { id: 'teams', label: 'Takım Profilleri', icon: Shield },
    { id: 'players', label: 'Oyuncu Profilleri', icon: User },
    { id: 'referees', label: 'Hakem Profilleri', icon: Scale },
    { id: 'stats', label: 'İstatistikler', icon: BarChart3 },
    { id: 'audit', label: 'Model Doğrulama', icon: ShieldCheck },
  ];

  const seasons = [
    { value: '2026_27', label: '2026-27 (Güncel Sezon)', note: 'Fikstür' },
    { value: '2025_26', label: '2025-26 (Tam Sezon)', note: '380 Maç' },
    { value: '2024_25', label: '2024-25 (Tam Sezon)', note: '380 Maç' },
    { value: '2023_24', label: '2023-24 (Tam Sezon)', note: '380 Maç' },
    { value: '2022_23', label: '2022-23 (Tam Sezon)', note: '380 Maç' },
    { value: 'all', label: 'Tüm Sezonlar', note: '1,520+ Maç' },
  ];

  const handleNavClick = (tabId) => {
    setActiveTab(tabId);
    setMobileOpen(false);
  };

  return (
    <>
      {/* Mobile Top Header */}
      <div className="lg:hidden fixed top-0 left-0 right-0 h-16 bg-background-primary border-b border-border z-40 px-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded bg-primary text-white flex items-center justify-center">
            <Trophy className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className="text-sm font-semibold text-text-primary leading-tight">Premier League</h1>
          </div>
        </div>

        <button 
          onClick={() => setMobileOpen(!mobileOpen)}
          className="p-2 rounded bg-background-tertiary hover:bg-border text-text-secondary transition-colors"
          aria-label="Toggle Navigation"
        >
          {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Mobile Backdrop */}
      {mobileOpen && (
        <div 
          className="lg:hidden fixed inset-0 bg-black/40 z-40"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Desktop Reopen Button (visible only when collapsed) */}
      {collapsed && (
        <button
          onClick={() => setCollapsed(false)}
          className="hidden lg:flex fixed top-4 left-4 z-40 p-2 rounded bg-background-primary border border-border hover:bg-background-tertiary text-text-secondary transition-colors"
          aria-label="Show sidebar"
        >
          <Menu className="w-5 h-5" />
        </button>
      )}

      {/* Main Sidebar (Desktop fixed left, mobile drawer) */}
      <aside
        className={`fixed top-0 bottom-0 left-0 w-72 bg-background-primary border-r border-border z-50 flex flex-col justify-between transition-transform duration-200 ease-out ${
          collapsed ? 'lg:-translate-x-full' : 'lg:translate-x-0'
        } ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="p-5 flex flex-col h-full overflow-y-auto">

          {/* Logo & Branding */}
          <div className="flex items-center gap-3.5 pb-6 border-b border-border-light">
            <div className="w-9 h-9 rounded bg-primary text-white flex items-center justify-center">
              <Trophy className="w-4 h-4 text-white" />
            </div>
            <div className="flex-1 min-w-0">
              <h1 className="font-semibold text-base tracking-tight text-text-primary">Premier League</h1>
            </div>
            <button
              onClick={() => setCollapsed(true)}
              className="hidden lg:flex p-2 rounded hover:bg-background-tertiary text-text-secondary transition-colors"
              aria-label="Hide sidebar"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
          </div>

          {/* Season Selector */}
          <div className="py-5 border-b border-border-light">
            <label className="text-xs font-semibold text-text-secondary block mb-2 flex items-center justify-between">
              <span>Sezon Filtresi</span>
              <Database className="w-3.5 h-3.5 text-text-muted" />
            </label>
            <div className="relative">
              <select
                value={selectedSeason}
                onChange={(e) => setSelectedSeason(e.target.value)}
                className="w-full appearance-none bg-background-primary hover:bg-background-tertiary border border-border rounded px-3 py-2 text-xs font-medium text-text-primary outline-none focus:border-border-focus transition-all cursor-pointer"
              >
                {seasons.map(s => (
                  <option key={s.value} value={s.value} className="text-text-primary">
                    {s.label}
                  </option>
                ))}
              </select>
              <ChevronDown className="w-4 h-4 text-text-muted absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>
          </div>

          {/* Navigation Links */}
          <div className="py-5 flex-1">
            <span className="text-xs font-semibold text-text-secondary block mb-3 px-2">
              Ana Menü
            </span>
            <nav className="space-y-1">
              {navItems.map(item => {
                const Icon = item.icon;
                const isActive = activeTab === item.id;

                return (
                  <button
                    key={item.id}
                    onClick={() => handleNavClick(item.id)}
                    className={`w-full flex items-center justify-start px-3 py-2.5 rounded text-xs font-medium transition-colors duration-150 group ${
                      isActive
                        ? 'bg-primary text-white'
                        : 'text-text-secondary hover:text-text-primary hover:bg-background-tertiary'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <Icon className={`w-4 h-4 ${
                        isActive ? 'text-white' : 'text-text-muted group-hover:text-text-primary'
                      }`} />
                      <span>{item.label}</span>
                    </div>

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
