import { ExternalLink, Users } from 'lucide-react';
import PitchLineup from '../PitchLineup';
import PlayerAvatar from '../PlayerAvatar';
import { RedCardIcon, YellowCardIcon } from './eventIcons';

export default function MatchLineupsTab({
  homeLineup,
  awayLineup,
  homeTeam,
  awayTeam,
  playerStats,
  lineupViewMode,
  setLineupViewMode,
  isCompleted,
  prediction,
  handlePlayerClick,
  groupPlayersByPosition,
  formatPosition,
  getPositionBadgeClass
}) {
  return (

          <div className="space-y-6">
            {!homeLineup && !awayLineup ? (
              <div className="py-16 text-center text-sm text-text-secondary font-medium">
                Bu maç için henüz resmi kadro veya ilk 11 verisi açıklanmamış.
              </div>
            ) : (
              <>
                {/* View Switcher Header: Taktik Saha vs Detaylı Liste */}
                <div className="flex items-center justify-between flex-wrap gap-3 pb-3 border-b border-border">
                  <div className="flex items-center gap-2">
                    <Users className="w-5 h-5 text-primary" />
                    <h3 className="text-sm font-semibold text-text-primary">
                      İlk 11 & Kadrolar
                    </h3>
                    <span className="text-xs text-text-secondary font-medium hidden sm:inline">
                      · Taktik diziliş ve yedek kulübesi
                    </span>
                  </div>

                  {/* Segmented Control */}
                  <div className="flex items-center bg-background-tertiary p-1 rounded border border-border gap-1">
                    <button
                      type="button"
                      onClick={() => setLineupViewMode('pitch')}
                      className={`px-3.5 py-1.5 rounded text-xs font-semibold transition-all ${
                        lineupViewMode === 'pitch'
                          ? 'bg-primary text-white '
                          : 'text-text-secondary hover:text-text-primary hover:bg-background-tertiary'
                      }`}
                    >
                      Taktik Saha
                    </button>
                    <button
                      type="button"
                      onClick={() => setLineupViewMode('list')}
                      className={`px-3.5 py-1.5 rounded text-xs font-semibold transition-all ${
                        lineupViewMode === 'list'
                          ? 'bg-primary text-white '
                          : 'text-text-secondary hover:text-text-primary hover:bg-background-tertiary'
                      }`}
                    >
                      Detaylı Liste
                    </button>
                  </div>
                </div>

                {/* Starting XI Form & Model Impact Banner (Clean, Minimalist Design) */}
                {(homeLineup?.team_ratings || prediction?.lineup_analysis) && (
                  <div className="bg-background-primary text-text-primary rounded p-4 sm:p-5 border border-border space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-2 pb-2.5 border-b border-border-light">
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-status-success" />
                        <h4 className="text-xs sm:text-sm font-semibold text-text-primary">
                          {isCompleted ? 'Maç Performansı & Oyuncu Reytingleri' : 'İlk 11 Kadro Formu & Dinamik Model Etkisi'}
                        </h4>
                      </div>
                      <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-sm border ${
                        (prediction?.lineup_analysis?.is_official || isCompleted)
                          ? 'bg-background-tertiary text-status-success border-status-success'
                          : 'bg-background-tertiary text-text-tertiary border-border-light'
                      }`}>
                        {prediction?.lineup_analysis?.status_label || (isCompleted ? 'Resmi Kadrolar Açıklandı' : "Muhtemel 11'ler Baz Alındı")}
                      </span>
                    </div>

                    {/* Team Ratings Comparison Grid */}
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 items-center text-center">
                      {/* Home Team 11 */}
                      <div className="bg-background-tertiary rounded p-2.5 flex flex-col items-center">
                        <span className="text-xs font-semibold text-text-tertiary truncate max-w-36">{homeTeam?.name}</span>
                        <div className="flex items-baseline gap-1 mt-0.5">
                          <span className="text-xl font-semibold tabular-nums text-text-primary">
                            {Number(homeLineup?.team_ratings?.overall || prediction?.lineup_analysis?.home_xi?.team_overall || 6.0).toFixed(1)}
                          </span>
                          <span className="text-xs text-text-secondary font-semibold">/ 10</span>
                        </div>
                        <div className="flex items-center gap-2 mt-1 text-xs text-text-tertiary">
                          <span>Hücum: <strong className="text-text-primary">{Number(homeLineup?.team_ratings?.attack || prediction?.lineup_analysis?.home_xi?.team_attack || 6.0).toFixed(1)}</strong></span>
                          <span>·</span>
                          <span>Savunma: <strong className="text-text-primary">{Number(homeLineup?.team_ratings?.defense || prediction?.lineup_analysis?.home_xi?.team_defense || 6.0).toFixed(1)}</strong></span>
                        </div>
                      </div>

                      {/* Center Model Impact Delta */}
                      <div className="bg-background-tertiary rounded p-2 space-y-1">
                        <span className="text-xs text-text-tertiary font-semibold block">
                          Lineup Modülatörleri
                        </span>
                        {prediction?.lineup_analysis?.lineup_impact ? (
                          <div className="space-y-0.5 text-xs tabular-nums">
                            <div className="flex justify-between px-2 text-xs">
                              <span className="text-text-tertiary">Gol Etkisi:</span>
                              <span className="font-semibold text-text-primary">
                                {prediction.lineup_analysis.lineup_impact.delta_home_goals > 0 ? `+${prediction.lineup_analysis.lineup_impact.delta_home_goals}` : prediction.lineup_analysis.lineup_impact.delta_home_goals} / {prediction.lineup_analysis.lineup_impact.delta_away_goals > 0 ? `+${prediction.lineup_analysis.lineup_impact.delta_away_goals}` : prediction.lineup_analysis.lineup_impact.delta_away_goals}
                              </span>
                            </div>
                            <div className="flex justify-between px-2 text-xs">
                              <span className="text-text-tertiary">Kart Beklentisi:</span>
                              <span className={`font-semibold ${prediction.lineup_analysis.lineup_impact.delta_cards > 0 ? 'text-status-warning' : 'text-text-primary'}`}>
                                {prediction.lineup_analysis.lineup_impact.delta_cards > 0 ? `+${prediction.lineup_analysis.lineup_impact.delta_cards}` : prediction.lineup_analysis.lineup_impact.delta_cards} Kart
                              </span>
                            </div>
                          </div>
                        ) : (
                          <p className="text-xs text-text-tertiary">Model çarpanları 11 açıklandığında güncellenir.</p>
                        )}
                      </div>

                      {/* Away Team 11 */}
                      <div className="bg-background-tertiary rounded p-2.5 flex flex-col items-center">
                        <span className="text-xs font-semibold text-text-tertiary truncate max-w-36">{awayTeam?.name}</span>
                        <div className="flex items-baseline gap-1 mt-0.5">
                          <span className="text-xl font-semibold tabular-nums text-text-primary">
                            {Number(awayLineup?.team_ratings?.overall || prediction?.lineup_analysis?.away_xi?.team_overall || 6.0).toFixed(1)}
                          </span>
                          <span className="text-xs text-text-secondary font-semibold">/ 10</span>
                        </div>
                        <div className="flex items-center gap-2 mt-1 text-xs text-text-tertiary">
                          <span>Hücum: <strong className="text-text-primary">{Number(awayLineup?.team_ratings?.attack || prediction?.lineup_analysis?.away_xi?.team_attack || 6.0).toFixed(1)}</strong></span>
                          <span>·</span>
                          <span>Savunma: <strong className="text-text-primary">{Number(awayLineup?.team_ratings?.defense || prediction?.lineup_analysis?.away_xi?.team_defense || 6.0).toFixed(1)}</strong></span>
                        </div>
                      </div>
                    </div>

                    {/* Summary text */}
                    {prediction?.lineup_analysis?.lineup_impact?.summary_text && (
                      <p className="text-xs text-text-tertiary text-center pt-1 border-t border-border-light">
                        {prediction.lineup_analysis.lineup_impact.summary_text}
                      </p>
                    )}
                  </div>
                )}

                {/* Conditional Rendering: Pitch View vs List View */}
                {lineupViewMode === 'pitch' ? (
                  <PitchLineup
                    homeLineup={homeLineup}
                    awayLineup={awayLineup}
                    homeTeam={homeTeam}
                    awayTeam={awayTeam}
                    playerStats={playerStats}
                    onPlayerClick={handlePlayerClick}
                  />
                ) : (
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
                
                {/* Home Team Column */}
                <div className="bg-background-primary border border-border rounded p-4 space-y-4 self-start">
                  {/* Team Card Header */}
                  <div className="pb-3 border-b border-border-light flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <img src={homeTeam.badge} alt="" className="w-8 h-8 object-contain shrink-0" />
                      <div>
                        <h4 className="font-semibold text-sm text-text-primary leading-tight">{homeTeam.name}</h4>
                        <span className="text-xs font-semibold text-text-secondary">Ev Sahibi</span>
                      </div>
                    </div>
                    {homeLineup?.formation && (
                      <span className="text-xs tabular-nums font-semibold px-3 py-1 rounded bg-background-tertiary text-primary border border-primary">
                        {homeLineup.formation}
                      </span>
                    )}
                  </div>

                  {/* Starting XI Grouped By Position Lines */}
                  <div className="space-y-4">
                    <div className="flex items-center justify-between pb-1.5 border-b border-border">
                      <span className="text-xs font-semibold text-text-primary">
                        Başlangıç 11'i ({homeLineup?.starters?.length || 0})
                      </span>
                      <span className="text-xs text-text-secondary font-medium">
                        İstatistik için oyuncuya tıklayın
                      </span>
                    </div>

                    {groupPlayersByPosition(homeLineup?.starters).map((group) => (
                      <div key={group.key} className="space-y-2">
                        <span className="text-xs tabular-nums font-semibold text-text-secondary block px-1">
                          {group.label} ({group.list.length})
                        </span>
                        <div className="space-y-1.5">
                          {group.list.map((p, idx) => {
                            const pStat = (playerStats?.home || []).find(ps => String(ps.id) === String(p.id));
                            const effectiveRating = (isCompleted && pStat?.rating != null) ? pStat.rating : (pStat?.rating != null ? pStat.rating : p.rating);

                            return (
                              <div 
                                key={p.id || idx}
                                onClick={(e) => handlePlayerClick(p, 'home', e)}
                                className="flex items-center justify-between p-2.5 rounded hover:bg-background-tertiary transition-all cursor-pointer group"
                                title={`${p.name} maç performansını görüntüle`}
                              >
                                <div className="flex items-center gap-3 min-w-0">
                                  <PlayerAvatar 
                                    photoUrl={p.photo_url}
                                    name={p.name}
                                    shirt={p.shirt || idx + 1}
                                    fallback="initials"
                                    size="w-8 h-8 text-xs"
                                    className="shrink-0 transition-transform"
                                  />
                                  <span className="w-6 h-6 rounded-full bg-background-tertiary border border-border flex items-center justify-center tabular-nums font-semibold text-xs text-text-primary shrink-0">
                                    {p.shirt || idx + 1}
                                  </span>
                                  <div className="min-w-0">
                                    <div className="flex items-center gap-1.5 flex-wrap">
                                      <span className="font-semibold text-text-primary group-hover:text-primary transition-colors truncate text-xs sm:text-sm">
                                        {p.name}
                                      </span>
                                      {p.captain && (
                                        <span className="text-xs font-semibold px-1.5 py-0.2 rounded bg-background-tertiary text-status-warning shrink-0">
                                          KAPTAN
                                        </span>
                                      )}
                                      {pStat?.goals > 0 && (
                                        <span className="text-xs bg-background-tertiary text-status-success font-semibold px-1 rounded border border-status-success shrink-0">
                                          G: {pStat.goals}
                                        </span>
                                      )}
                                      {pStat?.assists > 0 && (
                                        <span className="text-xs bg-background-tertiary text-primary font-semibold px-1 rounded border border-primary shrink-0">
                                          A: {pStat.assists}
                                        </span>
                                      )}
                                      {pStat?.red_cards > 0 ? (
                                        <RedCardIcon />
                                      ) : pStat?.yellow_cards > 0 ? (
                                        <YellowCardIcon />
                                      ) : null}
                                    </div>
                                  </div>
                                </div>
                                <div className="flex items-center gap-2 shrink-0">
                                  {effectiveRating != null ? (
                                    <span
                                      className={`text-xs tabular-nums font-semibold px-1.5 py-0.5 rounded border ${
                                        effectiveRating >= 7.5
                                          ? 'bg-background-tertiary text-status-success border-status-success'
                                          : effectiveRating >= 6.5
                                          ? 'bg-background-tertiary text-primary border-primary'
                                          : effectiveRating >= 5.5
                                          ? 'bg-background-tertiary text-text-primary border-border'
                                          : 'bg-background-tertiary text-status-error border-status-error'
                                      }`}
                                      title={isCompleted ? `Maç Performans Reytingi: ${Number(effectiveRating).toFixed(1)}/10` : `Form Puanı: ${Number(effectiveRating).toFixed(1)}/10`}
                                    >
                                      {Number(effectiveRating).toFixed(1)}
                                    </span>
                                  ) : isCompleted ? (
                                    <span className="text-xs tabular-nums text-text-tertiary px-1" title="Değerlendirilmedi">
                                      —
                                    </span>
                                  ) : null}
                                  <span className={`text-xs font-semibold px-2 py-0.5 rounded-sm border ${getPositionBadgeClass(p.position)}`}>
                                    {formatPosition(p.position)}
                                  </span>
                                  <ExternalLink className="w-3.5 h-3.5 text-text-tertiary group-hover:text-text-secondary transition-colors" />
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Substitutes Bench */}
                  {homeLineup?.substitutes?.length > 0 && (
                    <div className="pt-4 border-t border-border space-y-2.5">
                      <span className="text-xs font-semibold text-text-primary block">
                        Yedek Kulübesi ({homeLineup.substitutes.length})
                      </span>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {homeLineup.substitutes.map((sub, idx) => {
                          const pStat = (playerStats?.home || []).find(ps => String(ps.id) === String(sub.id));
                          const effectiveRating = (isCompleted && pStat?.rating != null) ? pStat.rating : (pStat?.rating != null ? pStat.rating : sub.rating);

                          return (
                            <div 
                              key={sub.id || idx}
                              onClick={(e) => handlePlayerClick(sub, 'home', e)}
                              className="flex items-center justify-between p-2 rounded hover:bg-background-tertiary transition-all cursor-pointer group text-xs"
                              title={`${sub.name} maç performansını görüntüle`}
                            >
                              <div className="flex items-center gap-2 min-w-0">
                                <PlayerAvatar 
                                  photoUrl={sub.photo_url}
                                  name={sub.name}
                                  shirt={sub.shirt}
                                  fallback="initials"
                                  size="w-6 h-6 text-xs"
                                  className="shrink-0"
                                />
                                <span className="tabular-nums text-xs font-semibold text-text-secondary">#{sub.shirt}</span>
                                <span className="font-medium text-text-primary truncate">{sub.name}</span>
                                {pStat?.goals > 0 && <span className="text-xs bg-background-tertiary text-status-success font-semibold px-1 rounded border border-status-success">G: {pStat.goals}</span>}
                                {pStat?.assists > 0 && <span className="text-xs bg-background-tertiary text-primary font-semibold px-1 rounded border border-primary">A: {pStat.assists}</span>}
                                {pStat?.red_cards > 0 ? <RedCardIcon /> : pStat?.yellow_cards > 0 ? <YellowCardIcon /> : null}
                              </div>
                              <div className="flex items-center gap-1.5 shrink-0">
                                {effectiveRating != null && (
                                  <span className={`text-xs tabular-nums font-semibold px-1.5 py-0.2 rounded border ${
                                    effectiveRating >= 7.5 ? 'bg-background-tertiary text-status-success border-status-success' :
                                    effectiveRating >= 6.5 ? 'bg-background-tertiary text-primary border-primary' :
                                    effectiveRating >= 5.5 ? 'bg-background-tertiary text-text-primary border-border' :
                                    'bg-background-tertiary text-status-error border-status-error'
                                  }`}>
                                    {Number(effectiveRating).toFixed(1)}
                                  </span>
                                )}
                                <span className={`text-xs font-semibold px-1.5 py-0.2 rounded border shrink-0 ${getPositionBadgeClass(sub.position)}`}>
                                  {formatPosition(sub.position)}
                                </span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>

                {/* Away Team Column */}
                <div className="bg-background-primary border border-border rounded p-4 space-y-4 self-start">
                  {/* Team Card Header */}
                  <div className="pb-3 border-b border-border-light flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <img src={awayTeam.badge} alt="" className="w-8 h-8 object-contain shrink-0" />
                      <div>
                        <h4 className="font-semibold text-sm text-text-primary leading-tight">{awayTeam.name}</h4>
                        <span className="text-xs font-semibold text-text-secondary">Deplasman</span>
                      </div>
                    </div>
                    {awayLineup?.formation && (
                      <span className="text-xs tabular-nums font-semibold px-3 py-1 rounded bg-background-tertiary text-primary border border-primary">
                        {awayLineup.formation}
                      </span>
                    )}
                  </div>

                  {/* Starting XI Grouped By Position Lines */}
                  <div className="space-y-4">
                    <div className="flex items-center justify-between pb-1.5 border-b border-border">
                      <span className="text-xs font-semibold text-text-primary">
                        Başlangıç 11'i ({awayLineup?.starters?.length || 0})
                      </span>
                      <span className="text-xs text-text-secondary font-medium">
                        İstatistik için oyuncuya tıklayın
                      </span>
                    </div>

                    {groupPlayersByPosition(awayLineup?.starters).map((group) => (
                      <div key={group.key} className="space-y-2">
                        <span className="text-xs tabular-nums font-semibold text-text-secondary block px-1">
                          {group.label} ({group.list.length})
                        </span>
                        <div className="space-y-1.5">
                          {group.list.map((p, idx) => {
                            const pStat = (playerStats?.away || []).find(ps => String(ps.id) === String(p.id));
                            const effectiveRating = (isCompleted && pStat?.rating != null) ? pStat.rating : (pStat?.rating != null ? pStat.rating : p.rating);

                            return (
                              <div 
                                key={p.id || idx}
                                onClick={(e) => handlePlayerClick(p, 'away', e)}
                                className="flex items-center justify-between p-2.5 rounded hover:bg-background-tertiary transition-all cursor-pointer group"
                                title={`${p.name} maç performansını görüntüle`}
                              >
                                <div className="flex items-center gap-3 min-w-0">
                                  <PlayerAvatar 
                                    photoUrl={p.photo_url}
                                    name={p.name}
                                    shirt={p.shirt || idx + 1}
                                    fallback="initials"
                                    size="w-8 h-8 text-xs"
                                    className="shrink-0 transition-transform"
                                  />
                                  <span className="w-6 h-6 rounded-full bg-background-tertiary border border-border flex items-center justify-center tabular-nums font-semibold text-xs text-text-primary shrink-0">
                                    {p.shirt || idx + 1}
                                  </span>
                                  <div className="min-w-0">
                                    <div className="flex items-center gap-1.5 flex-wrap">
                                      <span className="font-semibold text-text-primary group-hover:text-primary transition-colors truncate text-xs sm:text-sm">
                                        {p.name}
                                      </span>
                                      {p.captain && (
                                        <span className="text-xs font-semibold px-1.5 py-0.2 rounded bg-background-tertiary text-status-warning shrink-0">
                                          KAPTAN
                                        </span>
                                      )}
                                      {pStat?.goals > 0 && (
                                        <span className="text-xs bg-background-tertiary text-status-success font-semibold px-1 rounded border border-status-success shrink-0">
                                          G: {pStat.goals}
                                        </span>
                                      )}
                                      {pStat?.assists > 0 && (
                                        <span className="text-xs bg-background-tertiary text-primary font-semibold px-1 rounded border border-primary shrink-0">
                                          A: {pStat.assists}
                                        </span>
                                      )}
                                      {pStat?.red_cards > 0 ? (
                                        <RedCardIcon />
                                      ) : pStat?.yellow_cards > 0 ? (
                                        <YellowCardIcon />
                                      ) : null}
                                    </div>
                                  </div>
                                </div>
                                <div className="flex items-center gap-2 shrink-0">
                                  {effectiveRating != null ? (
                                    <span
                                      className={`text-xs tabular-nums font-semibold px-1.5 py-0.5 rounded border ${
                                        effectiveRating >= 7.5
                                          ? 'bg-background-tertiary text-status-success border-status-success'
                                          : effectiveRating >= 6.5
                                          ? 'bg-background-tertiary text-primary border-primary'
                                          : effectiveRating >= 5.5
                                          ? 'bg-background-tertiary text-text-primary border-border'
                                          : 'bg-background-tertiary text-status-error border-status-error'
                                      }`}
                                      title={isCompleted ? `Maç Performans Reytingi: ${Number(effectiveRating).toFixed(1)}/10` : `Form Puanı: ${Number(effectiveRating).toFixed(1)}/10`}
                                    >
                                      {Number(effectiveRating).toFixed(1)}
                                    </span>
                                  ) : isCompleted ? (
                                    <span className="text-xs tabular-nums text-text-tertiary px-1" title="Değerlendirilmedi">
                                      —
                                    </span>
                                  ) : null}
                                  <span className={`text-xs font-semibold px-2 py-0.5 rounded-sm border ${getPositionBadgeClass(p.position)}`}>
                                    {formatPosition(p.position)}
                                  </span>
                                  <ExternalLink className="w-3.5 h-3.5 text-text-tertiary group-hover:text-text-secondary transition-colors" />
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Substitutes Bench */}
                  {awayLineup?.substitutes?.length > 0 && (
                    <div className="pt-4 border-t border-border space-y-2.5">
                      <span className="text-xs font-semibold text-text-primary block">
                        Yedek Kulübesi ({awayLineup.substitutes.length})
                      </span>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {awayLineup.substitutes.map((sub, idx) => {
                          const pStat = (playerStats?.away || []).find(ps => String(ps.id) === String(sub.id));
                          const effectiveRating = (isCompleted && pStat?.rating != null) ? pStat.rating : (pStat?.rating != null ? pStat.rating : sub.rating);

                          return (
                            <div 
                              key={sub.id || idx}
                              onClick={(e) => handlePlayerClick(sub, 'away', e)}
                              className="flex items-center justify-between p-2 rounded hover:bg-background-tertiary transition-all cursor-pointer group text-xs"
                              title={`${sub.name} maç performansını görüntüle`}
                            >
                              <div className="flex items-center gap-2 min-w-0">
                                <PlayerAvatar 
                                  photoUrl={sub.photo_url}
                                  name={sub.name}
                                  shirt={sub.shirt}
                                  fallback="initials"
                                  size="w-6 h-6 text-xs"
                                  className="shrink-0"
                                />
                                <span className="tabular-nums text-xs font-semibold text-text-secondary">#{sub.shirt}</span>
                                <span className="font-medium text-text-primary truncate">{sub.name}</span>
                                {pStat?.goals > 0 && <span className="text-xs bg-background-tertiary text-status-success font-semibold px-1 rounded border border-status-success">G: {pStat.goals}</span>}
                                {pStat?.assists > 0 && <span className="text-xs bg-background-tertiary text-primary font-semibold px-1 rounded border border-primary">A: {pStat.assists}</span>}
                                {pStat?.red_cards > 0 ? <RedCardIcon /> : pStat?.yellow_cards > 0 ? <YellowCardIcon /> : null}
                              </div>
                              <div className="flex items-center gap-1.5 shrink-0">
                                {effectiveRating != null && (
                                  <span className={`text-xs tabular-nums font-semibold px-1.5 py-0.2 rounded border ${
                                    effectiveRating >= 7.5 ? 'bg-background-tertiary text-status-success border-status-success' :
                                    effectiveRating >= 6.5 ? 'bg-background-tertiary text-primary border-primary' :
                                    effectiveRating >= 5.5 ? 'bg-background-tertiary text-text-primary border-border' :
                                    'bg-background-tertiary text-status-error border-status-error'
                                  }`}>
                                    {Number(effectiveRating).toFixed(1)}
                                  </span>
                                )}
                                <span className={`text-xs font-semibold px-1.5 py-0.2 rounded border shrink-0 ${getPositionBadgeClass(sub.position)}`}>
                                  {formatPosition(sub.position)}
                                </span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>

                  </div>
                )}
              </>
            )}
          </div>

        
  );
}
