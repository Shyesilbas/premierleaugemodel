import { ChevronRight } from 'lucide-react';
import { handleTeamBadgeError } from '../../utils/imageFallbacks';

export default function FixtureMatchRow({ match: m, home, away, onMatchClick, onSelectTeam }) {
  const isCompleted = m.status === 'COMPLETED' && m.home_score !== null;
  const nameClass = (won, lost) => (won ? 'font-semibold text-text-primary' : lost ? 'font-normal text-text-secondary' : 'font-normal text-text-primary');
  const homeWon = isCompleted && m.home_score > m.away_score;
  const awayWon = isCompleted && m.away_score > m.home_score;
  const hasXg = isCompleted && (m.home_xg != null || m.away_xg != null);
  const tag = m.prediction?.favorite_label
    ? m.prediction.favorite_label
    : hasXg
      ? `xG ${Number(m.home_xg).toFixed(1)} - ${Number(m.away_xg).toFixed(1)}`
      : null;

  return (
    <div
      onClick={() => onMatchClick(m)}
      onKeyDown={(event) => {
        if (event.key === 'Enter' && event.target === event.currentTarget) onMatchClick(m);
      }}
      tabIndex={0}
      className="px-3 py-2.5 sm:px-4 sm:py-3 hover:bg-background-tertiary transition-colors duration-150 ease-out cursor-pointer flex items-center gap-3 sm:gap-4 text-sm focus:outline-none focus-visible:bg-background-tertiary"
    >
      <span className="w-14 sm:w-20 shrink-0 text-xs text-text-secondary truncate tabular-nums">
        {isCompleted ? 'Bitti' : (m.time_label || '')}
      </span>

      <div className="grid grid-cols-versus items-center gap-2 sm:gap-4 flex-1 min-w-0">
        <div className="flex items-center justify-end gap-2 min-w-0 text-right">
          <button
            type="button"
            onClick={(event) => { event.stopPropagation(); onSelectTeam?.(home.id); }}
            className={`${nameClass(homeWon, awayWon)} hover:underline truncate rounded-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-border-focus`}
            aria-label={`${home.name} takım profiline git`}
          >
            {home.short || home.name}
          </button>
          <img
            src={home.badge}
            alt=""
            className="w-5 h-5 sm:w-6 sm:h-6 object-contain shrink-0"
            onError={handleTeamBadgeError}
          />
        </div>

        <span className={`min-w-12 text-center tabular-nums ${isCompleted ? 'font-semibold text-text-primary' : 'text-text-tertiary'}`}>
          {isCompleted ? `${m.home_score} - ${m.away_score}` : 'vs'}
        </span>

        <div className="flex items-center gap-2 min-w-0">
          <img
            src={away.badge}
            alt=""
            className="w-5 h-5 sm:w-6 sm:h-6 object-contain shrink-0"
            onError={handleTeamBadgeError}
          />
          <button
            type="button"
            onClick={(event) => { event.stopPropagation(); onSelectTeam?.(away.id); }}
            className={`${nameClass(awayWon, homeWon)} hover:underline truncate rounded-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-border-focus`}
            aria-label={`${away.name} takım profiline git`}
          >
            {away.short || away.name}
          </button>
        </div>
      </div>

      <div className="flex items-center gap-2 shrink-0 justify-end sm:w-32">
        {tag && <span className="hidden sm:block text-xs text-text-secondary truncate tabular-nums">{tag}</span>}
        <ChevronRight className="w-4 h-4 text-text-tertiary" strokeWidth={1.5} aria-hidden="true" />
      </div>
    </div>
  );
}
