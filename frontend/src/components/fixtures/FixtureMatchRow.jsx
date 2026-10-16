import { ChevronRight, Clock, Sparkles } from 'lucide-react';
import { handleTeamBadgeError } from '../../utils/imageFallbacks';

export default function FixtureMatchRow({ match: m, home, away, onMatchClick, onSelectTeam }) {
  const isCompleted = m.status === 'COMPLETED' && m.home_score !== null;

  return (
<div
  onClick={() => onMatchClick(m)}
  className="px-3.5 py-2.5 sm:px-4 sm:py-3 hover:bg-slate-50/90 transition-all cursor-pointer group flex items-center justify-between gap-2 sm:gap-4 text-xs"
>
  {/* 1. Status / Kickoff Time */}
  <div className="w-14 sm:w-20 shrink-0 text-left">
    {isCompleted ? (
      <span className="font-mono font-bold text-slate-500 text-[11px] block">
        MS
      </span>
    ) : (
      <div className="flex items-center gap-1 text-slate-700 font-semibold text-[11px] sm:text-xs">
        <Clock className="w-3 h-3 text-slate-400 shrink-0 hidden sm:inline" />
        <span className="truncate">{m.time_label || 'vs'}</span>
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
        className="font-bold text-xs sm:text-sm text-slate-900 hover:text-[#38003c] hover:underline transition-colors truncate"
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
        <span className="px-2.5 py-1 rounded-lg bg-slate-900 text-white font-mono font-black text-xs sm:text-sm tracking-wider shadow-2xs">
          {m.home_score} - {m.away_score}
        </span>
      ) : (
        <span className="px-2.5 py-1 rounded-lg bg-slate-100 text-slate-600 font-mono text-xs font-bold border border-slate-200">
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
        className="font-bold text-xs sm:text-sm text-slate-900 hover:text-[#38003c] hover:underline transition-colors truncate"
        aria-label={`${away.name} takım profiline git`}
      >
        {away.short || away.name}
      </button>
    </div>
  </div>

  {/* 3. Prediction / Meta Badge & Chevron */}
  <div className="flex items-center gap-2 shrink-0 min-w-[70px] sm:min-w-[120px] justify-end">
    {m.prediction?.favorite_label ? (
      <span className="hidden sm:inline-flex items-center gap-1 text-[10px] font-bold text-[#38003c] bg-purple-50 border border-purple-200 px-2 py-0.5 rounded-full truncate max-w-[110px]">
        <Sparkles className="w-2.5 h-2.5 text-[#38003c] shrink-0" />
        <span className="truncate">{m.prediction.favorite_label}</span>
      </span>
    ) : isCompleted && (m.home_xg != null || m.away_xg != null) ? (
      <span className="hidden sm:inline-block text-[10px] font-mono text-slate-400 bg-slate-50 px-1.5 py-0.5 rounded border border-slate-200">
        xG {Number(m.home_xg).toFixed(1)}-{Number(m.away_xg).toFixed(1)}
      </span>
    ) : null}
    <span className="text-[11px] font-bold text-[#38003c] group-hover:text-purple-700 group-hover:translate-x-0.5 transition-all flex items-center gap-0.5 bg-slate-50 group-hover:bg-purple-50 p-1.5 rounded-lg border border-slate-200/80">
      <ChevronRight className="w-3.5 h-3.5" />
    </span>
  </div>
</div>
                          
  );
}
