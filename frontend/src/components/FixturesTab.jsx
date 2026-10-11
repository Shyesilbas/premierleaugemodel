import React, { useState, useEffect, useMemo } from 'react';
import { 
  Search, 
  Calendar, 
  ChevronRight, 
  Layers, 
  Clock, 
  MapPin, 
  Activity, 
  Target, 
  Flag, 
  Shield 
} from 'lucide-react';
import { getTeam } from '../data/teams';
import MatchDetailModal from './MatchDetailModal';

export default function FixturesTab({ selectedSeason, setSelectedSeason }) {
  const [data, setData] = useState({ gameweeks: [], total_matches: 0 });
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedGameweek, setSelectedGameweek] = useState('1'); // Default to GW 1
  const [activeModalMatch, setActiveModalMatch] = useState(null);

  useEffect(() => {
    setLoading(true);
    const seasonParam = selectedSeason || '2026_27';
    fetch(`/api/fixtures/grouped?season=${seasonParam}`)
      .then(res => res.json())
      .then(resData => {
        setData(resData || { gameweeks: [], total_matches: 0 });
        setLoading(false);
      })
      .catch(err => {
        console.error('Error fetching grouped fixtures:', err);
        setLoading(false);
      });
  }, [selectedSeason]);

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

  return (
    <div className="space-y-6">
      
      {/* Top Banner & Season Info */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Calendar className="w-5 h-5 text-[#38003c]" />
            <h2 className="text-lg font-black text-slate-900 tracking-tight">
              Premier League Fikstürü
            </h2>
            <span className="text-xs font-mono font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
              {selectedSeason === '2026_27' ? '2026-27 (Güncel Sezon)' : selectedSeason.replace('_', '-')}
            </span>
          </div>
          <p className="text-xs text-slate-500 font-medium">
            Hafta hafta ve günlere ayrılmış fikstür akışı. Maç kartına tıklayarak kadroları ve detayları inceleyebilirsiniz.
          </p>
        </div>

        {/* Season Quick Toggle */}
        <div className="flex items-center bg-slate-100 p-1 rounded-xl border border-slate-200 gap-1 self-stretch md:self-auto justify-center">
          <button
            onClick={() => setSelectedSeason('2026_27')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              selectedSeason === '2026_27'
                ? 'bg-[#38003c] text-white shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            2026-27 (Güncel)
          </button>
          <button
            onClick={() => setSelectedSeason('2025_26')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              selectedSeason === '2025_26'
                ? 'bg-[#38003c] text-white shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            2025-26
          </button>
          <button
            onClick={() => setSelectedSeason('2024_25')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              selectedSeason === '2024_25'
                ? 'bg-[#38003c] text-white shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            2024-25
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm flex flex-col gap-4">
        
        {/* Search Input */}
        <div className="relative w-full">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Takım veya stadyum ara (örn: Arsenal, Anfield, Chelsea)..."
            className="w-full bg-slate-50 border border-slate-200 rounded-xl pl-10 pr-4 py-2.5 text-xs font-medium text-slate-900 placeholder-slate-400 outline-none focus:border-[#38003c] focus:bg-white transition-all"
          />
        </div>

        {/* Gameweek Horizontal Selector */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 pt-1 border-t border-slate-100">
          <button
            onClick={() => setSelectedGameweek('all')}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all whitespace-nowrap ${
              selectedGameweek === 'all'
                ? 'bg-[#38003c] text-white shadow-sm'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            Tüm Haftalar
          </button>
          {allGwNumbers.map(gw => (
            <button
              key={gw}
              onClick={() => setSelectedGameweek(String(gw))}
              className={`px-3 py-1.5 rounded-xl text-xs font-mono font-bold transition-all whitespace-nowrap ${
                String(selectedGameweek) === String(gw)
                  ? 'bg-[#38003c] text-white shadow-sm'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200 hover:text-slate-900'
              }`}
            >
              Hafta {gw}
            </button>
          ))}
        </div>

      </div>

      {/* Gameweeks & Days Grouped View */}
      {loading ? (
        <div className="py-20 text-center bg-white border border-slate-200 rounded-2xl shadow-sm">
          <div className="w-8 h-8 border-3 border-[#38003c] border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-xs font-bold text-slate-700">Fikstür ve maç verileri yükleniyor...</p>
        </div>
      ) : filteredGameweeks.length === 0 ? (
        <div className="py-16 text-center bg-white border border-slate-200 rounded-2xl shadow-sm">
          <p className="text-sm font-bold text-slate-800">Aramanızla eşleşen maç bulunamadı.</p>
          <p className="text-xs text-slate-500 mt-1">Filtreleri temizleyip tekrar deneyin.</p>
        </div>
      ) : (
        <div className="space-y-8">
          {filteredGameweeks.map(gwObj => (
            <div key={gwObj.gameweek} className="space-y-4">
              
              {/* Gameweek Badge Header */}
              <div className="flex items-center justify-between bg-slate-200/70 border border-slate-300/80 px-4 py-2.5 rounded-xl">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#38003c]" />
                  <h3 className="text-sm font-black text-slate-900 tracking-tight">
                    Hafta {gwObj.gameweek}
                  </h3>
                </div>
                <span className="text-[11px] font-mono font-bold text-slate-600">
                  {gwObj.days.reduce((acc, d) => acc + d.matches.length, 0)} Karşılaşma
                </span>
              </div>

              {/* Day Groups inside Gameweek */}
              <div className="space-y-5 pl-1 md:pl-2">
                {gwObj.days.map((dayObj, dayIdx) => (
                  <div key={dayIdx} className="space-y-2.5">
                    
                    {/* Day Subheader */}
                    <div className="flex items-center gap-2 text-xs font-bold text-slate-700 px-1">
                      <Calendar className="w-3.5 h-3.5 text-[#38003c]" />
                      <span>{dayObj.day}</span>
                    </div>

                    {/* Matches Grid for that Day */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-3.5">
                      {dayObj.matches.map(m => {
                        const home = getTeam(m.home_id, m.home_name);
                        const away = getTeam(m.away_id, m.away_name);
                        const isCompleted = m.status === 'COMPLETED' && m.home_score !== null;

                        return (
                          <div
                            key={m.match_id}
                            onClick={() => setActiveModalMatch(m)}
                            className="bg-white border border-slate-200 hover:border-slate-400 rounded-2xl p-4 shadow-sm hover:shadow-md transition-all duration-200 cursor-pointer group flex flex-col justify-between gap-3"
                          >
                            
                            {/* Top Card Bar: Kickoff time & Ground */}
                            <div className="flex items-center justify-between text-[11px] text-slate-500 pb-2 border-b border-slate-100">
                              <div className="flex items-center gap-1.5 font-medium truncate max-w-[200px]">
                                <Clock className="w-3 h-3 text-slate-400 shrink-0" />
                                <span className="truncate">{m.time_label || m.kickoff_label}</span>
                              </div>

                              <span className="text-[11px] font-bold text-[#38003c] group-hover:translate-x-0.5 transition-transform flex items-center gap-1">
                                {isCompleted ? 'Kadrolar & Detay' : 'Model Maç Tahmini'} <ChevronRight className="w-3.5 h-3.5" />
                              </span>
                            </div>

                            {/* Teams & Score / Time */}
                            <div className="flex items-center justify-between gap-2 py-1">
                              
                              {/* Home Team */}
                              <div className="flex items-center gap-2.5 flex-1 min-w-0">
                                <img 
                                  src={home.badge} 
                                  alt={home.name} 
                                  className="w-7 h-7 object-contain shrink-0"
                                  onError={(e) => { e.target.src = '/badges/1.svg'; }}
                                />
                                <span className="font-bold text-xs text-slate-900 group-hover:text-[#38003c] transition-colors truncate">
                                  {home.name}
                                </span>
                              </div>

                              {/* Center: Score or Kickoff Time */}
                              <div className="shrink-0 px-3 py-1 rounded-xl bg-slate-100 border border-slate-200 font-mono font-black text-sm text-slate-900 text-center min-w-[64px]">
                                {isCompleted ? (
                                  <span>{m.home_score} - {m.away_score}</span>
                                ) : (
                                  <span className="text-xs font-bold text-slate-600">VS</span>
                                )}
                              </div>

                              {/* Away Team */}
                              <div className="flex items-center gap-2.5 flex-1 min-w-0 justify-end text-right">
                                <span className="font-bold text-xs text-slate-900 group-hover:text-[#38003c] transition-colors truncate">
                                  {away.name}
                                </span>
                                <img 
                                  src={away.badge} 
                                  alt={away.name} 
                                  className="w-7 h-7 object-contain shrink-0"
                                  onError={(e) => { e.target.src = '/badges/1.svg'; }}
                                />
                              </div>

                            </div>

                            {/* Bottom Bar: Completed Micro-stats OR Ground/Status */}
                            {isCompleted ? (
                              <div className="grid grid-cols-4 gap-1.5 pt-2 border-t border-slate-100 text-[10px] font-mono text-center">
                                <div className="bg-slate-50 py-1 px-1 rounded-lg">
                                  <span className="text-[9px] text-slate-500 font-sans block">KORNER</span>
                                  <strong className="text-emerald-700 font-bold">{m.home_won_corners ?? '-'} - {m.away_won_corners ?? '-'}</strong>
                                </div>
                                <div className="bg-slate-50 py-1 px-1 rounded-lg">
                                  <span className="text-[9px] text-slate-500 font-sans block">TAÇ</span>
                                  <strong className="text-sky-700 font-bold">{m.home_total_throws ?? '-'} - {m.away_total_throws ?? '-'}</strong>
                                </div>
                                <div className="bg-slate-50 py-1 px-1 rounded-lg">
                                  <span className="text-[9px] text-slate-500 font-sans block">ŞUT</span>
                                  <strong className="text-slate-800 font-bold">{m.total_shots ?? '-'}</strong>
                                </div>
                                <div className="bg-slate-50 py-1 px-1 rounded-lg">
                                  <span className="text-[9px] text-slate-500 font-sans block">KURTARIŞ</span>
                                  <strong className="text-purple-700 font-bold">{m.total_saves ?? '-'}</strong>
                                </div>
                              </div>
                            ) : (
                              <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
                                <span className="flex items-center gap-1 truncate">
                                  <MapPin className="w-3 h-3 text-slate-400" />
                                  <span className="truncate">{m.ground_name || 'Premier League Stadı'}</span>
                                </span>
                                <span className="text-[10px] font-bold text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-md">
                                  Yaklaşan Maç
                                </span>
                              </div>
                            )}

                          </div>
                        );
                      })}
                    </div>

                  </div>
                ))}
              </div>

            </div>
          ))}
        </div>
      )}

      {/* Match Detail & Lineup Modal */}
      {activeModalMatch && (
        <MatchDetailModal
          match={activeModalMatch}
          onClose={() => setActiveModalMatch(null)}
        />
      )}

    </div>
  );
}
