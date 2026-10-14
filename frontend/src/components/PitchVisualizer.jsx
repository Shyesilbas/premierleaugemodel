import React, { useState } from 'react';
import { TEAMS } from '../data/teams';
import { Flag, Activity, Target, Shield, Info } from 'lucide-react';

export default function PitchVisualizer() {
  const [selectedZone, setSelectedZone] = useState('corners'); // 'corners' | 'throws' | 'shots'
  const [homeTeam, setHomeTeam] = useState(TEAMS[0]); // Arsenal
  const [awayTeam, setAwayTeam] = useState(TEAMS[11]); // Liverpool

  return (
    <div className="space-y-6">
      
      {/* Control Bar */}
      <div className="bg-[#0b0f19]/80 border border-white/10 rounded-2xl p-4 backdrop-blur-xl flex flex-col md:flex-row items-center justify-between gap-4">
        
        {/* Teams Selector */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <img src={homeTeam.badge} alt={homeTeam.name} className="w-7 h-7 object-contain" />
            <select
              value={homeTeam.id}
              onChange={(e) => setHomeTeam(TEAMS.find(t => t.id === Number(e.target.value)) || TEAMS[0])}
              className="bg-[#121724] border border-white/10 rounded-lg px-2.5 py-1.5 text-xs font-bold text-white outline-none cursor-pointer"
            >
              {TEAMS.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select>
          </div>
          <span className="text-xs font-bold text-slate-500">VS</span>
          <div className="flex items-center gap-2">
            <img src={awayTeam.badge} alt={awayTeam.name} className="w-7 h-7 object-contain" />
            <select
              value={awayTeam.id}
              onChange={(e) => setAwayTeam(TEAMS.find(t => t.id === Number(e.target.value)) || TEAMS[1])}
              className="bg-[#121724] border border-white/10 rounded-lg px-2.5 py-1.5 text-xs font-bold text-white outline-none cursor-pointer"
            >
              {TEAMS.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select>
          </div>
        </div>

        {/* Tactical Layer Switcher */}
        <div className="flex items-center bg-black/40 p-1 rounded-xl border border-white/5 gap-1">
          <button
            onClick={() => setSelectedZone('corners')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              selectedZone === 'corners'
                ? 'bg-[#00ff87] text-black shadow-md shadow-[#00ff87]/20'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Flag className="w-3.5 h-3.5" />
            <span>Korner Yayları & Ceza Sahası</span>
          </button>
          <button
            onClick={() => setSelectedZone('throws')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              selectedZone === 'throws'
                ? 'bg-[#04f5ff] text-black shadow-md shadow-[#04f5ff]/20'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            <span>Taç Baskı Kanatları</span>
          </button>
          <button
            onClick={() => setSelectedZone('shots')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              selectedZone === 'shots'
                ? 'bg-rose-500 text-white shadow-md shadow-rose-500/20'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Target className="w-3.5 h-3.5" />
            <span>Şut Tehlike Bölgeleri</span>
          </button>
        </div>

      </div>

      {/* Football Pitch Container */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Pitch Graphic (2 cols) */}
        <div className="lg:col-span-2 bg-[#0b0f19]/90 border border-white/10 rounded-3xl p-6 backdrop-blur-xl relative flex flex-col items-center">
          
          <div className="w-full max-w-2xl aspect-[1.5/1] rounded-2xl relative overflow-hidden shadow-2xl pitch-surface border-2 border-white/20 select-none">
            
            {/* Center Line */}
            <div className="absolute top-0 bottom-0 left-1/2 -translate-x-1/2 w-0.5 bg-white/40" />
            
            {/* Center Circle */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-28 h-28 rounded-full border-2 border-white/40 flex items-center justify-center">
              <div className="w-2 h-2 rounded-full bg-white/70" />
            </div>

            {/* Left Penalty Box (Home Defense / Away Attack) */}
            <div className="absolute top-1/2 -translate-y-1/2 left-0 w-28 h-48 border-r-2 border-y-2 border-white/40">
              {/* 6-Yard Box */}
              <div className="absolute top-1/2 -translate-y-1/2 left-0 w-10 h-24 border-r-2 border-y-2 border-white/40" />
              {/* Penalty Spot */}
              <div className="absolute top-1/2 -translate-y-1/2 right-6 w-2 h-2 rounded-full bg-white/70" />
            </div>

            {/* Right Penalty Box (Away Defense / Home Attack) */}
            <div className="absolute top-1/2 -translate-y-1/2 right-0 w-28 h-48 border-l-2 border-y-2 border-white/40">
              {/* 6-Yard Box */}
              <div className="absolute top-1/2 -translate-y-1/2 right-0 w-10 h-24 border-l-2 border-y-2 border-white/40" />
              {/* Penalty Spot */}
              <div className="absolute top-1/2 -translate-y-1/2 left-6 w-2 h-2 rounded-full bg-white/70" />
            </div>

            {/* Corner Arcs */}
            <div className="absolute top-0 left-0 w-6 h-6 border-b-2 border-r-2 border-white/50 rounded-br-full" />
            <div className="absolute bottom-0 left-0 w-6 h-6 border-t-2 border-r-2 border-white/50 rounded-tr-full" />
            <div className="absolute top-0 right-0 w-6 h-6 border-b-2 border-l-2 border-white/50 rounded-bl-full" />
            <div className="absolute bottom-0 right-0 w-6 h-6 border-t-2 border-l-2 border-white/50 rounded-tl-full" />

            {/* INTERACTIVE OVERLAYS BASED ON SELECTED LAYER */}
            {selectedZone === 'corners' && (
              <>
                {/* 4 Corner Hotspots */}
                <div className="absolute top-1 left-1 flex items-center gap-1 bg-[#00ff87]/90 text-black text-[10px] font-black px-1.5 py-0.5 rounded shadow animate-pulse">
                  <Flag className="w-3 h-3" /> 2.4 Korner
                </div>
                <div className="absolute bottom-1 left-1 flex items-center gap-1 bg-[#00ff87]/90 text-black text-[10px] font-black px-1.5 py-0.5 rounded shadow animate-pulse">
                  <Flag className="w-3 h-3" /> 2.5 Korner
                </div>
                <div className="absolute top-1 right-1 flex items-center gap-1 bg-[#00ff87]/90 text-black text-[10px] font-black px-1.5 py-0.5 rounded shadow animate-pulse">
                  <Flag className="w-3 h-3" /> 2.8 Korner
                </div>
                <div className="absolute bottom-1 right-1 flex items-center gap-1 bg-[#00ff87]/90 text-black text-[10px] font-black px-1.5 py-0.5 rounded shadow animate-pulse">
                  <Flag className="w-3 h-3" /> 2.7 Korner
                </div>

                {/* Box Danger Area */}
                <div className="absolute top-1/2 -translate-y-1/2 right-2 w-32 h-44 rounded-xl bg-[#00ff87]/15 border border-[#00ff87]/40 flex flex-col items-center justify-center p-2 text-center pointer-events-none">
                  <span className="text-[11px] font-extrabold text-[#00ff87]">Orta & Kafa Hedefi</span>
                  <span className="text-[9px] text-white/80">%78 Kutu İçi İsabet</span>
                </div>
              </>
            )}

            {selectedZone === 'throws' && (
              <>
                {/* Touchlines (Top & Bottom) */}
                <div className="absolute top-1 left-16 right-16 h-4 bg-[#04f5ff]/20 border border-[#04f5ff]/50 rounded-full flex items-center justify-center">
                  <span className="text-[9px] font-mono font-bold text-[#04f5ff]">Üst Taç Hattı (~17.2 Taç / Maç)</span>
                </div>
                <div className="absolute bottom-1 left-16 right-16 h-4 bg-[#04f5ff]/20 border border-[#04f5ff]/50 rounded-full flex items-center justify-center">
                  <span className="text-[9px] font-mono font-bold text-[#04f5ff]">Alt Taç Hattı (~15.7 Taç / Maç)</span>
                </div>
              </>
            )}

            {selectedZone === 'shots' && (
              <>
                {/* Central Danger Shot Area */}
                <div className="absolute top-1/2 -translate-y-1/2 right-6 w-24 h-24 rounded-full bg-rose-500/25 border border-rose-500/60 flex flex-col items-center justify-center text-center animate-pulse">
                  <span className="text-[10px] font-extrabold text-white">Tehlikeli Şut Bölgesi</span>
                  <span className="text-[8px] text-rose-200">14.2 Şut</span>
                </div>

                {/* Outside Box Area */}
                <div className="absolute top-1/2 -translate-y-1/2 right-36 w-20 h-32 rounded-xl bg-amber-500/20 border border-amber-500/50 flex flex-col items-center justify-center text-center">
                  <span className="text-[9px] font-bold text-amber-300">Ceza Sahası Dışı</span>
                  <span className="text-[8px] text-slate-300">Uzaktan Şut</span>
                </div>
              </>
            )}

          </div>

          <div className="flex items-center justify-between w-full mt-4 text-xs text-slate-400">
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: homeTeam.color }} />
              <strong>{homeTeam.name}</strong> Savunma Alanı
            </span>
            <span className="flex items-center gap-1.5">
              <strong>{awayTeam.name}</strong> Savunma Alanı
              <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: awayTeam.color }} />
            </span>
          </div>

        </div>

        {/* Tactical Insights Sidebar */}
        <div className="bg-[#0b0f19]/90 border border-white/10 rounded-3xl p-6 backdrop-blur-xl flex flex-col justify-between space-y-4">
          <div>
            <div className="flex items-center gap-2 mb-4">
              <Info className="w-4 h-4 text-[#00ff87]" />
              <h3 className="text-sm font-bold uppercase tracking-wider text-white">
                Opta Taktiksel Metrikler
              </h3>
            </div>

            <div className="space-y-4">
              <div className="p-3.5 rounded-xl bg-white/5 border border-white/5 space-y-1.5">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-400">Ceza Sahasına Korner Ortaları</span>
                  <span className="font-mono font-bold text-[#00ff87]">8.2 / Maç</span>
                </div>
                <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
                  <div className="h-full bg-[#00ff87] w-[75%]" />
                </div>
                <p className="text-[10px] text-slate-500">Ortalama %79 korner doğrudan ceza sahasına kavisli kesilmektedir.</p>
              </div>

              <div className="p-3.5 rounded-xl bg-white/5 border border-white/5 space-y-1.5">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-400">Taç İsabet Oranı</span>
                  <span className="font-mono font-bold text-[#04f5ff]">%89.4</span>
                </div>
                <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
                  <div className="h-full bg-[#04f5ff] w-[89%]" />
                </div>
                <p className="text-[10px] text-slate-500">Baskı altındaki taçların %10.6'sı top kaybı veya rakip tacına dönüşür.</p>
              </div>

              <div className="p-3.5 rounded-xl bg-white/5 border border-white/5 space-y-1.5">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-400">Ceza Sahası İçi Şut Oranı</span>
                  <span className="font-mono font-bold text-rose-400">%61.8</span>
                </div>
                <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
                  <div className="h-full bg-rose-500 w-[62%]" />
                </div>
                <p className="text-[10px] text-slate-500">Gole dönüşüm ve kaleci kurtarışlarının %82'si ceza sahası içindedir.</p>
              </div>
            </div>
          </div>

          <div className="p-3 rounded-xl bg-gradient-to-r from-purple-900/30 to-black/40 border border-purple-500/20 text-xs text-purple-200">
            <strong>Taktik Notu:</strong> PulseLive koordinat ve olay akışına göre Premier League'de kornerlerin %48'i ön direk varyasyonlarıyla sonuçlanmaktadır.
          </div>
        </div>

      </div>

    </div>
  );
}
