import { handleTeamBadgeError } from '../../utils/imageFallbacks';
import TeamForm from '../TeamForm';

export default function FixtureMatchCard({
  match: m,
  home,
  away,
  homeForm,
  awayForm,
  onMatchClick,
  onSelectTeam,
}) {
  const isCompleted = m.status === 'COMPLETED' && m.home_score !== null;
  const nameClass = (won, lost) => (won ? 'font-semibold text-text-primary' : lost ? 'font-normal text-text-secondary' : 'font-normal text-text-primary');
  const homeWon = isCompleted && m.home_score > m.away_score;
  const awayWon = isCompleted && m.away_score > m.home_score;
  const hasXg = isCompleted && (m.home_xg != null || m.away_xg != null);
  const tag = m.prediction?.favorite_label
    ? `Öngörü: ${m.prediction.favorite_label}`
    : hasXg
      ? `xG ${m.home_xg != null ? Number(m.home_xg).toFixed(1) : '-'} - ${m.away_xg != null ? Number(m.away_xg).toFixed(1) : '-'}`
      : null;

  return (
    <article
      onClick={() => onMatchClick(m)}
      onKeyDown={(event) => {
        if (event.key === 'Enter' && event.target === event.currentTarget) onMatchClick(m);
      }}
      tabIndex={0}
      className="bg-background-primary border border-border hover:border-card-border-hover rounded p-4 transition-colors duration-150 ease-out cursor-pointer flex flex-col gap-3 focus:outline-none focus-visible:ring-2 focus-visible:ring-border-focus"
    >
      <div className="flex items-center justify-between gap-3 text-xs text-text-secondary">
        <span className="truncate tabular-nums">{m.time_label || m.kickoff_label}</span>
        {tag && <span className="shrink-0 truncate tabular-nums">{tag}</span>}
      </div>

      <div className="grid grid-cols-versus items-center gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <img
            src={home.badge}
            alt=""
            className="w-6 h-6 object-contain shrink-0"
            onError={handleTeamBadgeError}
          />
          <button
            type="button"
            onClick={(event) => { event.stopPropagation(); onSelectTeam?.(home.id); }}
            className={`text-sm ${nameClass(homeWon, awayWon)} hover:underline truncate text-left rounded-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-border-focus`}
            aria-label={`${home.name} takım profiline git`}
          >
            {home.name}
          </button>
        </div>

        <span className={`min-w-12 text-center text-lg tabular-nums ${isCompleted ? 'font-semibold text-text-primary' : 'text-text-tertiary'}`}>
          {isCompleted ? `${m.home_score} - ${m.away_score}` : 'vs'}
        </span>

        <div className="flex items-center gap-2 min-w-0 justify-end">
          <button
            type="button"
            onClick={(event) => { event.stopPropagation(); onSelectTeam?.(away.id); }}
            className={`text-sm ${nameClass(awayWon, homeWon)} hover:underline truncate text-right rounded-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-border-focus`}
            aria-label={`${away.name} takım profiline git`}
          >
            {away.name}
          </button>
          <img
            src={away.badge}
            alt=""
            className="w-6 h-6 object-contain shrink-0"
            onError={handleTeamBadgeError}
          />
        </div>
      </div>

      <div className="flex items-center justify-between gap-2 pt-3 border-t border-border-light text-xs text-text-secondary">
        <div aria-label={`${home.name} son 5 maç formu`}>
          <TeamForm results={homeForm} />
        </div>
        <span className="shrink-0">Son 5 maç</span>
        <div aria-label={`${away.name} son 5 maç formu`}>
          <TeamForm results={awayForm} />
        </div>
      </div>
    </article>
  );
}
