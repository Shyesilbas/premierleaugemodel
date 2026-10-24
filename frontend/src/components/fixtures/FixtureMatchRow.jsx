import { ChevronRight, Clock, Sparkles } from 'lucide-react';
import { handleTeamBadgeError } from '../../utils/imageFallbacks';

export default function FixtureMatchRow({ match: m, home, away, onMatchClick, onSelectTeam }) {
  const isCompleted = m.status === 'COMPLETED' && m.home_score !== null;

  return (
<div
  onClick={() => onMatchClick(m)}
  className="px-3.5 py-2.5 sm:px-4 sm:py-3 hover:bg-background-tertiary transition-colors cursor-pointer group flex items-center justify-between gap-2 sm:gap-4 text-xs"
>
  {/* 1. Status / Kickoff Time */}
  <div className="w-14 sm:w-20 shrink-0 text-left">
    {isCompleted ? (
      <span className="font-mono font-medium text-text-muted text-xs block tabular-nums">
        MS
      </span>
    ) : (
      <div className="flex items-center gap-1 text-text-secondary font-medium text-xs">
        <Clock className="w-3 h-3 text-text-muted shrink-0 hidden sm:inline" />
        <span className="truncate tabular-nums">{m.time_label || 'vs'}</span>
      </div>
    )}
  </div>

  {/* 2. Teams & Score (Center) */}
  <div className="flex items-center justify-center gap-2 sm:gap-4 flex-1 min-w-0">
    {/* Home Team */}
    <div className="flex items-center gap-2 justify-end flex-1 min-w-0 text-right">
      <button
        type="button"
        onClick={(event) => { event.stopPropagation(); onSelectTeam?.(home.id); }}
        className="font-medium text-xs sm:text-sm text-text-primary hover:text-text-secondary hover:underline transition-colors truncate"
        aria-label={`${home.name} takım profiline git`}
      >
        {home.short || home.name}
      </button>
      <img 
        src={home.badge} 
        alt={home.name} 
        className="w-5 h-5 sm:w-6 sm:h-6 object-contain shrink-0"
        onError={handleTeamBadgeError}
      />
    </div>

    {/* Score / VS Badge */}
    <div className="shrink-0 flex items-center justify-center min-w-[55px] sm:min-w-[65px]">
      {isCompleted ? (
        <span className="px-2.5 py-0.5 rounded bg-primary text-white font-mono font-semibold text-xs sm:text-sm tracking-wider tabular-nums">
          {m.home_score} - {m.away_score}
        </span>
      ) : (
        <span className="px-2.5 py-0.5 rounded bg-background-tertiary text-text-secondary font-mono text-xs font-medium border border-border">
          VS
        </span>
      )}
    </div>

    {/* Away Team */}
    <div className="flex items-center gap-2 justify-start flex-1 min-w-0 text-left">
      <img 
        src={away.badge} 
        alt={away.name} 
        className="w-5 h-5 sm:w-6 sm:h-6 object-contain shrink-0"
        onError={handleTeamBadgeError}
      />
      <button
        type="button"
        onClick={(event) => { event.stopPropagation(); onSelectTeam?.(away.id); }}
        className="font-medium text-xs sm:text-sm text-text-primary hover:text-text-secondary hover:underline transition-colors truncate"
        aria-label={`${away.name} takım profiline git`}
      >
        {away.short || away.name}
      </button>
    </div>
  </div>

  {/* 3. Prediction / Meta Badge & Chevron */}
  <div className="flex items-center gap-2 shrink-0 min-w-[70px] sm:min-w-[120px] justify-end">
    {m.prediction?.favorite_label ? (
      <span className="hidden sm:inline-flex items-center gap-1 text-xs font-medium text-primary bg-background-tertiary border border-border px-2 py-0.5 rounded-sm truncate max-w-[120px]">
        <Sparkles className="w-3 h-3 text-primary shrink-0" />
        <span className="truncate">{m.prediction.favorite_label}</span>
      </span>
    ) : isCompleted && (m.home_xg != null || m.away_xg != null) ? (
      <span className="hidden sm:inline-block text-xs font-mono text-text-muted bg-background-tertiary px-1.5 py-0.5 rounded-sm border border-border tabular-nums">
        xG {Number(m.home_xg).toFixed(1)}-{Number(m.away_xg).toFixed(1)}
      </span>
    ) : null}
    <span className="text-xs text-text-secondary group-hover:text-text-primary transition-colors flex items-center p-1 rounded hover:bg-background-tertiary">
      <ChevronRight className="w-4 h-4" />
    </span>
  </div>
</div>
                          
  );
}
