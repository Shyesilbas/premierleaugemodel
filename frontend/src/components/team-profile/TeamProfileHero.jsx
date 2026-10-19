import { ChevronDown, ChevronsUpDown, Coins, MapPin, Search, Shield, Trophy, X } from 'lucide-react';
import { handleTeamBadgeError } from '../../utils/imageFallbacks';
import TeamForm from '../TeamForm';
import { formatSeasonLabel } from '../../utils/dateFormatters';

export default function TeamProfileHero({ profile, currentMeta, selectedTeamId, onSelectTeam, teamSeason, setTeamSeason, setSelectedSeason, standingsMap, displayManager, onSelectManager, last5Matches, isTeamSelectorOpen, setIsTeamSelectorOpen, teamSearchQuery, setTeamSearchQuery, filteredClubs, teamSelectorRef }) {
  if (!profile) return null;

  return (
    <div className="relative py-1">
      <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
                
                {/* Left: Badge, Form Dots, Names, Stadium, Manager, League Standing & Club Switcher */}
                <div className="flex items-start sm:items-center gap-4 sm:gap-5 flex-1 min-w-0">
                  
                  {/* Badge with Click to Switch Team and Form Dots */}
                  <div className="flex flex-col items-center shrink-0">
                    <button
                      type="button"
                      onClick={() => setIsTeamSelectorOpen(prev => !prev)}
                      title="Kulüp değiştirmek için tıklayın"
                      className="w-20 h-20 rounded-2xl bg-slate-50 border border-slate-200 p-2 flex items-center justify-center shadow-inner hover:border-[#38003c] hover:shadow-md transition-all group relative cursor-pointer"
                    >
                      <img 
                        src={currentMeta.badge} 
                        alt={currentMeta.name} 
                        className="w-16 h-16 object-contain group-hover:scale-105 transition-transform" 
                      />
                      <div className="absolute inset-0 bg-black/5 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                        <ChevronsUpDown className="w-5 h-5 text-[#38003c] bg-white/90 rounded-full p-0.5 shadow-sm" />
                      </div>
                    </button>

                    {last5Matches.length > 0 && (
                      <TeamForm
                        className="mt-2"
                        itemClassName="shadow-2xs"
                        label="Son 5 maç formu"
                        results={last5Matches}
                        getKey={(item, index) => item.match_id || index}
                        getTitle={item => `vs ${item.opponent_name}: ${item.team_score}-${item.opp_score} (${item.result === 'W' ? 'Galibiyet' : item.result === 'D' ? 'Beraberlik' : 'Mağlubiyet'})`}
                      />
                    )}
                  </div>

                  {/* Team Info & Actions */}
                  <div className="min-w-0 flex-1 relative">
                    
                    {/* Team Name + Abbr + Quick Switcher Button */}
                    <div className="flex flex-wrap items-center gap-2 mb-1.5">
                      <h2 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight truncate">
                        {currentMeta.name}
                      </h2>
                      <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                        {currentMeta.abbr}
                      </span>

                      {/* Kulüp Değiştir Trigger Button & Popover */}
                      <div className="relative inline-block" ref={teamSelectorRef}>
                        <button
                          type="button"
                          onClick={() => setIsTeamSelectorOpen(prev => !prev)}
                          className={`flex items-center gap-1.5 px-2.5 py-1 rounded-xl text-xs font-bold transition-all border ${
                            isTeamSelectorOpen
                              ? 'bg-[#38003c] text-white border-[#38003c] shadow-xs'
                              : 'bg-slate-100 hover:bg-slate-200 text-slate-700 border-slate-200'
                          }`}
                          title="Premier League takımı seç"
                        >
                          <Shield className="w-3.5 h-3.5 text-[#38003c]" />
                          <span>Takım Değiştir</span>
                          <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-200 ${isTeamSelectorOpen ? 'rotate-180' : ''}`} />
                        </button>

                        {/* Team Selector Popover Dropdown */}
                        {isTeamSelectorOpen && (
                          <div className="absolute left-0 top-full mt-2 w-72 sm:w-80 bg-white border border-slate-200 rounded-2xl shadow-xl p-3 z-50 animate-in fade-in zoom-in-95 duration-150">
                            {/* Popover Header */}
                            <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-100">
                              <div className="flex items-center gap-1.5 text-xs font-bold text-slate-900">
                                <Trophy className="w-3.5 h-3.5 text-amber-500" />
                                <span>Premier League Kulüpleri</span>
                              </div>
                              <button
                                type="button"
                                onClick={() => setIsTeamSelectorOpen(false)}
                                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg text-xs"
                              >
                                <X className="w-3.5 h-3.5" />
                              </button>
                            </div>

                            {/* Search Bar */}
                            <div className="relative mb-2">
                              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
                              <input
                                type="text"
                                autoFocus
                                value={teamSearchQuery}
                                onChange={(e) => setTeamSearchQuery(e.target.value)}
                                placeholder="Takım ara (örn: Arsenal, MCI)..."
                                className="w-full bg-slate-50 border border-slate-200 rounded-xl pl-8 pr-2.5 py-1.5 text-xs text-slate-900 placeholder-slate-400 outline-none focus:border-[#38003c] focus:bg-white transition-all"
                              />
                            </div>

                            {/* Clubs List */}
                            <div className="max-h-60 overflow-y-auto space-y-1 scrollbar-thin pr-0.5">
                              {filteredClubs.map(club => {
                                const isSelected = Number(club.id) === Number(selectedTeamId);
                                const standing = standingsMap[club.id];
                                return (
                                  <button
                                    key={club.id}
                                    type="button"
                                    onClick={() => {
                                      onSelectTeam?.(club.id);
                                      setIsTeamSelectorOpen(false);
                                      setTeamSearchQuery('');
                                    }}
                                    className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-xl text-xs transition-all text-left ${
                                      isSelected
                                        ? 'bg-[#38003c] text-white font-bold shadow-xs'
                                        : 'hover:bg-slate-100 text-slate-700 hover:text-slate-950 font-medium'
                                    }`}
                                  >
                                    <div className="flex items-center gap-2 truncate">
                                      <img 
                                        src={club.badge} 
                                        alt={club.name} 
                                        className="w-4 h-4 object-contain shrink-0" 
                                        onError={handleTeamBadgeError}
                                      />
                                      <span className="truncate">{club.name}</span>
                                    </div>
                                    {standing && (
                                      <span className={`text-[10px] font-mono shrink-0 px-1.5 py-0.5 rounded font-bold ${
                                        isSelected ? 'bg-white/20 text-white' : 'bg-slate-100 text-slate-600'
                                      }`}>
                                        #{standing.rank} • {standing.points}P
                                      </span>
                                    )}
                                  </button>
                                );
                              })}
                              {filteredClubs.length === 0 && (
                                <p className="py-4 text-center text-xs text-slate-400">Eşleşen kulüp bulunamadı.</p>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Stadium & Manager */}
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500 font-medium mb-2">
                      <span className="flex items-center gap-1">
                        <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0" /> {currentMeta.stadium || 'Premier League Stadium'}
                      </span>
                      {displayManager?.name?.display && (
                        <span className="flex items-center gap-1">
                          <span className="text-slate-300">·</span>
                          <button 
                            type="button" 
                            onClick={() => onSelectManager(displayManager)} 
                            className="text-violet-800 font-semibold hover:text-violet-950 hover:underline" 
                            aria-label={`${displayManager.name.display} rakip performansını aç`}
                          >
                            {displayManager.name.display}
                          </button>
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Right: Season Switcher & Kadro Değeri Hero Card */}
                <div className="flex flex-col items-start lg:items-end gap-3 w-full lg:w-auto pt-4 lg:pt-0 border-t lg:border-t-0 border-slate-100">
                  <div className="relative">
                    <label htmlFor="team-profile-season" className="sr-only">Sezon seç</label>
                    <select
                      id="team-profile-season"
                      value={teamSeason}
                      onChange={(event) => {
                        const nextSeason = event.target.value;
                        setTeamSeason(nextSeason);
                        setSelectedSeason?.(nextSeason);
                      }}
                      className="appearance-none min-w-36 bg-slate-100 hover:bg-slate-200 border border-slate-200 rounded-xl pl-3 pr-9 py-2 text-xs font-bold text-slate-700 focus:outline-none focus:ring-2 focus:ring-[#38003c]/30 cursor-pointer"
                    >
                      {['2026_27', '2025_26', '2024_25', '2023_24', '2022_23', 'all'].map(season => (
                        <option key={season} value={season}>
                          {season === 'all' ? 'Tüm Sezonlar' : `${formatSeasonLabel(season)} Sezonu`}
                        </option>
                      ))}
                    </select>
                    <ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
                  </div>

                  {/* Prominent, Clean Kadro Değeri (Frameless / Minimalist) */}
                  {profile.market_value && (
                    <button 
                      type="button"
                      onClick={() => setShowMarketValueModal(true)}
                      className="text-left lg:text-right group p-1 -m-1 rounded-xl transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500/40"
                      title="5 yıllık piyasa değeri değişim grafiğini görüntülemek için tıklayın"
                    >
                      <div className="flex items-center lg:justify-end gap-1.5 text-xs text-slate-500">
                        <Coins className="w-3.5 h-3.5 text-amber-600 transition-transform group-hover:scale-110" />
                        <span className="text-[11px] font-semibold text-slate-600 uppercase tracking-wider group-hover:text-amber-700 transition-colors">
                          Kadro Değeri
                        </span>
                        <span className="text-slate-300">·</span>
                        <span className="text-[10px] font-medium text-slate-400 group-hover:text-slate-600 transition-colors">
                          Transfermarkt
                        </span>
                        <span className="text-[10px] font-bold text-amber-600 opacity-80 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all inline-flex items-center ml-0.5">
                          Grafik ↗
                        </span>
                      </div>
                      <div className="flex items-baseline lg:justify-end gap-2 mt-0.5">
                        <strong className="text-2xl sm:text-3xl font-black font-mono text-slate-900 group-hover:text-amber-700 tracking-tight transition-colors">
                          {profile.market_value.formatted}
                        </strong>
                        {profile.market_value.avg_formatted && (
                          <span className="text-xs font-mono text-slate-500 font-medium">
                            (Ort. {profile.market_value.avg_formatted})
                          </span>
                        )}
                      </div>
                    </button>
                  )}
                </div>

              </div>
            </div>
  );
}
