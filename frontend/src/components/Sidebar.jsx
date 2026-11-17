import React, { useEffect, useState } from 'react';
import {
  ArrowLeftRight,
  BarChart3,
  Calendar,
  ChevronLeft,
  ChevronRight,
  Menu,
  Scale,
  Shield,
  ShieldCheck,
  Trophy,
  User,
  X,
} from 'lucide-react';
import { useCompetition } from '../context/competitionState';

export default function Sidebar({
  activeTab,
  setActiveTab,
  collapsed,
  setCollapsed,
}) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { activeCompetition, hasAudit } = useCompetition();

  useEffect(() => {
    if (!mobileOpen) return undefined;
    const onKeyDown = (e) => {
      if (e.key === 'Escape') setMobileOpen(false);
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [mobileOpen]);

  const sections = [
    {
      title: 'Turnuva',
      items: [
        { id: 'fixtures', label: 'Fikstür & Günler', icon: Calendar },
        { id: 'teams', label: 'Takım Profilleri', icon: Shield },
        { id: 'players', label: 'Oyuncu Profilleri', icon: User },
        { id: 'player-compare', label: 'Oyuncu Karşılaştırma', icon: ArrowLeftRight },
      ],
    },
    {
      title: 'Analitik',
      items: [
        { id: 'referees', label: 'Hakem Profilleri', icon: Scale },
        { id: 'stats', label: 'İstatistikler', icon: BarChart3 },
        ...(hasAudit ? [{ id: 'audit', label: 'Model Takibi', icon: ShieldCheck }] : []),
      ],
    },
  ];

  const handleNavClick = (tabId) => {
    setActiveTab(tabId);
    setMobileOpen(false);
  };

  return (
    <>
      {/* Mobile Top Header */}
      <header className="lg:hidden fixed top-0 left-0 right-0 h-16 bg-background-primary border-b border-border z-40 px-4 flex items-center justify-between">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-8 h-8 rounded bg-accent text-white flex items-center justify-center shrink-0 transition-colors">
            <Trophy className="w-4 h-4 text-white" strokeWidth={1.5} aria-hidden="true" />
          </div>
          <span className="text-sm font-semibold text-text-primary leading-tight truncate">
            {activeCompetition.name}
          </span>
        </div>

        <button
          type="button"
          onClick={() => setMobileOpen(!mobileOpen)}
          className="p-2 rounded bg-background-tertiary hover:bg-border text-text-secondary hover:text-text-primary transition-colors cursor-pointer"
          aria-expanded={mobileOpen}
          aria-label={mobileOpen ? 'Menüyü kapat' : 'Menüyü aç'}
        >
          {mobileOpen ? <X className="w-5 h-5" strokeWidth={1.5} aria-hidden="true" /> : <Menu className="w-5 h-5" strokeWidth={1.5} aria-hidden="true" />}
        </button>
      </header>

      {/* Mobile Backdrop */}
      {mobileOpen && (
        <div
          aria-hidden="true"
          className="lg:hidden fixed inset-0 bg-black/50 z-40"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Main Sidebar (Desktop collapsible rail w-60/w-16 matching nbaModelApp; mobile drawer) */}
      <aside
        aria-label="Kenar çubuğu"
        className={`fixed top-0 bottom-0 left-0 bg-background-primary border-r border-border z-50 flex flex-col justify-between transition-all duration-200 ease-out motion-reduce:transition-none ${
          collapsed ? 'w-60 lg:w-16' : 'w-60'
        } ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        <div className="flex flex-col h-full overflow-y-auto overflow-x-hidden">
          {/* Logo & Branding */}
          <div className={`h-16 flex items-center border-b border-border-light shrink-0 ${collapsed ? 'px-3 lg:justify-center' : 'px-4 justify-between gap-2'}`}>
            <div className={`flex items-center gap-2.5 min-w-0 ${collapsed ? 'lg:hidden' : ''}`}>
              <div className="w-8 h-8 rounded bg-accent text-white flex items-center justify-center shrink-0 transition-colors">
                <Trophy className="w-4 h-4 text-white" strokeWidth={1.5} aria-hidden="true" />
              </div>
              <div className="min-w-0">
                <span className="block font-semibold text-sm tracking-tight text-text-primary leading-tight truncate">
                  {activeCompetition.name}
                </span>
                <p className="text-xs text-text-muted truncate">{activeCompetition.country}</p>
              </div>
            </div>

            {collapsed && (
              <div className="hidden lg:flex w-8 h-8 rounded bg-accent text-white items-center justify-center shrink-0" title={activeCompetition.name}>
                <Trophy className="w-4 h-4 text-white" strokeWidth={1.5} aria-hidden="true" />
              </div>
            )}

            <button
              type="button"
              onClick={() => setCollapsed(!collapsed)}
              className="hidden lg:inline-flex p-1.5 rounded hover:bg-background-tertiary text-text-secondary hover:text-text-primary transition-colors cursor-pointer shrink-0"
              aria-label={collapsed ? 'Kenar çubuğunu genişlet' : 'Kenar çubuğunu daralt'}
              title={collapsed ? 'Kenar çubuğunu genişlet' : 'Kenar çubuğunu daralt'}
            >
              {collapsed ? (
                <ChevronRight className="w-4 h-4" strokeWidth={1.5} aria-hidden="true" />
              ) : (
                <ChevronLeft className="w-4 h-4" strokeWidth={1.5} aria-hidden="true" />
              )}
            </button>
          </div>

          {/* Navigation Sections */}
          <div className="py-4 px-2.5 flex-1 space-y-5">
            {sections.map((section) => (
              <div key={section.title} className="space-y-1">
                {!collapsed && (
                  <span className="text-xs font-semibold text-text-muted block mb-1.5 px-2.5">
                    {section.title}
                  </span>
                )}
                <nav aria-label={section.title} className="space-y-1">
                  {section.items.map((item) => {
                    const Icon = item.icon;
                    const isActive = activeTab === item.id;

                    return (
                      <button
                        type="button"
                        key={item.id}
                        aria-current={isActive ? 'page' : undefined}
                        title={collapsed ? item.label : undefined}
                        onClick={() => handleNavClick(item.id)}
                        className={`w-full flex items-center rounded py-2.5 text-xs font-medium transition-colors duration-150 group cursor-pointer ${
                          collapsed ? 'lg:justify-center lg:px-0 px-3 gap-3' : 'justify-start px-3 gap-3'
                        } ${
                          isActive
                            ? 'bg-accent text-white'
                            : 'text-text-secondary hover:text-text-primary hover:bg-background-tertiary'
                        }`}
                      >
                        <Icon
                          className={`w-4 h-4 shrink-0 ${isActive ? 'text-white' : 'text-text-tertiary group-hover:text-text-primary'}`}
                          strokeWidth={1.5}
                          aria-hidden="true"
                        />
                        <span className={collapsed ? 'lg:hidden truncate' : 'truncate'}>{item.label}</span>
                      </button>
                    );
                  })}
                </nav>
              </div>
            ))}
          </div>
        </div>
      </aside>
    </>
  );
}
