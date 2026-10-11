import React, { useState, useEffect } from 'react';
import { TEAMS, getTeam } from '../data/teams';
import { Shield, Trophy, Users, Calendar, ChevronRight, Activity, Target, Flag, MapPin } from 'lucide-react';
import MatchDetailModal from './MatchDetailModal';

export default function TeamProfilesTab({ selectedSeason }) {
  const [selectedTeamId, setSelectedTeamId] = useState(1); // Default Arsenal
  const [teamSeason, setTeamSeason] = useState(selectedSeason === '2026_27' ? '2025_26' : selectedSeason);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeModalMatch, setActiveModalMatch] = useState(null);

  useEffect(() => {
    // If incoming prop changes and isn't 2026_27, keep in sync
    if (selectedSeason && selectedSeason !== '2026_27') {
      setTeamSeason(selectedSeason);
    }
  }, [selectedSeason]);

  useEffect(() => {
    setLoading(true);
    fetch(`/api/teams/profile?team_id=${selectedTeamId}&season=${teamSeason}`)
      .then(res => res.json())
      .then(data => {
        setProfile(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Error fetching team profile:', err);
        setLoading(false);
      });
  }, [selectedTeamId, teamSeason]);

  const currentMeta = getTeam(selectedTeamId);

  return (
    <div className="space-y-6">

      {/* Team Selection Carousel / Grid */}
      <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm">
        <div className="flex items-center justify-between mb-3 px-1">
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-[#38003c]" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">
              Kulüp Seçin
            </h3>
          </div>
          <span className="text-[11px] text-slate-500 font-medium">20 Premier League Takımı</span>
        </div>

        <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-thin">
          {TEAMS.map(t => {
            const isSelected = t.id === selectedTeamId;
            return (
              <button
                key={t.id}
                onClick={() => setSelectedTeamId(t.id)}
                className={`flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-bold transition-all shrink-0 border ${
                  isSelected
                    ? 'bg-[#38003c] text-white border-[#38003c] shadow-sm'
                    : 'bg-slate-50 hover:bg-slate-100 text-slate-700 border-slate-200'
                }`}
              >
                <img 
                  src={t.badge} 
                  alt={t.name} 
                  className="w-5 h-5 object-contain"
                  onError={(e) => { e.target.src = '/badges/1.svg'; }}
                />
                <span className="truncate max-w-[110px]">{t.short || t.name}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Team Profile Hero & Record Card */}
      {profile && (
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-5">
            <div className="w-20 h-20 rounded-2xl bg-slate-50 border border-slate-200 p-2 flex items-center justify-center shrink-0 shadow-inner">
              <img 
                src={currentMeta.badge} 
                alt={currentMeta.name} 
                className="w-16 h-16 object-contain" 
              />
            </div>
            <div>
              <div className="flex items-center gap-2 mb-1">
                <h2 className="text-2xl font-black text-slate-900 tracking-tight">
                  {currentMeta.name}
                </h2>
                <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                  {currentMeta.abbr}
                </span>
              </div>
              <p className="text-xs text-slate-500 font-medium flex items-center gap-1">
                <MapPin className="w-3.5 h-3.5 text-slate-400" /> {currentMeta.stadium || 'Premier League Stadium'}
              </p>
            </div>
          </div>

          {/* Season Switcher & Stats Pills */}
          <div className="flex flex-col items-end gap-3 w-full md:w-auto">
            <div className="flex items-center bg-slate-100 p-1 rounded-xl border border-slate-200 gap-1">
              <button
                onClick={() => setTeamSeason('2026_27')}
                className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                  teamSeason === '2026_27'
                    ? 'bg-[#38003c] text-white shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                2026-27
              </button>
              <button
                onClick={() => setTeamSeason('2025_26')}
                className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                  teamSeason === '2025_26'
                    ? 'bg-[#38003c] text-white shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                2025-26
              </button>
              <button
                onClick={() => setTeamSeason('2024_25')}
                className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                  teamSeason === '2024_25'
                    ? 'bg-[#38003c] text-white shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                2024-25
              </button>
              <button
                onClick={() => setTeamSeason('all')}
                className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                  teamSeason === 'all'
                    ? 'bg-[#38003c] text-white shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Tümü
              </button>
            </div>

            {/* Record Pills */}
            {profile.record && (
              <div className="flex items-center gap-2 font-mono text-xs">
                <div className="bg-emerald-50 border border-emerald-200 px-3 py-1 rounded-xl text-center">
                  <span className="text-[10px] text-emerald-700 font-sans block">GALİBİYET</span>
                  <strong className="text-emerald-800 text-sm font-bold">{profile.record.wins}</strong>
                </div>
                <div className="bg-slate-100 border border-slate-200 px-3 py-1 rounded-xl text-center">
                  <span className="text-[10px] text-slate-500 font-sans block">BERABERLİK</span>
                  <strong className="text-slate-800 text-sm font-bold">{profile.record.draws}</strong>
                </div>
                <div className="bg-rose-50 border border-rose-200 px-3 py-1 rounded-xl text-center">
                  <span className="text-[10px] text-rose-700 font-sans block">MAĞLUBİYET</span>
                  <strong className="text-rose-800 text-sm font-bold">{profile.record.losses}</strong>
                </div>
                <div className="bg-purple-50 border border-purple-200 px-3 py-1 rounded-xl text-center">
                  <span className="text-[10px] text-purple-700 font-sans block">GOL (AV)</span>
                  <strong className="text-purple-900 text-sm font-bold">
                    {profile.record.gf}:{profile.record.ga}
                  </strong>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Main Content: League Matches Preview List */}
      <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-[#38003c]" />
            <h3 className="text-sm font-black text-slate-900">
              {currentMeta.name} — Sezon Lig Maçları ve Skor Önizlemeleri
            </h3>
          </div>
          <span className="text-xs font-mono font-bold text-slate-500">
            {profile?.matches?.length || 0} Maç
          </span>
        </div>

        {loading ? (
          <div className="py-16 text-center">
            <div className="w-7 h-7 border-3 border-[#38003c] border-t-transparent rounded-full animate-spin mx-auto mb-2" />
            <p className="text-xs font-bold text-slate-600">Takım maçları yükleniyor...</p>
          </div>
        ) : !profile?.matches?.length ? (
          <div className="py-12 text-center text-xs text-slate-500 font-medium">
            Bu sezon için kayıtlı maç bulunamadı.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
            {profile.matches.map(m => {
              const opp = getTeam(m.opponent_id, m.opponent_name);
              const isWin = m.result === 'W';
              const isDraw = m.result === 'D';
              const isLoss = m.result === 'L';

              const resBadgeClass = isWin 
                ? 'bg-emerald-100 text-emerald-800 border-emerald-200' 
                : isDraw 
                ? 'bg-slate-100 text-slate-700 border-slate-300' 
                : 'bg-rose-100 text-rose-800 border-rose-200';

              const resLabel = isWin ? 'G' : isDraw ? 'B' : 'M';

              // Synthetic match object for MatchDetailModal
              const modalMatchObj = {
                match_id: m.match_id,
                status: (m.team_score !== null && m.team_score !== undefined) ? 'COMPLETED' : (m.status || 'UNPLAYED'),
                gameweek: m.gameweek,
                kickoff_label: m.kickoff_label,
                home_id: m.is_home ? selectedTeamId : m.opponent_id,
                home_name: m.is_home ? currentMeta.name : m.opponent_name,
                home_score: m.is_home ? m.team_score : m.opp_score,
                away_id: m.is_home ? m.opponent_id : selectedTeamId,
                away_name: m.is_home ? m.opponent_name : currentMeta.name,
                away_score: m.is_home ? m.opp_score : m.team_score,
                ground_name: m.is_home ? currentMeta.stadium : opp.stadium,
              };

              return (
                <div
                  key={m.match_id}
                  onClick={() => setActiveModalMatch(modalMatchObj)}
                  className="p-3.5 rounded-xl border border-slate-200 hover:border-slate-400 hover:shadow-md transition-all cursor-pointer group bg-slate-50/50 hover:bg-white flex flex-col justify-between gap-2.5"
                >
                  {/* Top info */}
                  <div className="flex items-center justify-between text-[11px] text-slate-500 pb-2 border-b border-slate-200/60">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-slate-700">Hafta {m.gameweek}</span>
                      <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-200 text-slate-700 font-medium">
                        {m.is_home ? 'İç Saha' : 'Deplasman'}
                      </span>
                    </div>
                    <span className="text-[11px] font-bold text-[#38003c] group-hover:translate-x-0.5 transition-transform flex items-center gap-0.5">
                      Detay & İstatistikler <ChevronRight className="w-3.5 h-3.5" />
                    </span>
                  </div>

                  {/* Teams & Score Preview */}
                  <div className="flex items-center justify-between py-1">
                    {/* Club */}
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      <img 
                        src={currentMeta.badge} 
                        alt={currentMeta.name} 
                        className="w-6 h-6 object-contain shrink-0" 
                      />
                      <span className="font-bold text-xs text-slate-900 truncate">
                        {currentMeta.short || currentMeta.name}
                      </span>
                    </div>

                    {/* Result badge & Score */}
                    <div className="flex items-center gap-2 px-2 shrink-0">
                      <span className={`text-[10px] font-mono font-black px-1.5 py-0.5 rounded border ${resBadgeClass}`}>
                        {resLabel}
                      </span>
                      <div className="px-2.5 py-1 rounded-lg bg-white border border-slate-300 font-mono font-black text-sm text-slate-900">
                        {m.team_score} - {m.opp_score}
                      </div>
                    </div>

                    {/* Opponent */}
                    <div className="flex items-center gap-2 flex-1 min-w-0 justify-end text-right">
                      <span className="font-bold text-xs text-slate-800 truncate">
                        {opp.short || opp.name}
                      </span>
                      <img 
                        src={opp.badge} 
                        alt={opp.name} 
                        className="w-6 h-6 object-contain shrink-0"
                        onError={(e) => { e.target.src = '/badges/1.svg'; }}
                      />
                    </div>
                  </div>

                  {/* Micro stats */}
                  <div className="grid grid-cols-3 gap-1 pt-1.5 border-t border-slate-200/60 text-[10px] font-mono text-center text-slate-600">
                    <span className="bg-white py-0.5 rounded border border-slate-200 flex items-center justify-center gap-1">
                      <Flag className="w-2.5 h-2.5 text-emerald-600" /> {m.total_corners ?? '-'} Korner
                    </span>
                    <span className="bg-white py-0.5 rounded border border-slate-200 flex items-center justify-center gap-1">
                      <Activity className="w-2.5 h-2.5 text-sky-600" /> {m.total_throws ?? '-'} Taç
                    </span>
                    <span className="bg-white py-0.5 rounded border border-slate-200 flex items-center justify-center gap-1">
                      <Target className="w-2.5 h-2.5 text-rose-600" /> {m.total_shots ?? '-'} Şut
                    </span>
                  </div>

                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Squad Roster Preview */}
      {profile?.squad && profile.squad.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-3">
          <div className="flex items-center gap-2 pb-2 border-b border-slate-100">
            <Users className="w-4 h-4 text-[#38003c]" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">
              {currentMeta.name} — Kadro Listesi ({profile.squad.length} Oyuncu)
            </h3>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2.5 pt-1">
            {profile.squad.map(p => (
              <div 
                key={p.id}
                className="p-2.5 rounded-xl bg-slate-50 border border-slate-200/80 hover:bg-white hover:border-slate-300 hover:shadow-xs transition-all flex flex-col justify-between"
              >
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-b from-slate-100 to-slate-200 border border-slate-300 overflow-hidden shrink-0 flex items-center justify-center shadow-inner">
                    {p.photo_url ? (
                      <img 
                        src={p.photo_url} 
                        alt={p.name} 
                        className="w-full h-full object-contain"
                        onError={(e) => { e.target.style.display = 'none'; }}
                        loading="lazy"
                      />
                    ) : (
                      <span className="font-mono text-xs font-black text-slate-600">#{p.shirt || '-'}</span>
                    )}
                  </div>
                  <div className="min-w-0">
                    <span className="font-mono text-xs font-black text-slate-900 block leading-tight">
                      #{p.shirt || '-'}
                    </span>
                    <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-200 text-slate-700 block mt-0.5 w-fit">
                      {p.position || 'O'}
                    </span>
                  </div>
                </div>
                <h4 className="font-bold text-xs text-slate-900 truncate" title={p.name}>
                  {p.name}
                </h4>
                <div className="flex items-center justify-between text-[10px] text-slate-500 mt-1.5 pt-1.5 border-t border-slate-200 font-mono">
                  <span>{p.total_appearances} Maç</span>
                  <span className="font-bold text-emerald-700">{p.total_goals} Gol</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Match Detail Modal */}
      {activeModalMatch && (
        <MatchDetailModal
          match={activeModalMatch}
          onClose={() => setActiveModalMatch(null)}
        />
      )}

    </div>
  );
}
