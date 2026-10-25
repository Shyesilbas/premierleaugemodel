import { Calendar } from 'lucide-react';
import { getTeam } from '../../data/teams';
import FixtureMatchCard from './FixtureMatchCard';
import FixtureMatchRow from './FixtureMatchRow';

export default function FixturesGameweeksView({ loading, filteredGameweeks, displayMode, currentGameweek, teamManagers, teamForms, onMatchClick, onSelectTeam }) {
  return (
    <>
      {loading ? (
        <div className="space-y-4">
          <div className="h-6 w-36 bg-background-tertiary animate-pulse rounded" />
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="h-44 bg-background-primary border border-border rounded animate-pulse" />
            <div className="h-44 bg-background-primary border border-border rounded animate-pulse" />
          </div>
        </div>
      ) : filteredGameweeks.length === 0 ? (
        <div className="py-12 text-center bg-background-primary border border-border rounded">
          <p className="text-sm font-semibold text-text-primary">Aramanızla eşleşen maç bulunamadı.</p>
          <p className="text-xs text-text-secondary mt-1">Filtreleri temizleyip tekrar deneyin.</p>
        </div>
      ) : (
              <div className="space-y-8">
                {filteredGameweeks.map(gwObj => {
                  const showHeader = filteredGameweeks.length > 1 || (gwObj.stage && gwObj.stage !== 'league');
                  const matchCount = gwObj.days.reduce((acc, d) => acc + d.matches.length, 0);

                  return (
                    <div key={gwObj.gameweek} className="space-y-4">
                      {showHeader && (
                        <div className="flex items-center justify-between pb-2 border-b border-border">
                          <div className="flex items-center gap-2">
                            <h3 className="text-sm font-semibold text-text-primary">{gwObj.title || `Hafta ${gwObj.gameweek}`}</h3>
                            {gwObj.stage && gwObj.stage !== 'league' && (
                              <span className="text-xs px-2 py-0.5 rounded-sm bg-primary/10 text-primary font-medium">
                                {gwObj.stage_title || 'Eleme Turu'}
                              </span>
                            )}
                          </div>
                          <span className="text-xs text-text-secondary tabular-nums">{matchCount} maç</span>
                        </div>
                      )}

                      {/* Day Groups inside Gameweek */}
                      <div className="space-y-5">
                      {gwObj.days.map((dayObj, dayIdx) => (
                        <div key={dayIdx} className="space-y-2.5">
                          
                          {/* Day Subheader */}
                          <div className="flex items-center gap-2 text-xs font-semibold text-text-secondary px-1">
                            <Calendar className="w-3.5 h-3.5 text-text-primary" />
                            <span>{dayObj.day}</span>
                          </div>

                          {/* Matches List or Grid for that Day */}
                          {displayMode === 'list' ? (
                            <div className="border border-border rounded divide-y divide-border-light bg-background-primary overflow-hidden">
                              {dayObj.matches.map(m => {
                                const home = getTeam(m.home_id, m.home_name);
                                const away = getTeam(m.away_id, m.away_name);
                                return (
                                  <FixtureMatchRow
                                    key={m.match_id}
                                    match={m}
                                    home={home}
                                    away={away}
                                    onMatchClick={onMatchClick}
                                    onSelectTeam={onSelectTeam}
                                  />
                                );
                              })}
                            </div>
                          ) : (
                            /* Matches Grid for that Day (Detaylı Kartlar) */
                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3.5">
                              {dayObj.matches.map(m => {
                                const home = getTeam(m.home_id, m.home_name);
                                const away = getTeam(m.away_id, m.away_name);
                                const homeManager = teamManagers[String(m.home_id)];
                                const awayManager = teamManagers[String(m.away_id)];
                                return (
                                  <FixtureMatchCard
                                    key={m.match_id}
                                    match={m}
                                    home={home}
                                    away={away}
                                    homeManager={homeManager}
                                    awayManager={awayManager}
                                    currentGameweek={currentGameweek}
                                    homeForm={teamForms.get(Number(m.home_id)) || []}
                                    awayForm={teamForms.get(Number(m.away_id)) || []}
                                    onMatchClick={onMatchClick}
                                    onSelectTeam={onSelectTeam}
                                  />
                                );
                              })}
                          </div>
                        )}

                        </div>
                      ))}
                    </div>

                  </div>
                  );
                })}
              </div>
            )}
    </>
  );
}
