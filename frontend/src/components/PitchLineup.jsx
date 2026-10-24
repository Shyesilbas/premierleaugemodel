import React, { useMemo } from 'react';
import { ArrowDown, ArrowUp } from 'lucide-react';
import PlayerAvatar from './PlayerAvatar';
import { BallIcon, RedCardIcon, YellowCardIcon } from './match-detail/eventIcons';

const POSITION_ORDER = { G: 0, GK: 0, D: 1, DEF: 1, M: 2, MID: 2, F: 3, FWD: 3 };
const POSITION_LABEL = { G: 'KL', GK: 'KL', D: 'DF', DEF: 'DF', M: 'OS', MID: 'OS', F: 'FV', FWD: 'FV' };

const ratingClass = (r) =>
  r >= 7.5 ? 'bg-emerald-500 text-white'
    : r >= 6.5 ? 'bg-sky-500 text-white'
    : r >= 5.5 ? 'bg-amber-500 text-white'
    : 'bg-rose-500 text-white';

// Resolve rows (GK first) from backend formation_matrix, falling back to the formation label
function getTeamRows(lineup) {
  if (!lineup?.starters?.length) return [];

  const startersMap = new Map(lineup.starters.map(p => [p.id, p]));
  if (Array.isArray(lineup.formation_matrix) && lineup.formation_matrix.length > 0) {
    const rows = lineup.formation_matrix
      .map(ids => ids.map(id => startersMap.get(id)).filter(Boolean))
      .filter(r => r.length > 0);
    if (rows.reduce((acc, r) => acc + r.length, 0) >= 10) return rows;
  }

  const parts = String(lineup.formation || '4-3-3').split('-').map(n => parseInt(n, 10)).filter(n => !isNaN(n));
  const sorted = [...lineup.starters].sort((a, b) => {
    const oa = POSITION_ORDER[a.position] ?? 2;
    const ob = POSITION_ORDER[b.position] ?? 2;
    return oa !== ob ? oa - ob : (a.shirt || 99) - (b.shirt || 99);
  });

  const rows = [];
  let cur = 0;
  for (const count of [1, ...parts]) {
    if (cur >= sorted.length) break;
    rows.push(sorted.slice(cur, cur + count));
    cur += count;
  }
  if (cur < sorted.length) {
    if (rows.length > 0) rows[rows.length - 1] = rows[rows.length - 1].concat(sorted.slice(cur));
    else rows.push(sorted.slice(cur));
  }
  return rows;
}

// FIFA-standard 105x68 pitch markings, drawn horizontally
function PitchMarkings() {
  return (
    <g fill="none" stroke="rgba(255,255,255,0.45)" strokeWidth="0.35">
      <rect x="0" y="0" width="105" height="68" />
      <line x1="52.5" y1="0" x2="52.5" y2="68" />
      <circle cx="52.5" cy="34" r="9.15" />
      <circle cx="52.5" cy="34" r="0.5" fill="rgba(255,255,255,0.6)" />
      <rect x="0" y="13.84" width="16.5" height="40.32" />
      <rect x="0" y="24.84" width="5.5" height="18.32" />
      <circle cx="11" cy="34" r="0.4" fill="rgba(255,255,255,0.6)" />
      <path d="M16.5 26.69 A9.15 9.15 0 0 1 16.5 41.31" />
      <rect x="88.5" y="13.84" width="16.5" height="40.32" />
      <rect x="99.5" y="24.84" width="5.5" height="18.32" />
      <circle cx="94" cy="34" r="0.4" fill="rgba(255,255,255,0.6)" />
      <path d="M88.5 26.69 A9.15 9.15 0 0 0 88.5 41.31" />
      <rect x="-1.2" y="30.34" width="1.2" height="7.32" />
      <rect x="105" y="30.34" width="1.2" height="7.32" />
      <path d="M0 1 A1 1 0 0 0 1 0 M104 0 A1 1 0 0 0 105 1 M0 67 A1 1 0 0 1 1 68 M104 68 A1 1 0 0 1 105 67" />
    </g>
  );
}

function TeamHeader({ team, lineup, label, align = 'left' }) {
  const isRight = align === 'right';
  const ratingLabel = lineup?.starters?.[0]?.is_match_rating ? 'Maç notu' : '11 formu';
  return (
    <div className={`flex items-center gap-3 min-w-0 ${isRight ? 'flex-row-reverse text-right' : ''}`}>
      <img src={team?.badge} alt="" className="w-9 h-9 sm:w-10 sm:h-10 object-contain shrink-0 drop-shadow" />
      <div className="min-w-0">
        <div className="text-sm sm:text-base font-semibold leading-tight truncate">{team?.name}</div>
        <div className={`flex items-center gap-1.5 mt-0.5 text-xs text-white/60 font-semibold ${isRight ? 'justify-end' : ''}`}>
          <span className="uppercase tracking-wider">{label}</span>
          {lineup?.formation && (
            <span className="font-mono font-semibold text-status-success bg-background-primary/10 rounded-md px-1.5 py-px">{lineup.formation}</span>
          )}
          {lineup?.team_ratings?.overall != null && (
            <span className="hidden sm:inline" title={ratingLabel}>
              · {ratingLabel} <strong className="font-mono text-white">{Number(lineup.team_ratings.overall).toFixed(1)}</strong>
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

export default function PitchLineup({
  homeLineup,
  awayLineup,
  homeTeam,
  awayTeam,
  playerStats = { home: [], away: [] },
  onPlayerClick,
}) {
  const getStats = (pid, side) => (playerStats?.[side] || []).find(p => p.id === pid) || {};

  const homeRows = useMemo(() => getTeamRows(homeLineup), [homeLineup]);
  const awayRows = useMemo(() => getTeamRows(awayLineup), [awayLineup]);

  const renderPlayerNode = (player, side) => {
    const stats = getStats(player.id, side);
    const goals = stats.goals || 0;
    const assists = stats.assists || 0;
    const rating = stats.rating ?? player.rating;
    const isMatchRating = stats.rating != null || player.is_match_rating;
    // shortcut: subbed-off minute is inferred from minutes played (no sub event join), off by stoppage time
    const subOffMinute = stats.minutes > 0 && stats.minutes < 90 && !stats.red_cards ? stats.minutes : null;
    const nameParts = (player.name || '').trim().split(/\s+/);
    const shortName = nameParts.length > 1 ? nameParts[nameParts.length - 1] : player.name;

    return (
      <button
        type="button"
        key={player.id || player.shirt}
        onClick={(e) => onPlayerClick && onPlayerClick(player, side, e)}
        title={`${player.name} (#${player.shirt ?? '-'}) · Detaylar için tıklayın`}
        className="group relative flex flex-col items-center w-16 sm:w-20 rounded focus:outline-none focus-visible:ring-2 focus-visible:ring-[#00ff87]"
      >
        <div className="relative transition-transform duration-200 group-hover:-translate-y-0.5">
          <PlayerAvatar
            photoUrl={player.photo_url}
            name={player.name}
            shirt={player.shirt}
            fallback="initials"
            size="w-9 h-9 sm:w-12 sm:h-12 text-xs"
            className="!border-0 ring-2 ring-white/90 shadow-lg shadow-black/30 group-hover:ring-primary transition-all"
          />

          {rating != null && (
            <span
              className={`absolute -top-1.5 -right-3 min-w-[26px] text-center px-1 rounded-md font-mono font-semibold text-xs leading-4 shadow-md ring-1 ring-black/10 ${ratingClass(rating)}`}
              title={isMatchRating
                ? `Maç Performans Notu: ${Number(rating).toFixed(1)}/10`
                : `5 Maçlık Form Puanı: ${Number(rating).toFixed(1)}/10 · ${player.form_label || 'Normal'} · Kart Riski: ${player.cards_risk ?? '-'}/10`}
            >
              {Number(rating).toFixed(1)}
            </span>
          )}

          {player.captain && (
            <span className="absolute -top-1 -left-1.5 w-4 h-4 rounded-full bg-amber-400 text-slate-950 font-semibold text-xs flex items-center justify-center ring-2 ring-white shadow" title="Kaptan">
              C
            </span>
          )}

          {(goals > 0 || assists > 0 || stats.yellow_cards > 0 || stats.red_cards > 0 || subOffMinute || (!isMatchRating && player.cards_risk >= 7)) && (
            <div className="absolute -bottom-2 left-1/2 -translate-x-1/2 flex items-center gap-0.5 whitespace-nowrap">
              {Array.from({ length: goals }).map((_, i) => (
                <span key={`g${i}`} className="w-4 h-4 rounded-full bg-background-primary text-text-primary flex items-center justify-center shadow" title="Gol">
                  <BallIcon className="w-3 h-3" />
                </span>
              ))}
              {assists > 0 && (
                <span className="h-4 px-1 rounded-full bg-primary text-white text-xs font-semibold flex items-center shadow ring-1 ring-white/60" title={`${assists} Asist`}>
                  A{assists > 1 ? assists : ''}
                </span>
              )}
              {stats.red_cards > 0 ? <RedCardIcon className="w-2.5 h-3.5 ring-1 ring-white" />
                : stats.yellow_cards > 0 ? <YellowCardIcon className="w-2.5 h-3.5 ring-1 ring-white" />
                : (!isMatchRating && player.cards_risk >= 7) ? (
                  <span className="w-2.5 h-3.5 rounded-xs border border-dashed border-amber-300 bg-amber-400/40" title={`Yüksek Kart Riski: ${player.cards_risk}/10`} />
                ) : null}
              {subOffMinute && (
                <span className="h-4 pl-0.5 pr-1 rounded-full bg-background-primary text-rose-600 text-xs font-semibold font-mono flex items-center shadow" title={`${subOffMinute}' oyundan çıktı`}>
                  <ArrowDown className="w-2.5 h-2.5" strokeWidth={3} />{subOffMinute}'
                </span>
              )}
            </div>
          )}
        </div>

        <span className="mt-2.5 max-w-full truncate text-xs font-bold text-white [text-shadow:0_1px_2px_rgba(0,0,0,0.8)] group-hover:text-status-success transition-colors">
          <span className="font-mono text-white/60 mr-0.5">{player.shirt}</span>{shortName}
        </span>
      </button>
    );
  };

  // Rows are GK-first. Mobile: vertical pitch (home bottom); xl+: horizontal pitch (home left).
  const renderHalf = (rows, side) => (
    <div className={`relative flex-1 flex ${side === 'home' ? 'flex-col-reverse xl:flex-row' : 'flex-col xl:flex-row-reverse'} py-3 xl:py-0 xl:px-3`}>
      {rows.map((row, i) => (
        <div key={`${side}-${i}`} className="flex-1 flex xl:flex-col items-center justify-around">
          {row.map(p => renderPlayerNode(p, side))}
        </div>
      ))}
    </div>
  );

  const renderBench = (lineup, team, side) => {
    const subs = lineup?.substitutes || [];
    const hasStats = (playerStats?.[side] || []).length > 0;
    return (
      <div className="min-w-0">
        <div className="flex items-center gap-2 px-4 py-2.5 bg-background-tertiary border-b border-border-light">
          <img src={team?.badge} alt="" className="w-5 h-5 object-contain" />
          <span className="text-xs font-semibold text-text-primary truncate">{team?.name}</span>
          <span className="ml-auto text-xs font-bold text-text-muted">{subs.length} oyuncu</span>
        </div>
        {subs.length === 0 ? (
          <p className="text-xs text-text-muted text-center py-6">Kayıtlı yedek oyuncu yok.</p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {subs.map((sub, idx) => {
              const stats = getStats(sub.id, side);
              const played = stats.minutes > 0;
              const rating = played ? stats.rating : (hasStats ? null : sub.rating);
              return (
                <li key={sub.id || idx}>
                  <button
                    type="button"
                    onClick={(e) => onPlayerClick && onPlayerClick(sub, side, e)}
                    title={`${sub.name} maç performansını görüntüle`}
                    className={`w-full flex items-center gap-3 px-4 py-2 text-left hover:bg-background-tertiary transition-colors group ${hasStats && !played ? 'opacity-55 hover:opacity-100' : ''}`}
                  >
                    <span className="w-5 text-right font-mono text-xs font-bold text-text-muted">{sub.shirt ?? '-'}</span>
                    <PlayerAvatar photoUrl={sub.photo_url} name={sub.name} shirt={sub.shirt} fallback="initials" size="w-8 h-8 text-xs" />
                    <div className="min-w-0 flex-1">
                      <div className="text-xs sm:text-sm font-bold text-text-primary truncate group-hover:text-text-primary transition-colors">{sub.name}</div>
                      <div className="flex items-center gap-1.5 text-xs font-semibold text-text-muted">
                        <span>{POSITION_LABEL[sub.position] || sub.position || '-'}</span>
                        {played && (
                          // shortcut: entry minute inferred as 90 - minutes played, off by stoppage time
                          <span className="inline-flex items-center text-emerald-600 font-mono font-semibold" title="Oyuna girdi">
                            <ArrowUp className="w-2.5 h-2.5" strokeWidth={3} />{Math.max(1, 90 - stats.minutes)}'
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      {Array.from({ length: stats.goals || 0 }).map((_, i) => <BallIcon key={i} className="w-3.5 h-3.5 text-text-secondary" />)}
                      {stats.red_cards > 0 ? <RedCardIcon /> : stats.yellow_cards > 0 ? <YellowCardIcon /> : null}
                      {rating != null && (
                        <span className={`min-w-[30px] text-center px-1 rounded-md font-mono font-semibold text-xs leading-5 ${ratingClass(rating)}`}>
                          {Number(rating).toFixed(1)}
                        </span>
                      )}
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-5">
      <div className="rounded overflow-hidden bg-primary shadow-xl ring-1 ring-black/5">
        <div className="flex items-center justify-between gap-4 px-4 sm:px-6 py-3.5 text-white bg-primary">
          <TeamHeader team={homeTeam} lineup={homeLineup} label="Ev" />
          <TeamHeader team={awayTeam} lineup={awayLineup} label="Dep" align="right" />
        </div>

        <div className="relative w-full aspect-[3/4] min-h-[620px] sm:min-h-0 xl:aspect-[4/3] bg-[#1d6b3a] select-none">
          <div className="absolute inset-0 flex flex-col xl:flex-row pointer-events-none">
            {[...Array(14)].map((_, i) => (
              <div key={i} className={`flex-1 ${i % 2 === 0 ? 'bg-background-primary/[0.035]' : 'bg-black/[0.06]'}`} />
            ))}
          </div>
          <div className="absolute inset-0 pointer-events-none bg-[radial-gradient(ellipse_at_center,transparent_55%,rgba(0,0,0,0.25))]" />
          <svg className="absolute inset-0 w-full h-full pointer-events-none xl:hidden" viewBox="-2 -2 72 109" preserveAspectRatio="none" aria-hidden="true">
            <g transform="translate(68 0) rotate(90)"><PitchMarkings /></g>
          </svg>
          <svg className="absolute inset-0 w-full h-full pointer-events-none hidden xl:block" viewBox="-2 -2 109 72" aria-hidden="true">
            <PitchMarkings />
          </svg>

          <div className="absolute inset-0 flex flex-col-reverse xl:flex-row px-1 sm:px-3 py-2 xl:py-3">
            {renderHalf(homeRows, 'home')}
            {renderHalf(awayRows, 'away')}
          </div>
        </div>
      </div>

      <div className="bg-background-primary border border-border rounded  overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-border">
          <h4 className="text-sm font-semibold text-text-primary">Yedek Kulübesi</h4>
          <span className="text-xs text-text-muted font-medium">Detay için oyuncuya tıklayın</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 md:divide-x divide-slate-200">
          {renderBench(homeLineup, homeTeam, 'home')}
          {renderBench(awayLineup, awayTeam, 'away')}
        </div>
      </div>
    </div>
  );
}
