import { ArrowRightLeft, Clock, Timer } from 'lucide-react';
import PlayerAvatar from '../PlayerAvatar';
import { BallIcon, MissedPenaltyIcon, PenaltyBallIcon, RedCardIcon, YellowCardIcon } from './eventIcons';

export default function MatchTimelineTab({ timeline, homeTeam, awayTeam, homeTeamId }) {
  return (

          <div className="space-y-6 max-w-5xl mx-auto py-2">
            
            {/* Header with team names */}
            <div className="grid grid-cols-2 text-center pb-4 border-b border-border">
              <div className="flex items-center justify-center gap-2 pr-4 border-r border-border">
                <img src={homeTeam.badge} alt="" className="w-5 h-5 object-contain" />
                <h4 className="text-xs sm:text-sm font-semibold text-text-primary uppercase tracking-wider truncate">
                  {homeTeam.name}
                </h4>
              </div>
              <div className="flex items-center justify-center gap-2 pl-4">
                <h4 className="text-xs sm:text-sm font-semibold text-text-primary uppercase tracking-wider truncate">
                  {awayTeam.name}
                </h4>
                <img src={awayTeam.badge} alt="" className="w-5 h-5 object-contain" />
              </div>
            </div>

            {timeline.length === 0 ? (
              <div className="py-16 text-center text-sm text-text-secondary font-medium">
                Bu karşılaşma için zaman akışı kaydı bulunamadı.
              </div>
            ) : (
              <div className="relative py-4 before:content-[''] before:absolute before:left-1/2 before:-translate-x-1/2 before:top-2 before:bottom-2 before:w-0.5 before:bg-background-tertiary">
                <div className="space-y-6">
                  {timeline.map((item, idx) => {
                    const isGoal = item.type === 'goal';
                    const isPenaltyGoal = isGoal && item.is_penalty;
                    const isOwnGoal = isGoal && item.is_own_goal;
                    const isMissedPenalty = item.type === 'penalty_missed';
                    const isYellowCard = item.type === 'yellow_card';
                    const isRedCard = item.type === 'red_card';
                    const isSub = item.type === 'substitution';
                    const isAddedTime = item.type === 'added_time';
                    const isPeriod = item.type === 'period_start' || item.type === 'period_end';

                    // Center Neutral Banners (Period start / end, added time)
                    if (isPeriod || isAddedTime) {
                      return (
                        <div key={idx} className="relative z-10 flex items-center justify-center my-4">
                          <div className="bg-background-tertiary hover:bg-background-tertiary border border-border text-text-primary px-4 py-1.5 rounded-full  flex items-center gap-2.5 text-xs transition-colors">
                            {isAddedTime ? (
                              <Timer className="w-3.5 h-3.5 text-primary" />
                            ) : (
                              <Clock className="w-3.5 h-3.5 text-text-primary" />
                            )}
                            <span className="font-semibold text-text-primary">
                              {item.label} {isAddedTime ? `(${item.description})` : ''}
                            </span>
                            {item.score && (
                              <span className="font-mono font-semibold text-text-primary bg-background-primary px-2 py-0.5 rounded border border-border text-xs">
                                {item.score}
                              </span>
                            )}
                            <span className="font-mono font-semibold text-text-secondary text-xs">
                              {item.minute}
                            </span>
                          </div>
                        </div>
                      );
                    }

                    // Determine if Home or Away
                    const isHome = Boolean(
                      (item.team_id && Number(item.team_id) === Number(homeTeamId)) ||
                      (item.team_name && homeTeam.name && item.team_name.toLowerCase().includes(homeTeam.name.toLowerCase()))
                    );

                    const renderEventBadgeIcon = () => {
                      if (isPenaltyGoal) return <PenaltyBallIcon className="w-3.5 h-3.5 text-status-success" />;
                      if (isOwnGoal) return <BallIcon className="w-3.5 h-3.5 text-status-error" />;
                      if (isGoal) return <BallIcon className="w-3.5 h-3.5 text-text-primary" />;
                      if (isMissedPenalty) return <MissedPenaltyIcon className="w-3.5 h-3.5 text-status-error" />;
                      if (isYellowCard) return <YellowCardIcon className="w-2.5 h-3.5" />;
                      if (isRedCard) return <RedCardIcon className="w-2.5 h-3.5" />;
                      if (isSub) return <ArrowRightLeft className="w-3.5 h-3.5 text-text-secondary" />;
                      return <Clock className="w-3.5 h-3.5 text-text-secondary" />;
                    };

                    const renderCardContent = () => (
                      <div className="p-3 rounded border border-border hover:border-border bg-background-primary  transition-all text-xs">
                        {/* Goal */}
                        {isGoal && (
                          <div className={`flex items-center gap-2.5 ${isHome ? 'flex-row-reverse text-right' : 'flex-row text-left'}`}>
                            <PlayerAvatar 
                              photoUrl={item.photo_url} 
                              name={item.player_name} 
                              size="w-7 h-7 text-xs" 
                              className="shrink-0"
                            />
                            <div className="min-w-0 flex-1">
                              <div className={`flex items-center gap-1.5 font-semibold text-text-primary text-xs sm:text-sm ${isHome ? 'justify-end' : 'justify-start'}`}>
                                <span className="truncate">{item.player_name}</span>
                                {isPenaltyGoal && (
                                  <span className="text-xs font-mono font-semibold text-status-success bg-background-tertiary border border-status-success px-1.5 py-0.2 rounded shrink-0">
                                    Penaltı
                                  </span>
                                )}
                                {isOwnGoal && (
                                  <span className="text-xs font-mono font-semibold text-status-error bg-background-tertiary border border-status-error px-1.5 py-0.2 rounded shrink-0">
                                    Kendi Kalesine
                                  </span>
                                )}
                              </div>
                              <div className="text-xs text-text-secondary mt-0.5">
                                {item.assist_name && (
                                  <span>Asist: <strong className="text-text-primary">{item.assist_name}</strong></span>
                                )}
                              </div>
                            </div>
                            {item.score && (
                              <span className="font-mono font-semibold text-text-primary bg-background-tertiary border border-border px-2.5 py-1 rounded text-xs sm:text-sm shrink-0">
                                {item.score}
                              </span>
                            )}
                          </div>
                        )}

                        {/* Missed Penalty */}
                        {isMissedPenalty && (
                          <div className={`space-y-0.5 ${isHome ? 'text-right' : 'text-left'}`}>
                            <div className="font-semibold text-status-error text-xs flex items-center gap-1.5">
                              <span>Kaçan Penaltı</span>
                              {item.player_name && <span className="text-text-primary">• {item.player_name}</span>}
                            </div>
                            <p className="text-xs text-text-secondary truncate">
                              {item.description}
                            </p>
                          </div>
                        )}

                        {/* Yellow Card or Red Card */}
                        {(isYellowCard || isRedCard) && (
                          <div className={`flex items-center gap-2.5 ${isHome ? 'flex-row-reverse text-right' : 'flex-row text-left'}`}>
                            <PlayerAvatar 
                              photoUrl={item.photo_url} 
                              name={item.player_name} 
                              size="w-7 h-7 text-xs" 
                              className="shrink-0"
                            />
                            <div className="min-w-0 flex-1">
                              <span className="font-semibold text-text-primary block truncate">
                                {item.player_name}
                              </span>
                              <span className="text-xs font-mono font-semibold text-text-secondary uppercase">
                                {isYellowCard ? 'Sarı Kart' : 'Kırmızı Kart'}
                              </span>
                            </div>
                            <div className="shrink-0">
                              {isYellowCard ? <YellowCardIcon /> : <RedCardIcon />}
                            </div>
                          </div>
                        )}

                        {/* Substitution */}
                        {isSub && (
                          <div className={`space-y-1 ${isHome ? 'text-right' : 'text-left'}`}>
                            <div className={`flex items-center gap-1.5 text-xs ${isHome ? 'justify-end' : 'justify-start'}`}>
                              <span className="text-status-success font-semibold font-mono">▲</span>
                              <span className="font-semibold text-text-primary truncate">{item.player_in_name}</span>
                            </div>
                            <div className={`flex items-center gap-1.5 text-xs text-text-secondary ${isHome ? 'justify-end' : 'justify-start'}`}>
                              <span className="text-status-error font-semibold font-mono">▼</span>
                              <span className="text-text-secondary truncate">{item.player_out_name}</span>
                            </div>
                          </div>
                        )}
                      </div>
                    );

                    return (
                      <div key={idx} className="relative grid grid-cols-2 gap-8 items-center">
                        
                        {/* Center Minute Marker & Icon on the line */}
                        <div className="absolute left-1/2 -translate-x-1/2 top-1/2 -translate-y-1/2 z-10 flex flex-col items-center">
                          <div className="w-8 h-8 rounded-full border-2 border-border bg-background-primary flex items-center justify-center ">
                            {renderEventBadgeIcon()}
                          </div>
                          <span className="font-mono font-semibold text-xs text-text-secondary bg-background-tertiary border border-border px-1.5 py-0.2 rounded-md mt-0.5 ">
                            {item.minute}
                          </span>
                        </div>

                        {/* Left Side (Home Team) */}
                        <div className="pr-6">
                          {isHome ? renderCardContent() : <div />}
                        </div>

                        {/* Right Side (Away Team) */}
                        <div className="pl-6">
                          {!isHome ? renderCardContent() : <div />}
                        </div>

                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

  );
}
