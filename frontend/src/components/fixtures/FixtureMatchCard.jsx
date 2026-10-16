import { ChevronRight, Clock, MapPin, Sparkles } from 'lucide-react';
import { handleTeamBadgeError } from '../../utils/imageFallbacks';
import TeamForm from '../TeamForm';

export default function FixtureMatchCard({
  match: m,
  home,
  away,
  homeManager,
  awayManager,
  currentGameweek,
  homeForm,
  awayForm,
  onMatchClick,
  onSelectTeam,
}) {
  const isCompleted = m.status === 'COMPLETED' && m.home_score !== null;

  return (
<div
  onClick={() => onMatchClick(m)}
  className="bg-white border border-slate-200 hover:border-purple-300 rounded-2xl p-4 shadow-xs hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 cursor-pointer group flex flex-col justify-between gap-3 relative overflow-hidden"
>

{/* Top Card Bar: Kickoff time & Ground */}
<div className="flex items-center justify-between text-[11px] text-slate-500 pb-2 border-b border-slate-100">
  <div className="flex items-center gap-1.5 font-medium truncate max-w-[200px]">
    <Clock className="w-3 h-3 text-slate-400 shrink-0" />
    <span className="truncate">{m.time_label || m.kickoff_label}</span>
  </div>

  <span className="text-[11px] font-bold text-[#38003c] group-hover:text-purple-700 group-hover:translate-x-0.5 transition-all flex items-center gap-1 bg-purple-50 group-hover:bg-purple-100 px-2.5 py-0.5 rounded-lg border border-purple-200/60 shadow-2xs">
    {isCompleted 
      ? 'Maç Sayfası' 
      : (Number(m.gameweek) === Number(currentGameweek) ? 'Model Analizi & Sayfa' : 'Maç Detayı')} 
    <ChevronRight className="w-3.5 h-3.5" />
  </span>
</div>

{/* Teams & Score / Time */}
<div className="flex items-center justify-between gap-2 py-1">
  
  {/* Home Team */}
  <div className="flex items-center gap-2.5 flex-1 min-w-0">
    <img 
      src={home.badge} 
      alt={home.name} 
      className="w-7 h-7 object-contain shrink-0"
      onError={handleTeamBadgeError}
    />
    <button
      type="button"
      onClick={(event) => { event.stopPropagation(); onSelectTeam?.(home.id); }}
      className="font-bold text-xs text-slate-900 hover:text-[#38003c] hover:underline transition-colors truncate text-left"
      aria-label={`${home.name} takım profiline git`}
    >
      {home.name}
    </button>
  </div>

  {/* Center: Score or Kickoff Time */}
  <div className="shrink-0 px-3 py-1 rounded-xl bg-slate-100 border border-slate-200 font-mono font-black text-sm text-slate-900 text-center min-w-[64px]">
    {isCompleted ? (
      <span>{m.home_score} - {m.away_score}</span>
    ) : (
      <span className="text-xs font-bold text-slate-600">VS</span>
    )}
  </div>

  {/* Away Team */}
  <div className="flex items-center gap-2.5 flex-1 min-w-0 justify-end text-right">
    <button
      type="button"
      onClick={(event) => { event.stopPropagation(); onSelectTeam?.(away.id); }}
      className="font-bold text-xs text-slate-900 hover:text-[#38003c] hover:underline transition-colors truncate text-right"
      aria-label={`${away.name} takım profiline git`}
    >
      {away.name}
    </button>
    <img 
      src={away.badge} 
      alt={away.name} 
      className="w-7 h-7 object-contain shrink-0"
      onError={handleTeamBadgeError}
    />
  </div>

</div>

{(homeManager || awayManager) && (
  <div className="grid grid-cols-2 gap-2 text-[10px] text-slate-500">
    <span className="truncate" title={homeManager ? `Teknik Direktör: ${homeManager}` : undefined}>
      {homeManager ? <><span className="text-slate-400">TD:</span> <strong className="font-semibold text-slate-700">{homeManager}</strong></> : ''}
    </span>
    <span className="truncate text-right" title={awayManager ? `Teknik Direktör: ${awayManager}` : undefined}>
      {awayManager ? <><span className="text-slate-400">TD:</span> <strong className="font-semibold text-slate-700">{awayManager}</strong></> : ''}
    </span>
  </div>
)}

{/* Recent form, using the same W/D/L markers as the standings table */}
<div className="flex items-center justify-between gap-2 text-[9px] text-slate-400">
  <div className="flex items-center gap-1" aria-label={`${home.name} son 5 maç formu`}>
    <TeamForm results={homeForm} />
  </div>
  <span className="shrink-0 font-bold tracking-wide">SON 5</span>
  <div className="flex items-center gap-1" aria-label={`${away.name} son 5 maç formu`}>
    <TeamForm results={awayForm} />
  </div>
</div>

{/* Bottom Bar: Completed Micro-stats OR Ground/Status */}
{isCompleted ? (
  <div className="pt-2 border-t border-slate-100 space-y-1.5">
    <div className="flex items-center justify-between text-[11px] text-slate-500">
      <span className="flex items-center gap-1 truncate text-slate-600">
        <span className="text-slate-400">👨‍⚖️ Hakem:</span>
        <strong className="text-slate-800 font-semibold truncate">{m.referee_name || 'Bilinmiyor'}</strong>
      </span>
      {m.total_yellow_cards !== null && m.total_yellow_cards !== undefined ? (
        <div className="flex items-center gap-1 shrink-0 font-mono text-[10px]">
          <span className="px-1.5 py-0.5 rounded bg-amber-50 border border-amber-200 text-amber-900 font-bold">
            {m.total_yellow_cards} 🟨
          </span>
          {m.total_red_cards > 0 && (
            <span className="px-1.5 py-0.5 rounded bg-rose-50 border border-rose-200 text-rose-900 font-bold">
              {m.total_red_cards} 🟥
            </span>
          )}
        </div>
      ) : (
        <span className="text-[10px] text-slate-400 font-mono">
          {m.ref_avg_cards ? `Ort. ${m.ref_avg_cards} Kart` : ''}
        </span>
      )}
    </div>

    <div className="grid grid-cols-5 gap-1.5 text-[10px] font-mono text-center">
      <div className="bg-slate-50 py-1 px-1 rounded-lg">
        <span className="text-[9px] text-slate-500 font-sans block">KORNER</span>
        <strong className="text-emerald-700 font-bold">{m.home_won_corners ?? '-'} - {m.away_won_corners ?? '-'}</strong>
      </div>
      <div className="bg-slate-50 py-1 px-1 rounded-lg">
        <span className="text-[9px] text-slate-500 font-sans block">TAÇ</span>
        <strong className="text-sky-700 font-bold">{m.home_total_throws ?? '-'} - {m.away_total_throws ?? '-'}</strong>
      </div>
      <div className="bg-slate-50 py-1 px-1 rounded-lg">
        <span className="text-[9px] text-slate-500 font-sans block">ŞUT</span>
        <strong className="text-slate-800 font-bold">{m.home_total_shots ?? '-'} - {m.away_total_shots ?? '-'}</strong>
      </div>
      <div className="bg-slate-50 py-1 px-1 rounded-lg">
        <span className="text-[9px] text-slate-500 font-sans block">KURTARIŞ</span>
        <strong className="text-purple-700 font-bold">{m.total_saves ?? '-'}</strong>
      </div>
      <div className="bg-slate-50 py-1 px-1 rounded-lg border border-slate-100">
        <span className="text-[9px] text-rose-700 font-sans font-bold block">TheStatsAPI xG</span>
        {(m.home_xg != null || m.away_xg != null) ? (
          <strong className="text-rose-600 font-bold">
            {m.home_xg != null ? Number(m.home_xg).toFixed(2) : '-'} - {m.away_xg != null ? Number(m.away_xg).toFixed(2) : '-'}
          </strong>
        ) : (
          <span className="text-slate-400 font-normal italic text-[8.5px] block leading-[15px]">
            Not Found
          </span>
        )}
      </div>
    </div>
  </div>
) : (
  <div className="pt-2.5 border-t border-slate-100/90 space-y-2">
    {/* Stadium & Favorite / Gameweek Meta Header */}
    <div className="flex items-center justify-between text-[11px] text-slate-500 gap-2 px-0.5">
      <span className="flex items-center gap-1.5 truncate text-slate-500 font-medium">
        <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0" />
        <span className="truncate">{m.ground_name || 'Premier League Stadı'}</span>
      </span>
      {Number(m.gameweek) === Number(currentGameweek) && m.prediction?.favorite_label ? (
        <span className="inline-flex items-center gap-1 text-[10px] font-extrabold text-[#38003c] bg-purple-50/90 border border-purple-200/80 px-2 py-0.5 rounded-full shrink-0 shadow-2xs">
          <Sparkles className="w-2.5 h-2.5 text-[#38003c]" />
          {m.prediction.favorite_label}
        </span>
      ) : (
        <span className="text-[10px] font-semibold text-slate-500 bg-slate-100 border border-slate-200/60 px-2 py-0.5 rounded-full shrink-0">
          {Number(m.gameweek) === Number(currentGameweek) ? 'Mevcut Hafta' : `${m.gameweek}. Hafta`}
        </span>
      )}
    </div>

    {/* Current Gameweek: Unified Harmonious Prediction & Referee Card */}
    {Number(m.gameweek) === Number(currentGameweek) && m.prediction ? (
      <div className="bg-slate-50/80 border border-slate-200/80 rounded-xl p-2 transition-all">
        {/* 3 Unified Metric Columns with subtle dividers */}
        <div className="grid grid-cols-3 divide-x divide-slate-200/80 text-center py-0.5">
          <div className="px-1">
            <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider block leading-tight">
              KORNER
            </span>
            <span className="text-xs font-mono font-black text-slate-800">
              ~{m.prediction.expected_corners}
            </span>
          </div>
          <div className="px-1">
            <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider block leading-tight">
              KART (+3.5)
            </span>
            <span className="text-xs font-mono font-black text-slate-800">
              %{m.prediction.prob_over_3_5_cards}
            </span>
          </div>
          <div className="px-1">
            <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider block leading-tight">
              2.5 ÜST GOL
            </span>
            <span className="text-xs font-mono font-black text-slate-800">
              %{m.prediction.over_2_5_goals_pct}
            </span>
          </div>
        </div>

        {/* Subtle Referee sub-line */}
        <div className="mt-1.5 pt-1.5 border-t border-slate-200/60 flex items-center justify-between text-[10px] text-slate-600 px-1">
          <span className="truncate">
            <span className="text-slate-400">Hakem: </span>
            <strong className="text-slate-700 font-semibold truncate">
              {m.referee_name && m.referee_name !== 'Atanmadı' && m.referee_name !== 'Unknown' 
                ? m.referee_name 
                : (m.prediction?.referee_name && m.prediction.referee_name !== 'Unknown' ? m.prediction.referee_name : 'Atanmadı')}
            </strong>
          </span>
          {(m.ref_avg_cards || m.prediction?.expected_cards) && (
            <span className="text-slate-500 font-mono text-[9.5px] font-medium shrink-0">
              Ort. {m.ref_avg_cards || m.prediction?.expected_cards} kart
            </span>
          )}
        </div>
      </div>
    ) : (
      /* Future Gameweeks: Simple, clean schedule bar without prediction noise */
      <div className="bg-slate-50/60 border border-slate-100 rounded-xl px-2.5 py-1.5 flex items-center justify-between text-[10px] text-slate-500">
        <span className="truncate">
          <span className="text-slate-400">Hakem: </span>
          <span className="font-medium text-slate-600">
            {m.referee_name && m.referee_name !== 'Atanmadı' && m.referee_name !== 'Unknown' 
              ? m.referee_name 
              : 'Henüz Atanmadı'}
          </span>
        </span>
        <span className="text-[9.5px] font-medium text-slate-400 shrink-0">
          Fikstür Programı
        </span>
      </div>
    )}
  </div>
)}

                          </div>
  );
}
