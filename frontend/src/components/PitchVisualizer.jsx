import React, { useState } from 'react';
import { TEAMS } from '../data/teams';
import { Activity, Flag, Info, Target } from 'lucide-react';

export default function PitchVisualizer() {
  const [selectedZone, setSelectedZone] = useState('corners'); // 'corners' | 'throws' | 'shots'
  const [homeTeam, setHomeTeam] = useState(TEAMS[0]);
  const [awayTeam, setAwayTeam] = useState(TEAMS[11]);

  return (
    <div className="space-y-6">
      {/* Control Bar */}
      <div className="bg-background-primary border border-border rounded p-4 flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Teams Selector */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <img src={homeTeam.badge} alt={homeTeam.name} className="w-7 h-7 object-contain" />
            <label htmlFor="pitch-home-team" className="visually-hidden">Ev sahibi takım</label>
            <select
              id="pitch-home-team"
              value={homeTeam.id}
              onChange={(e) => setHomeTeam(TEAMS.find(t => t.id === Number(e.target.value)) || TEAMS[0])}
              className="h-9 bg-background-primary border border-border rounded px-2.5 text-xs font-semibold text-text-primary outline-none cursor-pointer focus:border-border-focus"
            >
              {TEAMS.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select>
          </div>
          <span className="text-xs font-semibold text-text-secondary">VS</span>
          <div className="flex items-center gap-2">
            <img src={awayTeam.badge} alt={awayTeam.name} className="w-7 h-7 object-contain" />
            <label htmlFor="pitch-away-team" className="visually-hidden">Deplasman takımı</label>
            <select
              id="pitch-away-team"
              value={awayTeam.id}
              onChange={(e) => setAwayTeam(TEAMS.find(t => t.id === Number(e.target.value)) || TEAMS[1])}
              className="h-9 bg-background-primary border border-border rounded px-2.5 text-xs font-semibold text-text-primary outline-none cursor-pointer focus:border-border-focus"
            >
              {TEAMS.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select>
          </div>
        </div>

        {/* Tactical Layer Switcher */}
        <div role="tablist" aria-label="Taktik katman seçimi" className="flex flex-wrap items-center bg-background-tertiary p-1 rounded border border-border gap-1">
          <button
            type="button"
            role="tab"
            aria-selected={selectedZone === 'corners'}
            onClick={() => setSelectedZone('corners')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-semibold transition-colors cursor-pointer ${
              selectedZone === 'corners'
                ? 'bg-primary text-white'
                : 'text-text-secondary hover:text-text-primary hover:bg-background-primary'
            }`}
          >
            <Flag className="w-3.5 h-3.5" strokeWidth={1.5} aria-hidden="true" />
            <span>Korner Yayları &amp; Ceza Sahası</span>
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={selectedZone === 'throws'}
            onClick={() => setSelectedZone('throws')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-semibold transition-colors cursor-pointer ${
              selectedZone === 'throws'
                ? 'bg-primary text-white'
                : 'text-text-secondary hover:text-text-primary hover:bg-background-primary'
            }`}
          >
            <Activity className="w-3.5 h-3.5" strokeWidth={1.5} aria-hidden="true" />
            <span>Taç Baskı Kanatları</span>
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={selectedZone === 'shots'}
            onClick={() => setSelectedZone('shots')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-semibold transition-colors cursor-pointer ${
              selectedZone === 'shots'
                ? 'bg-status-error text-white'
                : 'text-text-secondary hover:text-text-primary hover:bg-background-primary'
            }`}
          >
            <Target className="w-3.5 h-3.5" strokeWidth={1.5} aria-hidden="true" />
            <span>Şut Tehlike Bölgeleri</span>
          </button>
        </div>
      </div>

      {/* Football Pitch Container */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Pitch Graphic (2 cols) */}
        <div className="lg:col-span-2 bg-background-primary border border-border rounded p-6 relative flex flex-col items-center">
          <div className="w-full max-w-2xl aspect-pitch-wide rounded relative overflow-hidden pitch-surface select-none">
            {/* Center Line */}
            <div className="absolute top-0 bottom-0 left-1/2 -translate-x-1/2 w-0.5 bg-white/40" />

            {/* Center Circle */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-28 h-28 rounded-full border-2 border-white/40 flex items-center justify-center">
              <div className="w-2 h-2 rounded-full bg-white/70" />
            </div>

            {/* Left Penalty Box (Home Defense / Away Attack) */}
            <div className="absolute top-1/2 -translate-y-1/2 left-0 w-28 h-48 border-r-2 border-y-2 border-white/40">
              <div className="absolute top-1/2 -translate-y-1/2 left-0 w-10 h-24 border-r-2 border-y-2 border-white/40" />
              <div className="absolute top-1/2 -translate-y-1/2 right-6 w-2 h-2 rounded-full bg-white/70" />
            </div>

            {/* Right Penalty Box (Away Defense / Home Attack) */}
            <div className="absolute top-1/2 -translate-y-1/2 right-0 w-28 h-48 border-l-2 border-y-2 border-white/40">
              <div className="absolute top-1/2 -translate-y-1/2 right-0 w-10 h-24 border-l-2 border-y-2 border-white/40" />
              <div className="absolute top-1/2 -translate-y-1/2 left-6 w-2 h-2 rounded-full bg-white/70" />
            </div>

            {/* Corner Arcs */}
            <div className="absolute top-0 left-0 w-6 h-6 border-b-2 border-r-2 border-white/50 rounded-br-full" />
            <div className="absolute bottom-0 left-0 w-6 h-6 border-t-2 border-r-2 border-white/50 rounded-tr-full" />
            <div className="absolute top-0 right-0 w-6 h-6 border-b-2 border-l-2 border-white/50 rounded-bl-full" />
            <div className="absolute bottom-0 right-0 w-6 h-6 border-t-2 border-l-2 border-white/50 rounded-tl-full" />

            {/* Interactive overlays */}
            {selectedZone === 'corners' && (
              <>
                <div className="absolute top-1.5 left-1.5 flex items-center gap-1 bg-background-primary text-text-primary border border-border text-xs font-semibold tabular-nums px-2 py-0.5 rounded-sm">
                  <Flag className="w-3 h-3 text-status-info" strokeWidth={1.5} aria-hidden="true" /> 2.4 Korner
                </div>
                <div className="absolute bottom-1.5 left-1.5 flex items-center gap-1 bg-background-primary text-text-primary border border-border text-xs font-semibold tabular-nums px-2 py-0.5 rounded-sm">
                  <Flag className="w-3 h-3 text-status-info" strokeWidth={1.5} aria-hidden="true" /> 2.5 Korner
                </div>
                <div className="absolute top-1.5 right-1.5 flex items-center gap-1 bg-background-primary text-text-primary border border-border text-xs font-semibold tabular-nums px-2 py-0.5 rounded-sm">
                  <Flag className="w-3 h-3 text-status-info" strokeWidth={1.5} aria-hidden="true" /> 2.8 Korner
                </div>
                <div className="absolute bottom-1.5 right-1.5 flex items-center gap-1 bg-background-primary text-text-primary border border-border text-xs font-semibold tabular-nums px-2 py-0.5 rounded-sm">
                  <Flag className="w-3 h-3 text-status-info" strokeWidth={1.5} aria-hidden="true" /> 2.7 Korner
                </div>

                <div className="absolute top-1/2 -translate-y-1/2 right-2 w-32 h-44 rounded bg-black/50 border border-white/40 flex flex-col items-center justify-center p-2 text-center pointer-events-none">
                  <span className="text-xs font-semibold text-white">Orta &amp; Kafa Hedefi</span>
                  <span className="text-xs text-white/90 tabular-nums mt-0.5">%78 Kutu İçi İsabet</span>
                </div>
              </>
            )}

            {selectedZone === 'throws' && (
              <>
                <div className="absolute top-1.5 left-16 right-16 py-0.5 bg-black/60 border border-white/40 rounded-full flex items-center justify-center">
                  <span className="text-xs font-mono font-medium tabular-nums text-white">Üst Taç Hattı (~17.2 Taç / Maç)</span>
                </div>
                <div className="absolute bottom-1.5 left-16 right-16 py-0.5 bg-black/60 border border-white/40 rounded-full flex items-center justify-center">
                  <span className="text-xs font-mono font-medium tabular-nums text-white">Alt Taç Hattı (~15.7 Taç / Maç)</span>
                </div>
              </>
            )}

            {selectedZone === 'shots' && (
              <>
                <div className="absolute top-1/2 -translate-y-1/2 right-6 w-24 h-24 rounded-full bg-status-error/70 border border-white/60 flex flex-col items-center justify-center text-center">
                  <span className="text-xs font-semibold text-white">Tehlikeli Bölge</span>
                  <span className="text-xs text-white/90 tabular-nums">14.2 Şut</span>
                </div>

                <div className="absolute top-1/2 -translate-y-1/2 right-36 w-20 h-32 rounded bg-status-warning/75 border border-white/60 flex flex-col items-center justify-center text-center px-1">
                  <span className="text-xs font-semibold text-white">Ceza Dışı</span>
                  <span className="text-xs text-white/90">Uzaktan Şut</span>
                </div>
              </>
            )}
          </div>

          <div className="flex items-center justify-between w-full mt-4 text-xs text-text-secondary">
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: homeTeam.color }} />
              <strong className="font-semibold text-text-primary">{homeTeam.name}</strong> Savunma Alanı
            </span>
            <span className="flex items-center gap-1.5">
              <strong className="font-semibold text-text-primary">{awayTeam.name}</strong> Savunma Alanı
              <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: awayTeam.color }} />
            </span>
          </div>
        </div>

        {/* Tactical Insights Sidebar */}
        <div className="bg-background-primary border border-border rounded p-6 flex flex-col justify-between space-y-4">
          <div>
            <div className="flex items-center gap-2 mb-4">
              <Info className="w-4 h-4 text-text-secondary" strokeWidth={1.5} aria-hidden="true" />
              <h3 className="text-sm font-semibold text-text-primary">
                Opta Taktiksel Metrikler
              </h3>
            </div>

            <div className="space-y-4">
              <div className="p-3.5 rounded bg-background-secondary border border-border-light space-y-1.5">
                <div className="flex justify-between text-xs">
                  <span className="text-text-secondary font-medium">Ceza Sahasına Korner Ortaları</span>
                  <span className="font-mono font-semibold tabular-nums text-text-primary">8.2 / Maç</span>
                </div>
                <div className="h-1.5 rounded-full bg-background-tertiary overflow-hidden">
                  <div className="h-full bg-primary w-3/4" />
                </div>
                <p className="text-xs text-text-secondary">Ortalama %79 korner doğrudan ceza sahasına kavisli kesilmektedir.</p>
              </div>

              <div className="p-3.5 rounded bg-background-secondary border border-border-light space-y-1.5">
                <div className="flex justify-between text-xs">
                  <span className="text-text-secondary font-medium">Taç İsabet Oranı</span>
                  <span className="font-mono font-semibold tabular-nums text-text-primary">%89.4</span>
                </div>
                <div className="h-1.5 rounded-full bg-background-tertiary overflow-hidden">
                  <div className="h-full bg-status-success w-5/6" />
                </div>
                <p className="text-xs text-text-secondary">Baskı altındaki taçların %10.6&apos;sı top kaybı veya rakip tacına dönüşür.</p>
              </div>

              <div className="p-3.5 rounded bg-background-secondary border border-border-light space-y-1.5">
                <div className="flex justify-between text-xs">
                  <span className="text-text-secondary font-medium">Ceza Sahası İçi Şut Oranı</span>
                  <span className="font-mono font-semibold tabular-nums text-status-error">%61.8</span>
                </div>
                <div className="h-1.5 rounded-full bg-background-tertiary overflow-hidden">
                  <div className="h-full bg-status-error w-3/5" />
                </div>
                <p className="text-xs text-text-secondary">Gole dönüşüm ve kaleci kurtarışlarının %82&apos;si ceza sahası içindedir.</p>
              </div>
            </div>
          </div>

          <div className="p-3 rounded bg-background-secondary border border-border text-xs text-text-secondary">
            <strong className="font-semibold text-text-primary">Taktik Notu:</strong> PulseLive koordinat ve olay akışına göre Premier League&apos;de kornerlerin %48&apos;i ön direk varyasyonlarıyla sonuçlanmaktadır.
          </div>
        </div>
      </div>
    </div>
  );
}
