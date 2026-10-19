import { ArrowLeft, Calendar, CheckCircle2, Clock, MapPin, RotateCw, Scale, Users } from 'lucide-react';
import { handleTeamBadgeError } from '../../utils/imageFallbacks';
import TeamForm from '../TeamForm';
import { RedCardIcon } from './eventIcons';

export default function MatchScoreboard({ match, homeTeam, awayTeam, homeManager, awayManager, isCompleted, loading, meta, homeRedCards, awayRedCards, homeGoals, awayGoals, recentForm, onBack, onRefresh }) {
  return (
    <>
      {/* Top Navigation & Context Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 bg-background-primary p-3.5 sm:p-4 rounded border border-border ">
            
            {/* Back Button & Breadcrumbs */}
            <div className="flex items-center gap-3">
              <button
                onClick={onBack}
                className="inline-flex items-center gap-2 px-3 h-9 rounded border border-border bg-background-primary hover:bg-background-tertiary text-text-primary font-medium text-sm transition-colors cursor-pointer group"
              >
                <ArrowLeft className="w-4 h-4 " />
                <span>Fikstüre Dön</span>
              </button>

              <div className="hidden sm:flex items-center gap-2 text-xs text-text-secondary font-medium">
                <span className="font-semibold text-text-primary">Premier League</span>
                <span>/</span>
                <span>{match.gameweek ? `${match.gameweek}. Hafta` : 'Maç Detayı'}</span>
                <span>/</span>
                <span className="font-semibold text-text-primary">{homeTeam.short} vs {awayTeam.short}</span>
              </div>
            </div>

            {/* Right Action: Refresh & Status Pill */}
            <div className="flex items-center gap-2">
              {isCompleted ? (
                <span className="inline-flex items-center gap-1.5 text-sm text-text-secondary">
                  <CheckCircle2 className="w-3.5 h-3.5 text-text-secondary" />
                  <span>Tamamlandı</span>
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 text-sm text-text-secondary">
                  <Clock className="w-3.5 h-3.5 text-primary" />
                  <span>{match.time_label || match.kickoff_label || 'Başlama Saati'}</span>
                </span>
              )}

              <button
                onClick={() => onRefresh()}
                title="Maç verilerini sunucudan yenile"
                className="p-2 rounded bg-background-tertiary hover:bg-background-tertiary text-text-secondary hover:text-text-primary transition-colors"
              >
                <RotateCw className={`w-4 h-4 ${loading ? 'animate-spin text-status-success' : ''}`} />
              </button>
            </div>

          </div>

          {/* Hero Scoreboard Banner: Compact & Balanced */}
          <div className="bg-background-primary border border-border  rounded p-4 sm:p-6 text-text-primary relative">
            <div className="relative z-10 flex flex-col md:flex-row items-center justify-between gap-4 sm:gap-6">
              
              {/* Home Team */}
              <div className="flex items-center gap-3 sm:gap-4 flex-1 w-full md:w-auto">
                <div className="relative flex items-center gap-2 shrink-0">
                  <img 
                    src={homeTeam.badge} 
                    alt={homeTeam.name} 
                    className="w-10 h-10 sm:w-12 sm:h-12 object-contain drop- shrink-0"
                    onError={handleTeamBadgeError}
                  />
                  {/* Home Team Red Card Badge */}
                  {homeRedCards > 0 && (
                    <div 
                      className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-background-tertiary border border-status-error " 
                      title={`${homeTeam.name} - ${homeRedCards} Kırmızı Kart`}
                    >
                      <RedCardIcon className="w-3 h-4" />
                      {homeRedCards > 1 && (
                        <span className="text-xs font-mono font-semibold text-status-error">x{homeRedCards}</span>
                      )}
                    </div>
                  )}
                </div>
                <div className="min-w-0">
                  <span className="text-xs font-semibold text-text-secondary uppercase tracking-wider block">
                    Ev Sahibi
                  </span>
                  <h2 className="text-lg sm:text-xl md:text-2xl font-semibold text-text-primary tracking-tight leading-tight truncate">
                    {homeTeam.name}
                  </h2>
                  {homeManager && (
                    <p className="text-xs text-text-secondary font-medium truncate">TD: {homeManager}</p>
                  )}
                  <div className="mt-1 flex items-center gap-1" aria-label={`${homeTeam.name} maç öncesi son 5 maç formu`}>
                    <TeamForm results={recentForm[String(match?.home_id)] || []} />
                  </div>
                </div>
              </div>

              {/* Center Scoreboard / Time Display */}
              <div className="flex flex-col items-center justify-center shrink-0 px-3 py-1 text-center">
                
                {/* Score or VS Badge */}
                <div className="flex items-center gap-2">
                  {isCompleted ? (
                    <div className="font-mono text-3xl sm:text-4xl font-semibold text-text-primary px-4 py-1 rounded bg-background-tertiary border border-border  tracking-tight">
                      {match.home_score} - {match.away_score}
                    </div>
                  ) : (
                    <div className="font-mono text-xl sm:text-2xl font-semibold text-text-primary px-4 py-1 rounded bg-background-tertiary border border-border  tracking-widest">
                      VS
                    </div>
                  )}
                </div>

                {/* Halftime score */}
                {isCompleted && meta.halfTimeScore?.homeScore != null && meta.halfTimeScore?.awayScore != null && (
                  <span className="text-xs font-mono text-text-secondary mt-1 font-semibold">
                    İY {meta.halfTimeScore.homeScore} - {meta.halfTimeScore.awayScore}
                  </span>
                )}

                {/* xG Metric Pill */}
                {isCompleted && (
                  <div className="mt-2">
                    {((match.home_xg ?? meta.home_xg) != null || (match.away_xg ?? meta.away_xg) != null) ? (
                      <span className="text-sm font-mono font-medium text-text-primary inline-flex items-center gap-1.5 tabular-nums ">
                        <span className="text-xs font-sans font-semibold text-status-error uppercase tracking-wider">xG:</span>
                        {(match.home_xg ?? meta.home_xg) != null ? Number(match.home_xg ?? meta.home_xg).toFixed(2) : '-'} - {(match.away_xg ?? meta.away_xg) != null ? Number(match.away_xg ?? meta.away_xg).toFixed(2) : '-'}
                      </span>
                    ) : (
                      <span className="text-xs font-mono text-text-tertiary italic">
                        xG: Not Found
                      </span>
                    )}
                  </div>
                )}

              </div>

              {/* Away Team */}
              <div className="flex items-center justify-end gap-3 sm:gap-4 flex-1 w-full md:w-auto text-right">
                <div className="min-w-0">
                  <span className="text-xs font-semibold text-text-secondary uppercase tracking-wider block">
                    Deplasman
                  </span>
                  <h2 className="text-lg sm:text-xl md:text-2xl font-semibold text-text-primary tracking-tight leading-tight truncate">
                    {awayTeam.name}
                  </h2>
                  {awayManager && (
                    <p className="text-xs text-text-secondary font-medium truncate">TD: {awayManager}</p>
                  )}
                  <div className="mt-1 flex items-center gap-1 justify-end" aria-label={`${awayTeam.name} maç öncesi son 5 maç formu`}>
                    <TeamForm results={recentForm[String(match?.away_id)] || []} />
                  </div>
                </div>
                <div className="relative flex items-center gap-2 shrink-0">
                  {/* Away Team Red Card Badge */}
                  {awayRedCards > 0 && (
                    <div 
                      className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-background-tertiary border border-status-error " 
                      title={`${awayTeam.name} - ${awayRedCards} Kırmızı Kart`}
                    >
                      <RedCardIcon className="w-3 h-4" />
                      {awayRedCards > 1 && (
                        <span className="text-xs font-mono font-semibold text-status-error">x{awayRedCards}</span>
                      )}
                    </div>
                  )}
                  <img 
                    src={awayTeam.badge} 
                    alt={awayTeam.name} 
                    className="w-10 h-10 sm:w-12 sm:h-12 object-contain drop- shrink-0"
                    onError={handleTeamBadgeError}
                  />
                </div>
              </div>

            </div>

            {isCompleted && (homeGoals.length > 0 || awayGoals.length > 0) && (
              <div className="relative z-10 mt-5 border-t border-border-light pt-4">
                <div className="grid grid-cols-2 gap-4">
                  {[{ goals: homeGoals, align: 'text-left' }, { goals: awayGoals, align: 'text-right' }].map((side, sideIndex) => (
                    <div key={sideIndex} className={`min-w-0 space-y-1 ${side.align}`}>
                      {side.goals.map((goal, index) => (
                        <p key={`${goal.minute}-${goal.player_id || index}`} className="text-xs sm:text-xs leading-4 text-text-secondary truncate">
                          <span className="font-semibold text-text-primary">{goal.minute}</span>{' '}
                          {goal.player_name || 'Bilinmeyen Oyuncu'}{goal.is_own_goal ? ' (KK)' : ''}
                        </p>
                      ))}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Hero Footer Meta Details (No emojis) */}
            <div className="mt-6 pt-4 border-t border-border-light flex flex-wrap items-center justify-center gap-5 sm:gap-8 text-xs text-text-secondary font-medium">
              <div className="flex items-center gap-1.5">
                <Calendar className="w-4 h-4 text-text-tertiary" />
                <span>{match.kickoff_label || meta.kickoff_label || match.time_label || 'Tarih Belirtilmedi'}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <MapPin className="w-4 h-4 text-text-tertiary" />
                <span>{match.ground_name || meta.ground || homeTeam.stadium || 'Premier League Stadı'}</span>
              </div>
              {(match.referee_name || meta.referee) && (
                <div className="flex items-center gap-1.5">
                  <Scale className="w-4 h-4 text-text-tertiary" />
                  <span>Hakem: <strong className="text-text-primary font-semibold">{match.referee_name || meta.referee}</strong></span>
                </div>
              )}
              {meta.attendance && (
                <div className="flex items-center gap-1.5">
                  <Users className="w-4 h-4 text-text-tertiary" />
                  <span>{Number(meta.attendance).toLocaleString()} Seyirci</span>
                </div>
              )}
            </div>

          </div>
    </>
  );
}
