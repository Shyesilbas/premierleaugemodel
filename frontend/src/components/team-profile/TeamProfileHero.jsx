import { ChevronDown, ChevronsUpDown, Coins, MapPin, Search, Shield, Trophy, X } from 'lucide-react';
import { handleTeamBadgeError } from '../../utils/imageFallbacks';
import TeamForm from '../TeamForm';
import { formatSeasonLabel } from '../../utils/dateFormatters';

export default function TeamProfileHero({ profile, currentMeta, selectedTeamId, onSelectTeam, teamSeason, setTeamSeason, setSelectedSeason, standingsMap, displayManager, onSelectManager, last5Matches, isTeamSelectorOpen, setIsTeamSelectorOpen, teamSearchQuery, setTeamSearchQuery, filteredClubs, teamSelectorRef, setShowMarketValueModal }) {
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
              className="w-16 h-16 rounded bg-background-primary border border-border p-2 flex items-center justify-center hover:border-card-border-hover transition-colors group relative cursor-pointer"
            >
              <img 
                src={currentMeta.badge} 
                alt={currentMeta.name} 
                className="w-12 h-12 object-contain" 
              />
              <div className="absolute inset-0 bg-black/5 rounded opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                <ChevronsUpDown className="w-4 h-4 text-text-primary bg-background-primary rounded-full p-0.5" />
              </div>
            </button>

            {last5Matches.length > 0 && (
              <TeamForm
                className="mt-2"
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
              <h2 className="text-xl sm:text-2xl font-semibold text-text-primary tracking-tight truncate">
                {currentMeta.name}
              </h2>
              <span className="text-xs font-mono font-medium px-2 py-0.5 rounded-sm bg-background-tertiary text-text-secondary border border-border">
                {currentMeta.abbr}
              </span>

              {/* Kulüp Değiştir Trigger Button & Popover */}
              <div className="relative inline-block" ref={teamSelectorRef}>
                <button
                  type="button"
                  onClick={() => setIsTeamSelectorOpen(prev => !prev)}
                  className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium transition-colors border ${
                    isTeamSelectorOpen
                      ? 'bg-primary text-white border-primary'
                      : 'bg-background-tertiary hover:bg-border text-text-primary border-border'
                  }`}
                  title="Premier League takımı seç"
                >
                  <Shield className="w-3.5 h-3.5" />
                  <span>Takım Değiştir</span>
                  <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-200 ${isTeamSelectorOpen ? 'rotate-180' : ''}`} />
                </button>

                {/* Team Selector Popover Dropdown */}
                {isTeamSelectorOpen && (
                  <div className="absolute left-0 top-full mt-2 w-72 sm:w-80 bg-background-primary border border-border rounded-md shadow-md p-3 z-50">
                    {/* Popover Header */}
                    <div className="flex items-center justify-between pb-2 mb-2 border-b border-border-light">
                      <div className="flex items-center gap-1.5 text-xs font-semibold text-text-primary">
                        <Trophy className="w-3.5 h-3.5 text-text-primary" />
                        <span>Premier League Kulüpleri</span>
                      </div>
                      <button
                        type="button"
                        onClick={() => setIsTeamSelectorOpen(false)}
                        className="text-text-muted hover:text-text-primary p-1 rounded text-xs"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>

                    {/* Search Bar */}
                    <div className="relative mb-2">
                      <Search className="w-3.5 h-3.5 text-text-muted absolute left-2.5 top-1/2 -translate-y-1/2" />
                      <input
                        type="text"
                        autoFocus
                        value={teamSearchQuery}
                        onChange={(e) => setTeamSearchQuery(e.target.value)}
                        placeholder="Takım ara (örn: Arsenal, MCI)..."
                        className="w-full bg-background-primary border border-border rounded pl-8 pr-2.5 py-1.5 text-xs text-text-primary placeholder-text-muted outline-none focus:border-border-focus transition-colors"
                      />
                    </div>

                    {/* Clubs List */}
                    <div className="max-h-60 overflow-y-auto space-y-1 pr-0.5">
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
                            className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded text-xs transition-colors text-left ${
                              isSelected
                                ? 'bg-primary text-white font-medium'
                                : 'hover:bg-background-tertiary text-text-secondary hover:text-text-primary font-medium'
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
                              <span className={`text-xs font-mono shrink-0 px-1.5 py-0.5 rounded-sm font-medium tabular-nums ${
                                isSelected ? 'bg-white/20 text-white' : 'bg-background-tertiary text-text-secondary'
                              }`}>
                                #{standing.rank} • {standing.points}P
                              </span>
                            )}
                          </button>
                        );
                      })}
                      {filteredClubs.length === 0 && (
                        <p className="py-4 text-center text-xs text-text-muted">Eşleşen kulüp bulunamadı.</p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Stadium & Manager */}
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-text-secondary font-medium mb-2">
              <span className="flex items-center gap-1">
                <MapPin className="w-3.5 h-3.5 text-text-muted shrink-0" /> {currentMeta.stadium || 'Premier League Stadium'}
              </span>
              {displayManager?.name?.display && (
                <span className="flex items-center gap-1">
                  <span className="text-text-muted">·</span>
                  <button 
                    type="button" 
                    onClick={() => onSelectManager(displayManager)} 
                    className="text-text-primary font-medium hover:underline" 
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
        <div className="flex flex-col items-start lg:items-end gap-3 w-full lg:w-auto pt-4 lg:pt-0 border-t lg:border-t-0 border-border-light">
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
              className="appearance-none min-w-36 bg-background-primary hover:bg-background-tertiary border border-border rounded pl-3 pr-9 py-2 text-xs font-medium text-text-primary focus:outline-none focus:border-border-focus cursor-pointer"
            >
              {['2026_27', '2025_26', '2024_25', '2023_24', '2022_23', 'all'].map(season => (
                <option key={season} value={season}>
                  {season === 'all' ? 'Tüm Sezonlar' : `${formatSeasonLabel(season)} Sezonu`}
                </option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-muted" />
          </div>

          {/* Kadro Değeri */}
          {profile.market_value && (
            <button 
              type="button"
              onClick={() => setShowMarketValueModal?.(true)}
              className="text-left lg:text-right group p-1 -m-1 rounded transition-colors focus:outline-none focus-visible:ring-1 focus-visible:ring-border-focus"
              title="5 yıllık piyasa değeri değişim grafiğini görüntülemek için tıklayın"
            >
              <div className="flex items-center lg:justify-end gap-1.5 text-xs text-text-secondary">
                <Coins className="w-3.5 h-3.5 text-text-muted" />
                <span className="text-xs font-medium text-text-secondary uppercase tracking-wider">
                  Kadro Değeri
                </span>
                <span className="text-text-muted">·</span>
                <span className="text-xs font-medium text-text-muted">
                  Transfermarkt
                </span>
                <span className="text-xs font-medium text-text-primary ml-0.5">
                  Grafik
                </span>
              </div>
              <div className="flex items-baseline lg:justify-end gap-2 mt-0.5">
                <strong className="text-2xl sm:text-3xl font-semibold font-mono text-text-primary tracking-tight tabular-nums">
                  {profile.market_value.formatted}
                </strong>
                {profile.market_value.avg_formatted && (
                  <span className="text-xs font-mono text-text-secondary font-medium tabular-nums">
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
