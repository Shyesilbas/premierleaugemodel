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
      className="bg-background-primary border border-border hover:border-card-border-hover rounded p-4 transition-colors cursor-pointer group flex flex-col justify-between gap-3 relative"
    >
      {/* Top Card Bar: Kickoff time & Ground */}
      <div className="flex items-center justify-between text-xs text-text-secondary pb-2 border-b border-border-light">
        <div className="flex items-center gap-1.5 font-medium truncate max-w-[200px]">
          <Clock className="w-3.5 h-3.5 text-text-muted shrink-0" />
          <span className="truncate tabular-nums">{m.time_label || m.kickoff_label}</span>
        </div>

        <span className="text-xs font-medium text-text-primary flex items-center gap-1 bg-background-tertiary px-2 py-0.5 rounded-sm border border-border">
          {isCompleted 
            ? 'Maç Sayfası' 
            : (Number(m.gameweek) === Number(currentGameweek) ? 'Model Analizi' : 'Maç Detayı')} 
          <ChevronRight className="w-3.5 h-3.5 text-text-muted" />
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
            className="font-medium text-xs text-text-primary hover:text-text-secondary hover:underline transition-colors truncate text-left"
            aria-label={`${home.name} takım profiline git`}
          >
            {home.name}
          </button>
        </div>

        {/* Center: Score or Kickoff Time */}
        <div className="shrink-0 px-3 py-1 rounded bg-background-tertiary border border-border font-mono font-semibold text-sm text-text-primary text-center min-w-[64px] tabular-nums">
          {isCompleted ? (
            <span>{m.home_score} - {m.away_score}</span>
          ) : (
            <span className="text-xs font-medium text-text-secondary">VS</span>
          )}
        </div>

        {/* Away Team */}
        <div className="flex items-center gap-2.5 flex-1 min-w-0 justify-end text-right">
          <button
            type="button"
            onClick={(event) => { event.stopPropagation(); onSelectTeam?.(away.id); }}
            className="font-medium text-xs text-text-primary hover:text-text-secondary hover:underline transition-colors truncate text-right"
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
        <div className="grid grid-cols-2 gap-2 text-xs text-text-secondary">
          <span className="truncate" title={homeManager ? `Teknik Direktör: ${homeManager}` : undefined}>
            {homeManager ? <><span className="text-text-muted">TD:</span> <span className="font-medium text-text-primary">{homeManager}</span></> : ''}
          </span>
          <span className="truncate text-right" title={awayManager ? `Teknik Direktör: ${awayManager}` : undefined}>
            {awayManager ? <><span className="text-text-muted">TD:</span> <span className="font-medium text-text-primary">{awayManager}</span></> : ''}
          </span>
        </div>
      )}

      {/* Recent form */}
      <div className="flex items-center justify-between gap-2 text-xs text-text-muted">
        <div className="flex items-center gap-1" aria-label={`${home.name} son 5 maç formu`}>
          <TeamForm results={homeForm} />
        </div>
        <span className="shrink-0 font-medium tracking-wide text-xs">SON 5</span>
        <div className="flex items-center gap-1" aria-label={`${away.name} son 5 maç formu`}>
          <TeamForm results={awayForm} />
        </div>
      </div>

      {/* Bottom Bar: Completed Micro-stats OR Ground/Status */}
      {isCompleted ? (
        <div className="pt-2 border-t border-border-light space-y-2">
          <div className="flex items-center justify-between text-xs text-text-secondary">
            <span className="flex items-center gap-1 truncate">
              <span className="text-text-muted">Hakem:</span>
              <strong className="text-text-primary font-medium truncate">{m.referee_name || 'Bilinmiyor'}</strong>
            </span>
            {m.total_yellow_cards !== null && m.total_yellow_cards !== undefined ? (
              <div className="flex items-center gap-1 shrink-0 font-mono text-xs tabular-nums">
                <span className="px-1.5 py-0.5 rounded-sm bg-background-tertiary border border-border text-status-warning font-medium">
                  {m.total_yellow_cards} S
                </span>
                {m.total_red_cards > 0 && (
                  <span className="px-1.5 py-0.5 rounded-sm bg-background-tertiary border border-border text-status-error font-medium">
                    {m.total_red_cards} K
                  </span>
                )}
              </div>
            ) : (
              <span className="text-xs text-text-muted font-mono tabular-nums">
                {m.ref_avg_cards ? `Ort. ${m.ref_avg_cards} Kart` : ''}
              </span>
            )}
          </div>

          <div className="grid grid-cols-5 gap-1.5 text-xs font-mono text-center tabular-nums">
            <div className="bg-background-tertiary py-1 px-1 rounded-sm border border-border-light">
              <span className="text-xs text-text-muted font-sans block">Korner</span>
              <span className="text-text-primary font-medium">{m.home_won_corners ?? '-'} - {m.away_won_corners ?? '-'}</span>
            </div>
            <div className="bg-background-tertiary py-1 px-1 rounded-sm border border-border-light">
              <span className="text-xs text-text-muted font-sans block">Taç</span>
              <span className="text-text-primary font-medium">{m.home_total_throws ?? '-'} - {m.away_total_throws ?? '-'}</span>
            </div>
            <div className="bg-background-tertiary py-1 px-1 rounded-sm border border-border-light">
              <span className="text-xs text-text-muted font-sans block">Şut</span>
              <span className="text-text-primary font-medium">{m.home_total_shots ?? '-'} - {m.away_total_shots ?? '-'}</span>
            </div>
            <div className="bg-background-tertiary py-1 px-1 rounded-sm border border-border-light">
              <span className="text-xs text-text-muted font-sans block">Kurtarış</span>
              <span className="text-text-primary font-medium">{m.total_saves ?? '-'}</span>
            </div>
            <div className="bg-background-tertiary py-1 px-1 rounded-sm border border-border-light">
              <span className="text-xs text-text-muted font-sans block">xG</span>
              {(m.home_xg != null || m.away_xg != null) ? (
                <span className="text-text-primary font-medium">
                  {m.home_xg != null ? Number(m.home_xg).toFixed(1) : '-'} - {m.away_xg != null ? Number(m.away_xg).toFixed(1) : '-'}
                </span>
              ) : (
                <span className="text-text-muted italic text-xs block">
                  -
                </span>
              )}
            </div>
          </div>
        </div>
      ) : (
        <div className="pt-2 border-t border-border-light space-y-2">
          {/* Stadium & Favorite / Gameweek Meta Header */}
          <div className="flex items-center justify-between text-xs text-text-secondary gap-2 px-0.5">
            <span className="flex items-center gap-1.5 truncate text-text-muted font-medium">
              <MapPin className="w-3.5 h-3.5 text-text-muted shrink-0" />
              <span className="truncate">{m.ground_name || 'Premier League Stadı'}</span>
            </span>
            {Number(m.gameweek) === Number(currentGameweek) && m.prediction?.favorite_label ? (
              <span className="inline-flex items-center gap-1 text-xs font-medium text-text-primary bg-background-tertiary border border-border px-2 py-0.5 rounded-sm shrink-0">
                <Sparkles className="w-3 h-3 text-text-primary" />
                {m.prediction.favorite_label}
              </span>
            ) : (
              <span className="text-xs font-medium text-text-secondary bg-background-tertiary border border-border px-2 py-0.5 rounded-sm shrink-0">
                {Number(m.gameweek) === Number(currentGameweek) ? 'Mevcut Hafta' : `${m.gameweek}. Hafta`}
              </span>
            )}
          </div>

          {/* Current Gameweek: Prediction & Referee Card */}
          {Number(m.gameweek) === Number(currentGameweek) && m.prediction ? (
            <div className="bg-background-tertiary border border-border rounded p-2">
              <div className="grid grid-cols-3 divide-x divide-border text-center py-0.5">
                <div className="px-1">
                  <span className="text-xs font-medium text-text-muted uppercase tracking-wider block">
                    Korner
                  </span>
                  <span className="text-xs font-mono font-semibold text-text-primary tabular-nums">
                    ~{m.prediction.expected_corners}
                  </span>
                </div>
                <div className="px-1">
                  <span className="text-xs font-medium text-text-muted uppercase tracking-wider block">
                    Kart (+3.5)
                  </span>
                  <span className="text-xs font-mono font-semibold text-text-primary tabular-nums">
                    %{m.prediction.prob_over_3_5_cards}
                  </span>
                </div>
                <div className="px-1">
                  <span className="text-xs font-medium text-text-muted uppercase tracking-wider block">
                    2.5 Üst Gol
                  </span>
                  <span className="text-xs font-mono font-semibold text-text-primary tabular-nums">
                    %{m.prediction.over_2_5_goals_pct}
                  </span>
                </div>
              </div>

              <div className="mt-1.5 pt-1.5 border-t border-border flex items-center justify-between text-xs text-text-secondary px-1">
                <span className="truncate">
                  <span className="text-text-muted">Hakem: </span>
                  <strong className="text-text-primary font-medium truncate">
                    {m.referee_name && m.referee_name !== 'Atanmadı' && m.referee_name !== 'Unknown' 
                      ? m.referee_name 
                      : (m.prediction?.referee_name && m.prediction.referee_name !== 'Unknown' ? m.prediction.referee_name : 'Atanmadı')}
                  </strong>
                </span>
                {(m.ref_avg_cards || m.prediction?.expected_cards) && (
                  <span className="text-text-muted font-mono text-xs font-medium shrink-0 tabular-nums">
                    Ort. {m.ref_avg_cards || m.prediction?.expected_cards} kart
                  </span>
                )}
              </div>
            </div>
          ) : (
            <div className="bg-background-tertiary border border-border rounded px-2.5 py-1.5 flex items-center justify-between text-xs text-text-secondary">
              <span className="truncate">
                <span className="text-text-muted">Hakem: </span>
                <span className="font-medium text-text-primary">
                  {m.referee_name && m.referee_name !== 'Atanmadı' && m.referee_name !== 'Unknown' 
                    ? m.referee_name 
                    : 'Henüz Atanmadı'}
                </span>
              </span>
              <span className="text-xs text-text-muted shrink-0">
                Fikstür Programı
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
