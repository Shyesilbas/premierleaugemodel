import { ChevronDown, ChevronRight, MapPin, Search, X } from 'lucide-react';
import { handleTeamBadgeError } from '../../utils/imageFallbacks';
import TeamForm from '../TeamForm';
import { formatSeasonLabel } from '../../utils/dateFormatters';
import { useCompetition } from '../../context/CompetitionContext';
import { seasonsFor } from '../../data/seasons';

function SeasonSelect({ value, options, onChange }) {
  const shown = options.includes(value) ? options : [value, ...options];
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor="team-profile-season" className="text-xs text-text-secondary">Sezon</label>
      <div className="relative">
        <select
          id="team-profile-season"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className="appearance-none h-10 min-w-36 pl-3 pr-9 rounded border border-border bg-background-primary text-sm font-medium text-text-primary cursor-pointer transition-colors duration-150 ease-out hover:border-card-border-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-border-focus"
        >
          {shown.map(season => (
            <option key={season} value={season}>
              {season === 'all' ? 'Tüm sezonlar' : `${formatSeasonLabel(season, '/')} sezonu`}
            </option>
          ))}
        </select>
        <ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-tertiary" strokeWidth={1.5} aria-hidden="true" />
      </div>
    </div>
  );
}

export default function TeamProfileHero({ profile, currentMeta, selectedTeamId, onSelectTeam, teamSeason, setTeamSeason, setSelectedSeason, standingsMap, displayManager, onSelectManager, last5Matches, isTeamSelectorOpen, setIsTeamSelectorOpen, teamSearchQuery, setTeamSearchQuery, filteredClubs, teamSelectorRef, setShowMarketValueModal }) {
  const { activeCompetition, competitionKey } = useCompetition();
  const seasonsList = seasonsFor(competitionKey);
  const changeSeason = (nextSeason) => {
    setTeamSeason(nextSeason);
    setSelectedSeason?.(nextSeason);
  };

  // No profile for this team and season (e.g. the club did not play in it): keep the season picker reachable.
  if (!profile) {
    return (
      <div className="flex flex-wrap items-end justify-between gap-3 bg-background-primary border border-border rounded p-4">
        <p className="text-sm text-text-secondary">
          {currentMeta?.name ? `${currentMeta.name} için bu sezonda veri yok.` : 'Bu sezon için takım verisi yok.'}
        </p>
        <SeasonSelect value={teamSeason} options={seasonsList} onChange={changeSeason} />
      </div>
    );
  }

  const marketValue = profile.market_value;

  return (
    <header className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 pb-6 border-b border-border">
      <div className="flex items-center gap-4 sm:gap-5 min-w-0">
        <div className="w-16 h-16 sm:w-20 sm:h-20 rounded border border-border bg-background-primary p-2 shrink-0 flex items-center justify-center">
          <img
            src={currentMeta.badge}
            alt=""
            className="w-full h-full object-contain"
            onError={handleTeamBadgeError}
          />
        </div>

        <div className="min-w-0 flex flex-col gap-2">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
            <h2 className="text-2xl font-semibold text-text-primary truncate">{currentMeta.name}</h2>
            <span className="text-sm text-text-secondary tabular-nums">{currentMeta.abbr}</span>

            <div className="relative" ref={teamSelectorRef}>
              <button
                type="button"
                onClick={() => setIsTeamSelectorOpen(prev => !prev)}
                aria-expanded={isTeamSelectorOpen}
                aria-haspopup="listbox"
                className="h-8 px-3 rounded border border-border bg-background-primary text-sm font-medium text-text-primary inline-flex items-center gap-1.5 transition-colors duration-150 ease-out hover:border-card-border-hover cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-border-focus"
              >
                Takım değiştir
                <ChevronDown className={`w-4 h-4 text-text-tertiary transition-transform duration-150 ease-out motion-reduce:transition-none ${isTeamSelectorOpen ? 'rotate-180' : ''}`} strokeWidth={1.5} aria-hidden="true" />
              </button>

              {isTeamSelectorOpen && (
                <div className="absolute left-0 top-full mt-2 w-72 sm:w-80 bg-background-primary border border-border rounded shadow-md p-3 z-50">
                  <div className="flex items-center justify-between pb-2 mb-2 border-b border-border-light">
                    <span className="text-sm font-semibold text-text-primary">{activeCompetition?.name || 'Turnuva'} kulüpleri</span>
                    <button
                      type="button"
                      onClick={() => setIsTeamSelectorOpen(false)}
                      aria-label="Kapat"
                      className="p-1 rounded text-text-tertiary hover:text-text-primary transition-colors duration-150 ease-out cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-border-focus"
                    >
                      <X className="w-4 h-4" strokeWidth={1.5} />
                    </button>
                  </div>

                  <div className="relative mb-2">
                    <label htmlFor="team-search" className="sr-only">Takım ara</label>
                    <Search className="w-4 h-4 text-text-tertiary absolute left-3 top-1/2 -translate-y-1/2" strokeWidth={1.5} aria-hidden="true" />
                    <input
                      id="team-search"
                      type="text"
                      autoFocus
                      value={teamSearchQuery}
                      onChange={(e) => setTeamSearchQuery(e.target.value)}
                      placeholder="Takım ara"
                      className="w-full h-9 bg-background-primary border border-border rounded pl-9 pr-3 text-sm text-text-primary placeholder:text-text-tertiary focus:outline-none focus-visible:ring-2 focus-visible:ring-border-focus"
                    />
                  </div>

                  <div className="max-h-60 overflow-y-auto flex flex-col gap-0.5">
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
                          className={`w-full h-9 flex items-center justify-between gap-2 px-2.5 rounded text-sm text-left transition-colors duration-150 ease-out cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-border-focus ${
                            isSelected
                              ? 'bg-primary text-white font-medium'
                              : 'text-text-secondary hover:bg-background-tertiary hover:text-text-primary'
                          }`}
                        >
                          <span className="flex items-center gap-2 min-w-0">
                            <img
                              src={club.badge}
                              alt=""
                              className="w-5 h-5 object-contain shrink-0"
                              onError={handleTeamBadgeError}
                            />
                            <span className="truncate">{club.name}</span>
                          </span>
                          {standing && (
                            <span className={`text-xs tabular-nums shrink-0 ${isSelected ? 'text-white/70' : 'text-text-tertiary'}`}>
                              {standing.rank}. sıra · {standing.points} puan
                            </span>
                          )}
                        </button>
                      );
                    })}
                    {filteredClubs.length === 0 && (
                      <p className="py-4 text-center text-sm text-text-secondary">Eşleşen kulüp bulunamadı.</p>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-text-secondary">
            <MapPin className="w-4 h-4 text-text-tertiary shrink-0" strokeWidth={1.5} aria-hidden="true" />
            <span>{currentMeta.stadium || (competitionKey === 'premier_league' ? 'Premier League stadyumu' : 'Stadyum bilgisi yok')}</span>
            {displayManager?.name?.display && (
              <>
                <span className="text-text-muted">·</span>
                <span className="text-text-tertiary">Teknik direktör</span>
                <button
                  type="button"
                  onClick={() => onSelectManager(displayManager)}
                  className="font-medium text-text-primary hover:underline cursor-pointer rounded-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-border-focus"
                  aria-label={`${displayManager.name.display} rakip performansını aç`}
                >
                  {displayManager.name.display}
                </button>
              </>
            )}
          </div>

          {last5Matches.length > 0 && (
            <div className="flex items-center gap-2 text-xs text-text-secondary">
              <span>Son 5 maç</span>
              <TeamForm
                label="Son 5 maç formu"
                results={last5Matches}
                getKey={(item, index) => item.match_id || index}
                getTitle={item => `vs ${item.opponent_name}: ${item.team_score}-${item.opp_score} (${item.result === 'W' ? 'Galibiyet' : item.result === 'D' ? 'Beraberlik' : 'Mağlubiyet'})`}
              />
            </div>
          )}
        </div>
      </div>

      <div className="flex items-end gap-3 w-full lg:w-auto shrink-0">
        <SeasonSelect value={teamSeason} options={seasonsList} onChange={changeSeason} />

        {marketValue && (
          <button
            type="button"
            onClick={() => setShowMarketValueModal?.(true)}
            title="5 yıllık kadro değeri grafiğini aç"
            className="flex-1 lg:flex-none text-left rounded border border-border bg-background-primary px-4 py-2 transition-colors duration-150 ease-out hover:border-card-border-hover cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-border-focus"
          >
            <span className="flex items-center justify-between gap-3 text-xs text-text-secondary">
              Kadro değeri
              <span className="inline-flex items-center gap-0.5 text-text-primary">
                Grafik
                <ChevronRight className="w-3.5 h-3.5" strokeWidth={1.5} aria-hidden="true" />
              </span>
            </span>
            <span className="flex items-baseline gap-2">
              <strong className="text-xl font-semibold tabular-nums text-text-primary">{marketValue.formatted}</strong>
              {marketValue.avg_formatted && (
                <span className="text-xs tabular-nums text-text-tertiary">oyuncu başı {marketValue.avg_formatted}</span>
              )}
            </span>
          </button>
        )}
      </div>
    </header>
  );
}
