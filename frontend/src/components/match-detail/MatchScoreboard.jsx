import { ArrowLeft, RotateCw } from 'lucide-react';
import { handleTeamBadgeError } from '../../utils/imageFallbacks';
import TeamForm from '../TeamForm';
import { RedCardIcon } from './eventIcons';

const formatXg = (value) => (value != null ? Number(value).toFixed(2) : '-');

function RedCardBadge({ count, teamName }) {
  if (!count) return null;
  return (
    <span
      className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-sm border border-status-error bg-background-primary"
      title={`${teamName} - ${count} Kırmızı Kart`}
    >
      <RedCardIcon className="w-3 h-4" />
      {count > 1 && <span className="text-xs font-semibold tabular-nums text-status-error">x{count}</span>}
    </span>
  );
}

function TeamBlock({ team, manager, form, redCards, side }) {
  const isAway = side === 'away';
  return (
    <div className={`flex flex-1 min-w-0 items-center gap-3 ${isAway ? 'flex-row-reverse text-right' : ''}`}>
      <img
        src={team.badge}
        alt=""
        className="w-10 h-10 object-contain shrink-0"
        onError={handleTeamBadgeError}
      />
      <div className="min-w-0">
        <div className={`flex items-center gap-2 ${isAway ? 'justify-end' : ''}`}>
          <h2 className="text-lg font-semibold text-text-primary leading-tight truncate">
            <span className="sm:hidden">{team.short || team.name}</span>
            <span className="hidden sm:inline">{team.name}</span>
          </h2>
          <RedCardBadge count={redCards} teamName={team.name} />
        </div>
        {manager && <p className="text-xs text-text-secondary truncate hidden sm:block">{manager}</p>}
        <TeamForm
          results={form}
          className={`mt-1 ${isAway ? 'justify-end' : ''}`}
          label={`${team.name} maç öncesi son 5 maç formu`}
        />
      </div>
    </div>
  );
}

export default function MatchScoreboard({ match, homeTeam, awayTeam, homeManager, awayManager, isCompleted, loading, meta, homeRedCards, awayRedCards, homeGoals, awayGoals, recentForm, onBack, onRefresh }) {
  const homeXg = match.home_xg ?? meta.home_xg;
  const awayXg = match.away_xg ?? meta.away_xg;
  const hasXg = homeXg != null || awayXg != null;
  const halfTime = meta.halfTimeScore;
  const hasHalfTime = isCompleted && halfTime?.homeScore != null && halfTime?.awayScore != null;
  const hasGoals = isCompleted && (homeGoals.length > 0 || awayGoals.length > 0);

  const contextItems = [
    match.gameweek ? `${match.gameweek}. Hafta` : null,
    match.kickoff_label || meta.kickoff_label || match.time_label,
    match.ground_name || meta.ground || homeTeam.stadium,
    (match.referee_name || meta.referee) ? `Hakem: ${match.referee_name || meta.referee}` : null,
    meta.attendance ? `${Number(meta.attendance).toLocaleString()} seyirci` : null,
  ].filter(Boolean);

  return (
    <section className="bg-background-primary border border-border rounded" aria-label="Maç özeti">
      <div className="flex items-center justify-between gap-3 px-4 py-2 border-b border-border-light">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-2 h-9 -ml-2 px-2 rounded text-sm font-medium text-text-secondary hover:text-text-primary hover:bg-background-tertiary transition-colors cursor-pointer focus-visible:outline-none focus-visible:border-border-focus"
        >
          <ArrowLeft className="w-4 h-4" strokeWidth={1.5} aria-hidden="true" />
          <span>Fikstür</span>
        </button>

        <div className="flex items-center gap-3">
          <span className="text-xs text-text-secondary">{isCompleted ? 'Tamamlandı' : 'Oynanmadı'}</span>
          <button
            type="button"
            onClick={onRefresh}
            disabled={loading}
            aria-label="Maç verilerini yenile"
            title="Maç verilerini yenile"
            className="inline-flex items-center justify-center w-9 h-9 rounded text-text-secondary hover:text-text-primary hover:bg-background-tertiary transition-colors cursor-pointer disabled:cursor-default disabled:opacity-60 focus-visible:outline-none focus-visible:border-border-focus"
          >
            <RotateCw className={`w-4 h-4 ${loading ? 'animate-spin motion-reduce:animate-none' : ''}`} strokeWidth={1.5} aria-hidden="true" />
          </button>
        </div>
      </div>

      <div className="px-4 py-4">
        <div className="flex items-center justify-between gap-3">
          <TeamBlock
            team={homeTeam}
            manager={homeManager}
            form={recentForm[String(match?.home_id)] || []}
            redCards={homeRedCards}
            side="home"
          />

          <div className="flex flex-col items-center shrink-0 text-center min-w-20">
            {isCompleted ? (
              <span className="text-3xl font-semibold tabular-nums text-text-primary leading-none">
                {match.home_score} - {match.away_score}
              </span>
            ) : (
              <span className="text-xl font-medium text-text-muted leading-none">vs</span>
            )}
            {hasHalfTime && (
              <span className="mt-1.5 text-xs tabular-nums text-text-secondary">
                İY {halfTime.homeScore} - {halfTime.awayScore}
              </span>
            )}
            {isCompleted && hasXg && (
              <span className="mt-0.5 text-xs tabular-nums text-text-secondary">
                xG {formatXg(homeXg)} - {formatXg(awayXg)}
              </span>
            )}
          </div>

          <TeamBlock
            team={awayTeam}
            manager={awayManager}
            form={recentForm[String(match?.away_id)] || []}
            redCards={awayRedCards}
            side="away"
          />
        </div>

        {hasGoals && (
          <div className="mt-4 pt-3 border-t border-border-light grid grid-cols-2 gap-4">
            {[{ goals: homeGoals, align: 'text-left' }, { goals: awayGoals, align: 'text-right' }].map((side, sideIndex) => (
              <ul key={sideIndex} className={`min-w-0 space-y-0.5 ${side.align}`}>
                {side.goals.map((goal, index) => (
                  <li key={`${goal.minute}-${goal.player_id || index}`} className="text-xs text-text-secondary truncate">
                    <span className="font-semibold tabular-nums text-text-primary">{goal.minute}</span>{' '}
                    {goal.player_name || 'Bilinmeyen oyuncu'}{goal.is_own_goal ? ' (KK)' : ''}
                  </li>
                ))}
              </ul>
            ))}
          </div>
        )}
      </div>

      {contextItems.length > 0 && (
        <p className="px-4 py-2 border-t border-border-light text-xs text-text-secondary flex flex-wrap gap-x-3 gap-y-1">
          {contextItems.map((item, index) => (
            <span key={index} className="tabular-nums">{item}</span>
          ))}
        </p>
      )}
    </section>
  );
}
