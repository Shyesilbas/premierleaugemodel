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
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex flex-col gap-3 border-b border-slate-100 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-5">
        <div className="flex items-center gap-2">
          <Calendar className="h-4 w-4 text-slate-500" />
          <div>
            <h3 className="text-sm font-bold text-slate-900">Maç geçmişi</h3>
            <p className="text-xs text-slate-500">{playedMatchCount} oynanmış maç · {season === 'all' ? 'Tüm sezonlar' : formatSeasonLabel(season)}</p>
          </div>
        </div>
        {weeks.length > 0 && (
          <label className="flex items-center gap-2 text-xs font-medium text-slate-500">
            Hafta
            <select value={selectedWeek} onChange={event => onWeekChange(event.target.value)} className="min-w-36 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-800 outline-none focus:border-slate-400">
              <option value="all">Tüm haftalar</option>
              {weeks.map(week => <option key={week} value={week}>Hafta {week}</option>)}
            </select>
          </label>
        )}
      </div>

      {loading ? (
        <div className="py-16 text-center">
          <div className="w-7 h-7 border-3 border-[#38003c] border-t-transparent rounded-full animate-spin mx-auto mb-2" />
          <p className="text-xs font-bold text-slate-600">Oyuncu maç kayıtları yükleniyor...</p>
        </div>
      ) : !playedMatchCount ? (
        <div className="py-12 text-center text-xs text-slate-500 font-medium">Seçilen sezonda oyuncunun süre aldığı maç bulunamadı.</div>
      ) : matches.length === 0 ? (
        <div className="py-12 text-center text-xs text-slate-500 font-medium bg-slate-50 border border-slate-200 rounded-xl">
          Bu haftada ({selectedWeek}. Hafta) oyuncunun süre aldığı karşılaşma kaydı bulunmuyor.
        </div>
      ) : (
        <div className="divide-y divide-slate-100">
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
              <button key={match.match_id} onClick={() => onSelectMatch(modalMatch)} className="group flex w-full flex-col gap-2.5 px-4 py-3 text-left transition-colors hover:bg-slate-50 sm:flex-row sm:items-center sm:gap-3 sm:px-5">
                <div className="flex items-center gap-2.5 shrink-0">
                  <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg font-mono text-xs font-black shadow-xs transition-transform group-hover:scale-105 ${ratingClass(match.rating)}`} title={match.rating != null ? `Maç Performans Reytingi: ${match.rating.toFixed(1)} / 10` : '10 dakikadan az oynandı veya belirleyici aksiyon olmadı (Değerlendirilmedi)'}>
                    {match.rating != null ? match.rating.toFixed(1) : '—'}
                  </div>
                  <div className="flex items-center justify-between gap-2 text-[11px] text-slate-500 sm:w-36 sm:shrink-0 sm:flex-col sm:items-start sm:gap-1">
                    <span className="inline-flex items-center gap-1.5 font-semibold text-slate-700"><Clock className="hidden h-3.5 w-3.5 text-slate-400 sm:block" />{kickoff.date}</span>
                    <span className="flex items-center gap-2">
                      {season === 'all' && <span>{formatSeasonLabel(match.season)}</span>}
                      <span className="font-mono">H{Math.round(Number(match.gameweek) || 1)}</span>
                      <span>{match.is_home ? 'İç' : 'Dep'}</span>
                    </span>
                  </div>
                </div>

                <div className="flex min-w-0 flex-1 items-center justify-center gap-1.5 sm:gap-3">
                  <div className="flex min-w-0 flex-1 items-center justify-end gap-1.5 text-right">
                    <span className={`truncate text-xs ${match.is_home ? 'font-bold text-slate-950' : 'font-medium text-slate-600'}`}>{home.short || home.name}</span>
                    <img src={home.badge} alt={home.name} className="h-5 w-5 shrink-0 object-contain" onError={handleTeamBadgeError} />
                  </div>
                  <span className="min-w-[58px] shrink-0 text-center font-mono text-xs font-black text-slate-900">{played ? `${homeScore} - ${awayScore}` : kickoff.time || 'vs'}</span>
                  <div className="flex min-w-0 flex-1 items-center gap-1.5">
                    <img src={away.badge} alt={away.name} className="h-5 w-5 shrink-0 object-contain" onError={handleTeamBadgeError} />
                    <span className={`truncate text-xs ${!match.is_home ? 'font-bold text-slate-950' : 'font-medium text-slate-600'}`}>{away.short || away.name}</span>
                  </div>
                </div>

                <div className="flex items-center justify-between gap-3 border-t border-slate-100 pt-2 text-[11px] text-slate-600 sm:w-56 sm:shrink-0 sm:justify-end sm:border-0 sm:pt-0">
                  <span className="whitespace-nowrap"><strong className="font-semibold text-slate-800">{match.minutes_played || 0}'</strong> · {match.started ? 'İlk 11' : 'Yedek'}</span>
                  <span className="whitespace-nowrap">Gol <strong className="text-slate-900">{match.goals || 0}</strong><span className="mx-1.5 text-slate-300">|</span>Asist <strong className="text-slate-900">{match.assists || 0}</strong></span>
                  <ChevronRight className="hidden h-3.5 w-3.5 text-slate-300 transition group-hover:translate-x-0.5 group-hover:text-slate-600 sm:block" />
                </div>
              </button>
            );
          })}
        </div>
      )}
    </section>
  );
}
