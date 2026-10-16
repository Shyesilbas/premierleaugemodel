import { Trophy } from 'lucide-react';
import { handleTeamBadgeError } from '../../utils/imageFallbacks';

export default function FixturesStandingsView({ displayedStandings, standingsType, setStandingsType, loadingStandings, onSelectTeam }) {
  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-4">
              {/* Table Header: Title + Overall/Home/Away toggle */}
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
                <div className="flex items-center gap-2">
                  <Trophy className="w-5 h-5 text-amber-500" />
                  <div>
                    <h3 className="text-sm font-black text-slate-900">
                      Premier League Puan Durumu
                    </h3>
                    <p className="text-[11px] text-slate-500">
                      {selectedSeason === '2026_27' ? '2026-27 Güncel Sezon Sıralaması' : `${formatSeasonLabel(selectedSeason)} Sezon Sonu Tablosu`}
                    </p>
                  </div>
                </div>

                {/* Genel / İç Saha / Deplasman Filtresi */}
                <div className="flex items-center bg-slate-100 p-1 rounded-xl border border-slate-200 gap-1 self-stretch sm:self-auto justify-center">
                  <button
                    onClick={() => setStandingsType('all')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                      standingsType === 'all'
                        ? 'bg-[#38003c] text-white shadow-xs'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    Genel
                  </button>
                  <button
                    onClick={() => setStandingsType('home')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                      standingsType === 'home'
                        ? 'bg-[#38003c] text-white shadow-xs'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    İç Saha
                  </button>
                  <button
                    onClick={() => setStandingsType('away')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                      standingsType === 'away'
                        ? 'bg-[#38003c] text-white shadow-xs'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    Deplasman
                  </button>
                </div>
              </div>

              {/* Table Content */}
              {loadingStandings ? (
                <div className="py-20 text-center">
                  <div className="w-8 h-8 border-3 border-[#38003c] border-t-transparent rounded-full animate-spin mx-auto mb-3" />
                  <p className="text-xs font-bold text-slate-700">Puan tablosu hesaplanıyor...</p>
                </div>
              ) : displayedStandings.length === 0 ? (
                <div className="py-12 text-center text-xs text-slate-500">
                  Puan tablosu verisi bulunamadı.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider bg-slate-50/50">
                        <th className="py-2.5 px-3 w-12 text-center">#</th>
                        <th className="py-2.5 px-3 min-w-[180px]">Kulüp</th>
                        <th className="py-2.5 px-2 text-center w-10" title="Oynanan Maç">O</th>
                        <th className="py-2.5 px-2 text-center w-10" title="Galibiyet">G</th>
                        <th className="py-2.5 px-2 text-center w-10" title="Beraberlik">B</th>
                        <th className="py-2.5 px-2 text-center w-10" title="Mağlubiyet">M</th>
                        <th className="py-2.5 px-2 text-center w-12 hidden md:table-cell" title="Attığı Gol">AG</th>
                        <th className="py-2.5 px-2 text-center w-12 hidden md:table-cell" title="Yediği Gol">YG</th>
                        <th className="py-2.5 px-2 text-center w-12" title="Averaj">AV</th>
                        <th className="py-2.5 px-3 text-center w-14 font-black text-slate-900" title="Puan">P</th>
                        <th className="py-2.5 px-3 text-center w-36 hidden sm:table-cell" title="Son 5 Maç">Form</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 font-mono">
                      {displayedStandings.map((t, idx) => {
                        const rank = idx + 1;
                        const stats = standingsType === 'all' ? t : (t[standingsType] || t);
                        const isUcl = rank <= 4;
                        const isUel = rank === 5;
                        const isRelegation = rank >= 18;

                        const borderClass = isUcl 
                          ? 'border-l-4 border-l-blue-500' 
                          : isUel 
                          ? 'border-l-4 border-l-orange-500' 
                          : isRelegation 
                          ? 'border-l-4 border-l-rose-500' 
                          : 'border-l-4 border-l-transparent';

                        const gdFormatted = stats.gd > 0 ? `+${stats.gd}` : `${stats.gd}`;

                        return (
                          <tr 
                            key={t.id}
                            className={`hover:bg-slate-50 transition-colors ${borderClass}`}
                          >
                            <td className="py-2.5 px-3 text-center font-bold text-slate-700">
                              <span className={`inline-flex items-center justify-center w-6 h-6 rounded-md text-[11px] font-black ${
                                rank === 1 ? 'bg-amber-100 text-amber-900 border border-amber-300' : 'text-slate-600'
                              }`}>
                                {rank}
                              </span>
                            </td>

                            <td className="py-2.5 px-3 font-sans">
                              <div className="flex items-center gap-2.5">
                                <img 
                                  src={t.badge} 
                                  alt={t.name} 
                                  className="w-5 h-5 object-contain shrink-0"
                                  onError={handleTeamBadgeError}
                                />
                                <button
                                  type="button"
                                  onClick={() => onSelectTeam?.(t.id)}
                                  className="font-bold text-slate-900 truncate text-left hover:text-[#38003c] hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#38003c]"
                                  aria-label={`${t.name} takım profiline git`}
                                >
                                  {t.name}
                                </button>
                                {t.abbr && (
                                  <span className="text-[10px] font-mono font-bold text-slate-400 hidden lg:inline">
                                    {t.abbr}
                                  </span>
                                )}
                              </div>
                            </td>

                            <td className="py-2.5 px-2 text-center font-semibold text-slate-800">{stats.played}</td>
                            <td className="py-2.5 px-2 text-center text-slate-600">{stats.won}</td>
                            <td className="py-2.5 px-2 text-center text-slate-600">{stats.drawn}</td>
                            <td className="py-2.5 px-2 text-center text-slate-600">{stats.lost}</td>

                            <td className="py-2.5 px-2 text-center text-slate-500 hidden md:table-cell">{stats.gf}</td>
                            <td className="py-2.5 px-2 text-center text-slate-500 hidden md:table-cell">{stats.ga}</td>

                            <td className={`py-2.5 px-2 text-center font-bold ${
                              stats.gd > 0 ? 'text-emerald-700' : stats.gd < 0 ? 'text-rose-700' : 'text-slate-500'
                            }`}>
                              {gdFormatted}
                            </td>

                            <td className="py-2.5 px-3 text-center">
                              <span className="inline-block px-2 py-0.5 rounded-md bg-slate-900 text-white font-black text-xs">
                                {stats.points}
                              </span>
                            </td>

                            <td className="py-2.5 px-3 text-center hidden sm:table-cell">
                              <div className="flex items-center justify-center gap-1">
                                {(t.form || []).map((res, fIdx) => {
                                  const bg = res === 'W' 
                                    ? 'bg-emerald-500 text-white' 
                                    : res === 'D' 
                                    ? 'bg-slate-400 text-white' 
                                    : 'bg-rose-500 text-white';
                                  const label = res === 'W' ? 'G' : res === 'D' ? 'B' : 'M';
                                  return (
                                    <span
                                      key={fIdx}
                                      className={`w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-black ${bg}`}
                                      title={res === 'W' ? 'Galibiyet' : res === 'D' ? 'Beraberlik' : 'Mağlubiyet'}
                                    >
                                      {label}
                                    </span>
                                  );
                                })}
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Legend Footer */}
              <div className="pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3 text-[11px] text-slate-500 font-medium">
                <div className="flex flex-wrap items-center gap-4">
                  <div className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-xs bg-blue-500" />
                    <span>Şampiyonlar Ligi (1-4)</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-xs bg-orange-500" />
                    <span>Avrupa Ligi (5)</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-xs bg-rose-500" />
                    <span>Küme Düşme Hattı (18-20)</span>
                  </div>
                </div>
                <div className="font-mono text-[10px] text-slate-400">
                  O: Oynanan • G: Galibiyet • B: Beraberlik • M: Mağlubiyet • AV: Averaj • P: Puan
                </div>
              </div>
            </div>
  );
}
