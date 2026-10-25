import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';
import { handleTeamBadgeError } from '../../utils/imageFallbacks';
import PlayerAvatar from '../PlayerAvatar';
import { BallIcon, RedCardIcon, YellowCardIcon } from './eventIcons';

const ratingClass = (r) =>
  r == null ? 'bg-background-tertiary text-text-tertiary'
    : r >= 7.5 ? 'bg-background-tertiary text-text-primary'
    : r >= 6.5 ? 'bg-background-tertiary text-text-primary'
    : r >= 5.5 ? 'bg-background-tertiary text-text-primary'
    : 'bg-background-tertiary text-text-primary';

function StatGroup({ title, rows, wide = false }) {
  const visible = rows.filter(Boolean);
  if (visible.length === 0) return null;
  return (
    <section className={wide ? 'col-span-2' : ''}>
      <h4 className="px-1 mb-1 text-xs font-semibold text-text-tertiary">{title}</h4>
      <dl className="rounded border border-border divide-y divide-border-light bg-background-primary">
        {visible.map(([label, value, highlight]) => (
          <div key={label} className="flex items-center justify-between gap-2 px-2.5 py-1.5 text-xs">
            <dt className="text-text-secondary truncate">{label}</dt>
            <dd className={`tabular-nums font-semibold ${highlight ? 'text-primary' : 'text-text-primary'}`}>{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

export default function PlayerMatchPanel({ selectedPlayer, onClose, isCompleted, formatPosition }) {
  const panelRef = useRef(null);
  const [coords, setCoords] = useState(null);

  useEffect(() => {
    if (!selectedPlayer) return undefined;
    const onKey = (e) => e.key === 'Escape' && onClose();
    // Desktop popover: clicking anywhere outside closes it (clicking another player then reopens on that player)
    const onDown = (e) => {
      if (window.innerWidth >= 1024 && panelRef.current && !panelRef.current.contains(e.target)) onClose();
    };
    window.addEventListener('keydown', onKey);
    document.addEventListener('mousedown', onDown);
    return () => {
      window.removeEventListener('keydown', onKey);
      document.removeEventListener('mousedown', onDown);
    };
  }, [selectedPlayer, onClose]);

  // Desktop: anchor the card next to the clicked player, in page coordinates so it scrolls with the page
  useLayoutEffect(() => {
    const a = selectedPlayer?.anchor;
    if (!a || window.innerWidth < 1024 || !panelRef.current) { setCoords(null); return; }
    const w = panelRef.current.offsetWidth;
    const h = panelRef.current.offsetHeight;
    const gap = 12;
    const left = window.innerWidth - a.right >= w + gap + 8 ? a.right + gap : Math.max(8, a.left - w - gap);
    const top = Math.min(Math.max(a.top + a.height / 2 - h / 2, 8), window.innerHeight - h - 8);
    setCoords({ top: top + window.scrollY, left: left + window.scrollX });
  }, [selectedPlayer]);

  if (!selectedPlayer) return null;

  const { player: p, stats: s, team } = selectedPlayer;
  const pos = String(p.position || s.position || 'M').toUpperCase();
  const isGK = ['G', 'GK'].includes(pos);
  const rating = s.rating ?? p.rating ?? null;
  const shots = Number(s.shots || 0);
  const onTarget = Number(s.shots_ontarget || 0);
  const minutes = Number(s.minutes || 0);
  const played = isCompleted && minutes > 0;

  const summary = isGK
    ? [['Dakika', `${minutes}'`], ['Kurtarış', s.saves || 0], ['Yenen', s.opp_score ?? 0]]
    : [['Dakika', `${minutes}'`], ['Gol', s.goals || 0], ['Asist', s.assists || 0]];

  return createPortal(
    <>
      {/* Mobile-only backdrop; on desktop the card is a popover beside the clicked player */}
      <div className="fixed inset-0 z-40 bg-black/40 lg:hidden" onClick={onClose} />

      <aside
        ref={panelRef}
        style={coords ? { top: coords.top, left: coords.left } : undefined}
        role="dialog"
        aria-label={`${p.name} maç performansı`}
        className="fixed z-50 inset-x-0 bottom-0 max-h-screen rounded-t-md lg:absolute lg:inset-auto lg:max-h-screen lg:w-80 lg:rounded bg-background-tertiary ring-1 ring-black/10 flex flex-col overflow-hidden animate-panelIn"
      >
        {/* Header */}
        <div className="relative shrink-0 bg-background-tertiary text-text-primary border-b border-border px-4 pt-4 pb-3">
          <div className="mx-auto mb-3 h-1 w-10 rounded-full bg-background-primary lg:hidden" />
          <button
            type="button"
            onClick={onClose}
            className="absolute top-3 right-3 p-1.5 rounded-full hover:bg-background-secondary text-text-secondary hover:text-text-primary transition-colors"
            title="Kapat (Esc)"
          >
            <X className="w-4 h-4" />
          </button>

          <div className="flex items-center gap-3 pr-8">
            <div className="relative shrink-0">
              <PlayerAvatar
                photoUrl={p.photo_url}
                name={p.name}
                shirt={p.shirt}
                fallback="initials"
                size="w-12 h-12 text-sm"
                className="!border-0 ring-2 ring-white/80 bg-background-primary"
              />
              {p.captain && (
                <span className="absolute -bottom-0.5 -left-0.5 w-5 h-5 rounded-full bg-background-tertiary text-text-primary font-semibold text-xs flex items-center justify-center ring-2 ring-border" title="Kaptan">C</span>
              )}
            </div>
            <div className="min-w-0">
              <h3 className="text-base font-semibold leading-tight truncate">{p.name}</h3>
              <div className="mt-1 flex items-center gap-1.5 text-xs text-text-secondary">
                <img src={team?.badge} alt="" className="w-4 h-4 object-contain" onError={handleTeamBadgeError} />
                <span className="truncate">{team?.name}</span>
              </div>
              <div className="mt-1.5 flex items-center gap-1.5 text-xs font-semibold">
                <span className="tabular-nums text-text-secondary">#{p.shirt ?? '-'}</span>
                <span className="px-1.5 py-px rounded-sm bg-background-primary">{formatPosition(p.position)}</span>
                {isCompleted && (
                  <span className="px-1.5 py-px rounded-sm bg-background-primary text-text-secondary">{s.is_starter ? 'İlk 11' : played ? 'Yedekten girdi' : 'Oynamadı'}</span>
                )}
              </div>
            </div>
          </div>

          <div className="mt-3 grid grid-cols-4 gap-1.5 text-center">
            <div className={`rounded py-1.5 ${ratingClass(rating)}`} title={isCompleted ? 'Maç notu' : '5 maçlık form puanı'}>
              <div className="text-base font-semibold tabular-nums leading-none">{rating != null ? Number(rating).toFixed(1) : '—'}</div>
              <div className="mt-0.5 text-xs font-semibold opacity-80">{isCompleted ? 'Not' : 'Form'}</div>
            </div>
            {isCompleted ? summary.map(([label, value]) => (
              <div key={label} className="rounded py-1.5 bg-background-primary">
                <div className="text-base font-semibold tabular-nums leading-none">{value}</div>
                <div className="mt-0.5 text-xs font-semibold text-text-secondary">{label}</div>
              </div>
            )) : (
              <>
                <div className="col-span-2 rounded py-1.5 bg-background-primary">
                  <div className="text-sm font-semibold leading-5">{p.form_label || 'Normal'}</div>
                  <div className="mt-0.5 text-xs font-semibold text-text-secondary">Form durumu</div>
                </div>
                <div className="rounded py-1.5 bg-background-primary">
                  <div className="text-base font-semibold tabular-nums leading-none">{p.cards_risk ?? '—'}</div>
                  <div className="mt-0.5 text-xs font-semibold text-text-secondary">Kart riski</div>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-3 grid grid-cols-2 gap-3 content-start">
          {!isCompleted ? (
            <StatGroup
              title="Maç öncesi profil"
              wide
              rows={[
                p.form_rating != null && ['Form puanı (son 5)', Number(p.form_rating).toFixed(2)],
                p.attack_rating != null && ['Hücum puanı', Number(p.attack_rating).toFixed(1)],
                p.defense_rating != null && ['Savunma puanı', Number(p.defense_rating).toFixed(1)],
                p.cards_risk != null && ['Kart riski', `${p.cards_risk} / 10`, p.cards_risk >= 7],
              ]}
            />
          ) : !played ? (
            <p className="col-span-2 py-6 text-center text-sm text-text-secondary">Bu oyuncu maçta forma giymedi.</p>
          ) : (
            <>
              {(s.goals > 0 || s.assists > 0 || s.yellow_cards > 0 || s.red_cards > 0 || s.penalties_missed > 0) && (
                <div className="col-span-2 flex flex-wrap gap-1.5">
                  {s.goals > 0 && <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-sm bg-background-primary border border-border text-xs font-semibold text-text-primary"><BallIcon className="w-3.5 h-3.5" /> {s.goals} gol</span>}
                  {s.assists > 0 && <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-sm bg-background-primary border border-border text-xs font-semibold text-text-primary"><span className="font-semibold text-primary">A</span> {s.assists} asist</span>}
                  {s.yellow_cards > 0 && <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-sm bg-background-primary border border-border text-xs font-semibold text-text-primary"><YellowCardIcon /> Sarı kart</span>}
                  {s.red_cards > 0 && <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-sm bg-background-primary border border-border text-xs font-semibold text-text-primary"><RedCardIcon /> Kırmızı kart</span>}
                  {s.penalties_missed > 0 && <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-sm bg-background-tertiary border border-status-error text-xs font-semibold text-status-error">{s.penalties_missed} penaltı kaçırdı</span>}
                </div>
              )}

              <StatGroup
                title="Hücum"
                rows={[
                  ['Gol', s.goals || 0, s.goals > 0],
                  ['Asist', s.assists || 0, s.assists > 0],
                  ['Şut', shots],
                  ['İsabetli şut', shots > 0 ? `${onTarget} (%${Math.round((onTarget / shots) * 100)})` : onTarget],
                  s.penalties_won > 0 && ['Kazanılan pen.', s.penalties_won, true],
                  s.offsides > 0 && ['Ofsayt', s.offsides],
                  s.attack_rating != null && ['Hücum notu', Number(s.attack_rating).toFixed(1)],
                ]}
              />
              <StatGroup
                title="Savunma"
                rows={[
                  isGK && ['Kurtarış', s.saves || 0, s.saves > 0],
                  ['Yenen gol', s.opp_score ?? 0],
                  s.penalties_conceded > 0 && ['Yaptırılan pen.', s.penalties_conceded],
                  s.defense_rating != null && ['Savunma notu', Number(s.defense_rating).toFixed(1)],
                ]}
              />
              <StatGroup
                title="Disiplin"
                rows={[
                  ['Yapılan faul', s.fouls_committed || 0],
                  ['Kazanılan faul', s.fouls_won || 0],
                  ['Sarı kart', s.yellow_cards || 0],
                  s.red_cards > 0 && ['Kırmızı kart', s.red_cards],
                ]}
              />
            </>
          )}
        </div>
      </aside>
    </>,
    document.body
  );
}
