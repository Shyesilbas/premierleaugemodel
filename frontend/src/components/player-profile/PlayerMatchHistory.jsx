import { handleTeamBadgeError } from '../../utils/imageFallbacks';
import { formatSeasonLabel } from '../../utils/dateFormatters';
import { Calendar, ChevronRight, Clock } from 'lucide-react';
import { getTeam } from '../../data/teams';
import { parseKickoff } from '../../utils/dateFormatters';

function ratingClass(rating) {
  if (rating == null) return 'bg-slate-100 text-slate-400 border border-slate-200';
  if (rating >= 8) return 'bg-emerald-600 text-white shadow-emerald-500/20';
  if (rating >= 7) return 'bg-emerald-100 text-emerald-800 border border-emerald-200/60';
  if (rating >= 6) return 'bg-sky-100 text-sky-800 border border-sky-200/60';
  if (rating >= 5) return 'bg-amber-100 text-amber-800 border border-amber-200/60';
  return 'bg-rose-100 text-rose-800 border border-rose-200/60';
}

function toMatchModalData(match) {
  const opponent = getTeam(match.opponent_id, match.opponent_name);
  const team = getTeam(match.team_id, match.team_name);
  const home = match.is_home ? team : opponent;
  const away = match.is_home ? opponent : team;
  return {
    match_id: match.match_id,
    status: match.team_score !== null && match.team_score !== undefined ? 'COMPLETED' : 'UNPLAYED',
    gameweek: match.gameweek,
    kickoff_label: match.kickoff,
    home_id: home.id,
    home_name: home.name,
    home_score: match.is_home ? match.team_score : match.opp_score,
    away_id: away.id,
    away_name: away.name,
    away_score: match.is_home ? match.opp_score : match.team_score,
    ground_name: 'Premier League',
  };
}

export default function PlayerMatchHistory({
  matches,
  playedMatchCount,
  weeks,
  selectedWeek,
  onWeekChange,
  loading,
  season,
  onSelectMatch,
}) {
  return (
    <section className="bg-background-primary border border-border rounded">
      <div className="flex flex-col gap-3 border-b border-border-light p-4 sm:flex-row sm:items-center sm:justify-between sm:px-5">
        <div className="flex items-center gap-2">
          <Calendar className="h-4 w-4 text-text-secondary" />
          <div>
            <h2 className="text-base font-semibold text-text-primary">Maç Geçmişi</h2>
            <p className="text-xs text-text-secondary">
              {playedMatchCount} oynanmış maç · {season === 'all' ? 'Tüm sezonlar' : formatSeasonLabel(season)}
            </p>
          </div>
        </div>
        {weeks.length > 0 && (
          <div className="flex items-center gap-2">
            <label htmlFor="gameweek-filter-select" className="text-xs font-medium text-text-secondary">
              Hafta:
            </label>
            <select
              id="gameweek-filter-select"
              value={selectedWeek}
              onChange={event => onWeekChange(event.target.value)}
              className="min-w-36 h-9 rounded border border-border bg-background-primary px-3 text-sm font-medium text-text-primary outline-none focus:border-border-focus transition-colors"
            >
              <option value="all">Tüm haftalar</option>
              {weeks.map(week => (
                <option key={week} value={week}>Hafta {week}</option>
              ))}
            </select>
          </div>
        )}
      </div>

      {loading ? (
        <div className="py-16 text-center space-y-2">
          <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-xs font-medium text-text-secondary">Maç kayıtları yükleniyor...</p>
        </div>
      ) : !playedMatchCount ? (
        <div className="py-12 text-center text-xs text-text-secondary font-medium">
          Seçilen sezonda oyuncunun süre aldığı maç bulunamadı.
        </div>
      ) : matches.length === 0 ? (
        <div className="py-12 text-center text-xs text-text-secondary font-medium m-4 bg-background-secondary border border-border rounded">
          Bu haftada ({selectedWeek}. Hafta) oyuncunun süre aldığı karşılaşma kaydı bulunmuyor.
        </div>
      ) : (
        <div className="divide-y divide-border-light">
          {matches.map(match => {
            const modalMatch = toMatchModalData(match);
            const opponent = getTeam(match.opponent_id, match.opponent_name);
            const team = getTeam(match.team_id, match.team_name);
            const home = match.is_home ? team : opponent;
            const away = match.is_home ? opponent : team;
            const played = match.team_score !== null && match.team_score !== undefined;
            const kickoff = parseKickoff(match.kickoff);
            const homeScore = match.is_home ? match.team_score : match.opp_score;
            const awayScore = match.is_home ? match.opp_score : match.team_score;

            return (
              <button
                key={match.match_id}
                type="button"
                onClick={() => onSelectMatch(modalMatch)}
                className="group flex w-full flex-col gap-2.5 px-4 py-3 text-left transition-colors hover:bg-background-secondary sm:flex-row sm:items-center sm:gap-4 sm:px-5 cursor-pointer"
              >
                <div className="flex items-center gap-3 shrink-0">
                  <div
                    className={`flex h-8 w-8 shrink-0 items-center justify-center rounded border font-mono text-xs tabular-nums ${ratingClass(match.rating)}`}
                    title={match.rating != null ? `Maç Performans Reytingi: ${match.rating.toFixed(1)} / 10` : 'Değerlendirilmedi'}
                  >
                    {match.rating != null ? match.rating.toFixed(1) : '—'}
                  </div>
                  <div className="flex items-center justify-between gap-2 text-xs text-text-secondary sm:w-36 sm:shrink-0 sm:flex-col sm:items-start sm:gap-0.5">
                    <span className="inline-flex items-center gap-1.5 font-medium text-text-primary">
                      <Clock className="hidden h-3.5 w-3.5 text-text-tertiary sm:block" />
                      {kickoff.date}
                    </span>
                    <span className="flex items-center gap-2 text-text-tertiary text-xs">
                      {season === 'all' && <span>{formatSeasonLabel(match.season)}</span>}
                      <span className="font-mono">H{Math.round(Number(match.gameweek) || 1)}</span>
                      <span>{match.is_home ? 'İç Saha' : 'Deplasman'}</span>
                    </span>
                  </div>
                </div>

                <div className="flex min-w-0 flex-1 items-center justify-center gap-2 sm:gap-3">
                  <div className="flex min-w-0 flex-1 items-center justify-end gap-1.5 text-right">
                    <span className={`truncate text-xs ${match.is_home ? 'font-semibold text-text-primary' : 'font-normal text-text-secondary'}`}>
                      {home.short || home.name}
                    </span>
                    <img src={home.badge} alt={home.name} className="h-5 w-5 shrink-0 object-contain" onError={handleTeamBadgeError} />
                  </div>
                  <span className="min-w-[58px] shrink-0 text-center font-mono text-xs font-semibold tabular-nums text-text-primary">
                    {played ? `${homeScore} - ${awayScore}` : kickoff.time || 'vs'}
                  </span>
                  <div className="flex min-w-0 flex-1 items-center gap-1.5">
                    <img src={away.badge} alt={away.name} className="h-5 w-5 shrink-0 object-contain" onError={handleTeamBadgeError} />
                    <span className={`truncate text-xs ${!match.is_home ? 'font-semibold text-text-primary' : 'font-normal text-text-secondary'}`}>
                      {away.short || away.name}
                    </span>
                  </div>
                </div>

                <div className="flex items-center justify-between gap-3 border-t border-border-light pt-2 text-xs text-text-secondary sm:w-56 sm:shrink-0 sm:justify-end sm:border-0 sm:pt-0">
                  <span className="whitespace-nowrap">
                    <strong className="font-medium text-text-primary">{match.minutes_played || 0}'</strong> · {match.started ? 'İlk 11' : 'Yedek'}
                  </span>
                  <span className="whitespace-nowrap tabular-nums">
                    Gol <strong className="font-medium text-text-primary">{match.goals || 0}</strong>
                    <span className="mx-1.5 text-text-muted">|</span>
                    Asist <strong className="font-medium text-text-primary">{match.assists || 0}</strong>
                  </span>
                  <ChevronRight className="hidden h-4 w-4 text-text-tertiary transition-transform group-hover:translate-x-0.5 sm:block" />
                </div>
              </button>
            );
          })}
        </div>
      )}
    </section>
  );
}
