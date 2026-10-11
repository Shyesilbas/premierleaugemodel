import React, { useState, useEffect } from 'react';
import { TEAMS, getTeam } from '../data/teams';
import { Shield, Trophy, Users, Calendar, ChevronRight, Activity, Target, Flag, MapPin, Clock } from 'lucide-react';
import MatchDetailModal from './MatchDetailModal';

function parseKickoff(label) {
  if (!label) return { date: '-', time: '' };
  const parts = label.split(',');
  if (parts.length >= 2) {
    return {
      date: parts[0].trim(),
      time: parts[1].trim().replace(/\s+(BST|GMT)/gi, ''),
    };
  }
  return { date: label, time: '' };
}

export default function TeamProfilesTab({ selectedSeason }) {
  const [selectedTeamId, setSelectedTeamId] = useState(1); // Default Arsenal
  const [teamSeason, setTeamSeason] = useState(selectedSeason || '2026_27');
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeModalMatch, setActiveModalMatch] = useState(null);

  useEffect(() => {
    if (selectedSeason) {
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
          <div className="border border-slate-200 rounded-xl divide-y divide-slate-100 bg-white shadow-2xs overflow-hidden">
            {profile.matches.map(m => {
              const opp = getTeam(m.opponent_id, m.opponent_name);
              const isPlayed = (m.team_score !== null && m.team_score !== undefined);
              const isWin = m.result === 'W';
              const isDraw = m.result === 'D';
              const isLoss = m.result === 'L';

              const resBadgeClass = isWin 
                ? 'bg-emerald-100 text-emerald-800 border-emerald-300' 
                : isDraw 
                ? 'bg-slate-100 text-slate-700 border-slate-300' 
                : 'bg-rose-100 text-rose-800 border-rose-300';

              const resLabel = isWin ? 'G' : isDraw ? 'B' : 'M';
              const kickoff = parseKickoff(m.kickoff_label);

              const homeTeam = m.is_home ? currentMeta : opp;
              const awayTeam = m.is_home ? opp : currentMeta;
              const homeScore = m.is_home ? m.team_score : m.opp_score;
              const awayScore = m.is_home ? m.opp_score : m.team_score;

              // Synthetic match object for MatchDetailModal
              const modalMatchObj = {
                match_id: m.match_id,
                status: isPlayed ? 'COMPLETED' : (m.status || 'UNPLAYED'),
                gameweek: m.gameweek,
                kickoff_label: m.kickoff_label,
                home_id: homeTeam.id,
                home_name: homeTeam.name,
                home_score: homeScore,
                away_id: awayTeam.id,
                away_name: awayTeam.name,
                away_score: awayScore,
                ground_name: m.is_home ? currentMeta.stadium : opp.stadium,
              };

              return (
                <div
                  key={m.match_id}
                  onClick={() => setActiveModalMatch(modalMatchObj)}
                  className="px-3.5 py-2.5 hover:bg-slate-50/80 transition-colors cursor-pointer group flex items-center justify-between gap-3 text-xs"
                >
                  {/* 1. Tarih & Saat (En Başta) */}
                  <div className="flex items-center gap-2 min-w-[130px] sm:min-w-[160px] shrink-0">
                    <Clock className="w-3.5 h-3.5 text-slate-400 shrink-0 hidden sm:block" />
                    <div className="flex flex-col sm:flex-row sm:items-center gap-0.5 sm:gap-2">
                      <span className="font-bold text-slate-900 text-[11px] sm:text-xs whitespace-nowrap">
                        {kickoff.date}
                      </span>
                      {kickoff.time && (
                        <span className="font-mono text-slate-500 font-semibold text-[10px] sm:text-[11px] whitespace-nowrap">
                          {kickoff.time}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* 2. Hafta & Saha Rozeti */}
                  <div className="flex items-center gap-1.5 shrink-0 hidden sm:flex">
                    <span className="font-mono font-bold text-slate-700 bg-slate-100 px-1.5 py-0.5 rounded text-[10px]">
                      H{Math.round(Number(m.gameweek) || 1)}
                    </span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
                      m.is_home ? 'bg-sky-50 text-sky-700 border border-sky-200' : 'bg-slate-100 text-slate-600'
                    }`}>
                      {m.is_home ? 'İç' : 'Dep'}
                    </span>
                  </div>

                  {/* 3. Karşılaşma ve Skor (Ortada Tek Sıra) */}
                  <div className="flex items-center justify-center gap-2 sm:gap-3 flex-1 min-w-0">
                    {/* Ev Sahibi */}
                    <div className="flex items-center gap-1.5 justify-end flex-1 min-w-0 text-right">
                      <span className={`truncate text-xs ${homeTeam.id === selectedTeamId ? 'font-black text-slate-900' : 'font-medium text-slate-600'}`}>
                        {homeTeam.short || homeTeam.name}
                      </span>
                      <img 
                        src={homeTeam.badge} 
                        alt={homeTeam.name} 
                        className="w-5 h-5 object-contain shrink-0"
                        onError={(e) => { e.target.src = '/badges/1.svg'; }}
                      />
                    </div>

                    {/* Skor / Durum */}
                    <div className="shrink-0 flex items-center justify-center min-w-[55px]">
                      {isPlayed ? (
                        <span className="px-2 py-0.5 rounded bg-slate-900 text-white font-mono font-black text-xs tracking-wider shadow-2xs">
                          {homeScore} - {awayScore}
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-500 font-mono text-[10px] font-bold border border-slate-200">
                          {kickoff.time || 'vs'}
                        </span>
                      )}
                    </div>

                    {/* Deplasman */}
                    <div className="flex items-center gap-1.5 justify-start flex-1 min-w-0 text-left">
                      <img 
                        src={awayTeam.badge} 
                        alt={awayTeam.name} 
                        className="w-5 h-5 object-contain shrink-0"
                        onError={(e) => { e.target.src = '/badges/1.svg'; }}
                      />
                      <span className={`truncate text-xs ${awayTeam.id === selectedTeamId ? 'font-black text-slate-900' : 'font-medium text-slate-600'}`}>
                        {awayTeam.short || awayTeam.name}
                      </span>
                    </div>
                  </div>

                  {/* 4. Sonuç Rozeti (G/B/M) & Ok */}
                  <div className="flex items-center gap-2 shrink-0">
                    {isPlayed && (
                      <span className={`w-5 h-5 flex items-center justify-center text-[10px] font-mono font-black rounded border ${resBadgeClass}`}>
                        {resLabel}
                      </span>
                    )}
                    <ChevronRight className="w-3.5 h-3.5 text-slate-300 group-hover:text-slate-700 group-hover:translate-x-0.5 transition-all" />
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
