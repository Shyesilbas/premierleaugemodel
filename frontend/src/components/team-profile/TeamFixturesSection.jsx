import { handleTeamBadgeError } from '../../utils/imageFallbacks';
import { useState } from 'react';
import { CalendarDays, CalendarX, List } from 'lucide-react';
import { getTeam } from '../../data/teams';
import MatchDetailModal from '../MatchDetailModal';
import Skeleton from '../common/Skeleton';
import EmptyState from '../common/EmptyState';
import TeamFixturesCalendar from './TeamFixturesCalendar';
import { RESULT_META } from './teamProfileUtils';
import { getCachedTeamData } from '../../utils/teamProfileCache';
import { parseKickoff } from '../../utils/dateFormatters';

const VIEW_STORAGE_KEY = 'team-fixtures-view';
const MONTHS_EN = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const MONTHS_TR = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık'];

// 'Sat 10 Oct 2026' -> Date(2026, 9, 10); null when the label has no recognisable date.
function parseDate(label) {
  const match = /(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})/.exec(label || '');
  const month = match ? MONTHS_EN.indexOf(match[2]) : -1;
  return month === -1 ? null : new Date(Number(match[3]), month, Number(match[1]));
}

// 'Sat 10 Oct 2026' -> '10 Ekim'; unknown shapes are returned unchanged.
function formatShortDate(label) {
  const match = /(\d{1,2})\s+([A-Za-z]{3})/.exec(label || '');
  const month = match ? MONTHS_EN.indexOf(match[2]) : -1;
  return month === -1 ? label : `${Number(match[1])} ${MONTHS_TR[month]}`;
}

function readStoredView() {
  try {
    return localStorage.getItem(VIEW_STORAGE_KEY) === 'calendar' ? 'calendar' : 'list';
  } catch {
    return 'list';
  }
}

function RedCards({ count }) {
  if (!count) return null;
  return (
    <span className="inline-flex shrink-0 items-center gap-1" title={`${count} kırmızı kart`} aria-label={`${count} kırmızı kart`}>
      <span aria-hidden="true" className="inline-block h-3 w-2 rounded-sm bg-status-error" />
      {count > 1 && <span className="text-xs text-status-error tabular-nums">x{count}</span>}
    </span>
  );
}

function ViewButton({ active, onClick, icon: Icon, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={`h-8 px-3 rounded text-sm font-medium inline-flex items-center gap-1.5 border transition-colors duration-150 ease-out cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-border-focus ${
        active
          ? 'bg-primary border-primary text-white'
          : 'bg-background-primary border-border text-text-secondary hover:text-text-primary hover:border-card-border-hover'
      }`}
    >
      <Icon className="w-4 h-4" strokeWidth={1.5} aria-hidden="true" />
      {children}
    </button>
  );
}

export default function TeamFixturesSection({
  activeTeamTab,
  profile,
  currentMeta,
  loading,
  selectedTeamId,
  onSelectMatch
}) {
  const [activeModalMatch, setActiveModalMatch] = useState(null);
  const [view, setView] = useState(readStoredView);
  if (activeTeamTab !== 'fixtures') return null;

  const matches = profile?.matches || [];

  const openMatch = (matchObj) => {
    if (onSelectMatch) onSelectMatch(matchObj);
    else setActiveModalMatch(matchObj);
  };

  const changeView = (next) => {
    setView(next);
    try {
      localStorage.setItem(VIEW_STORAGE_KEY, next);
    } catch {
      // The preference is a convenience only.
    }
  };

  const entries = matches.map(m => {
    const opponent = getTeam(m.opponent_id, m.opponent_name);
    const isPlayed = m.team_score !== null && m.team_score !== undefined;
    const kickoff = parseKickoff(m.kickoff_label);
    const homeTeam = m.is_home ? currentMeta : opponent;
    const awayTeam = m.is_home ? opponent : currentMeta;
    const homeScore = m.is_home ? m.team_score : m.opp_score;
    const awayScore = m.is_home ? m.opp_score : m.team_score;

    return {
      key: m.match_id,
      match: m,
      opponent,
      isHome: Boolean(m.is_home),
      isPlayed,
      result: m.result,
      scoreLabel: isPlayed ? `${m.team_score}-${m.opp_score}` : '',
      time: kickoff.time,
      date: parseDate(kickoff.date),
      dateLabel: formatShortDate(kickoff.date),
      homeTeam,
      awayTeam,
      homeScore,
      awayScore,
      modalMatchObj: {
        match_id: m.match_id,
        status: isPlayed ? 'COMPLETED' : (m.status || 'UNPLAYED'),
        gameweek: m.gameweek,
        kickoff_label: m.kickoff_label,
        home_id: homeTeam.id,
        home_name: homeTeam.name,
        home_score: homeScore,
        away_id: awayTeam.id,
        away_name: awayTeam.name,
        away_score: awayScore,
        ground_name: m.is_home ? currentMeta.stadium : opponent.stadium,
      },
    };
  });

  const redCardsForSide = (entry, side, team) => {
    const matchDetails = getCachedTeamData('match_detail', entry.match.match_id, 'all')?.data;
    const redCardStat = (matchDetails?.team_stats || [])
      .flatMap(category => category.items || [])
      .find(item => item.label === 'Kırmızı Kart');
    const statCount = Number(side === 'home' ? redCardStat?.home : redCardStat?.away);
    if (Number.isFinite(statCount) && statCount > 0) return statCount;
    return (matchDetails?.timeline || []).filter(event =>
      event.type === 'red_card' && (
        Number(event.team_id) === Number(team.id) ||
        (event.team_name && event.team_name.toLowerCase() === team.name.toLowerCase())
      )
    ).length;
  };

  return (
    <section aria-label="Fikstür ve sonuçlar" className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3 pb-4 border-b border-border">
        <div className="flex flex-col gap-1 min-w-0">
          <h3 className="text-lg font-semibold text-text-primary">Fikstür ve sonuçlar</h3>
          <p className="text-sm text-text-secondary tabular-nums">{currentMeta.name} sezon maçları · {matches.length} maç</p>
        </div>
        <div className="flex items-center gap-2" role="group" aria-label="Görünüm">
          <ViewButton active={view === 'list'} onClick={() => changeView('list')} icon={List}>Liste</ViewButton>
          <ViewButton active={view === 'calendar'} onClick={() => changeView('calendar')} icon={CalendarDays}>Takvim</ViewButton>
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col gap-2" aria-busy="true" aria-label="Yükleniyor">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-11 w-full" />
          ))}
        </div>
      ) : matches.length === 0 ? (
        <EmptyState icon={CalendarX}>Bu sezon için kayıtlı maç bulunamadı.</EmptyState>
      ) : view === 'calendar' ? (
        <TeamFixturesCalendar entries={entries} onOpen={openMatch} />
      ) : (
        <div className="overflow-x-auto bg-background-primary border border-border rounded">
          <table className="w-full text-left text-sm border-collapse">
            <thead>
              <tr className="bg-background-tertiary border-b border-border text-text-secondary">
                <th scope="col" className="py-2 px-3 font-medium">Tarih</th>
                <th scope="col" className="py-2 px-3 font-medium text-center border-l border-border">Durum</th>
                <th scope="col" className="w-full py-2 px-3 font-medium border-l border-border">Karşılaşma</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-light">
              {entries.map(entry => {
                const { homeTeam, awayTeam, isPlayed } = entry;
                const result = isPlayed ? RESULT_META[entry.result] || RESULT_META.L : null;

                return (
                  <tr
                    key={entry.key}
                    tabIndex={0}
                    onClick={() => openMatch(entry.modalMatchObj)}
                    onKeyDown={event => {
                      if (event.key === 'Enter') openMatch(entry.modalMatchObj);
                    }}
                    className="cursor-pointer transition-colors duration-150 ease-out hover:bg-background-tertiary focus:outline-none focus-visible:bg-background-tertiary"
                  >
                    <td className="py-2.5 px-3 whitespace-nowrap">
                      <span className="text-text-primary tabular-nums">{entry.dateLabel}</span>
                      {entry.time && <span className="ml-2 text-xs text-text-tertiary tabular-nums">{entry.time}</span>}
                    </td>

                    <td className="py-2.5 px-3 text-center border-l border-border-light">
                      {result ? (
                        <span
                          title={result.title}
                          aria-label={result.title}
                          className={`inline-flex w-6 h-6 items-center justify-center rounded-sm text-xs font-semibold ${result.className}`}
                        >
                          {result.label}
                        </span>
                      ) : (
                        <span className="text-text-muted">—</span>
                      )}
                    </td>

                    <td className="py-2.5 px-3 border-l border-border-light">
                      <div className="flex items-center gap-3">
                        <div className="w-36 flex items-center justify-end gap-2 min-w-0 text-right">
                          <span className={`truncate ${homeTeam.id === selectedTeamId ? 'font-semibold text-text-primary' : 'text-text-secondary'}`}>
                            {homeTeam.short || homeTeam.name}
                          </span>
                          <RedCards count={isPlayed ? redCardsForSide(entry, 'home', homeTeam) : 0} />
                          <img
                            src={homeTeam.badge}
                            alt=""
                            className="w-5 h-5 object-contain shrink-0"
                            onError={handleTeamBadgeError}
                          />
                        </div>

                        <span className={`w-12 shrink-0 text-center tabular-nums ${isPlayed ? 'font-semibold text-text-primary' : 'text-text-tertiary'}`}>
                          {isPlayed ? `${entry.homeScore} - ${entry.awayScore}` : 'vs'}
                        </span>

                        <div className="w-36 flex items-center gap-2 min-w-0">
                          <img
                            src={awayTeam.badge}
                            alt=""
                            className="w-5 h-5 object-contain shrink-0"
                            onError={handleTeamBadgeError}
                          />
                          <span className={`truncate ${awayTeam.id === selectedTeamId ? 'font-semibold text-text-primary' : 'text-text-secondary'}`}>
                            {awayTeam.short || awayTeam.name}
                          </span>
                          <RedCards count={isPlayed ? redCardsForSide(entry, 'away', awayTeam) : 0} />
                        </div>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {activeModalMatch && (
        <MatchDetailModal match={activeModalMatch} onClose={() => setActiveModalMatch(null)} />
      )}
    </section>
  );
}
