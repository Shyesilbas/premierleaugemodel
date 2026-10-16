import { Calendar } from 'lucide-react';
import { getTeam } from '../../data/teams';
import FixtureMatchCard from './FixtureMatchCard';
import FixtureMatchRow from './FixtureMatchRow';

export default function FixturesGameweeksView({ loading, filteredGameweeks, displayMode, currentGameweek, teamManagers, teamForms, onMatchClick, onSelectTeam }) {
  return (
    <>
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
                    
                    {/* Day Groups inside Gameweek */}
                    <div className="space-y-5">
                      {gwObj.days.map((dayObj, dayIdx) => (
                        <div key={dayIdx} className="space-y-2.5">
                          
                          {/* Day Subheader */}
                          <div className="flex items-center gap-2 text-xs font-bold text-slate-700 px-1">
                            <Calendar className="w-3.5 h-3.5 text-[#38003c]" />
                            <span>{dayObj.day}</span>
                          </div>

                          {/* Matches List or Grid for that Day */}
                          {displayMode === 'list' ? (
                            <div className="border border-slate-200 rounded-xl divide-y divide-slate-100 bg-white shadow-2xs overflow-hidden">
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
                ))}
              </div>
            )}
    </>
  );
}
