import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';
import { handleTeamBadgeError } from '../../utils/imageFallbacks';
import PlayerAvatar from '../PlayerAvatar';
import { BallIcon, RedCardIcon, YellowCardIcon } from './eventIcons';

const ratingClass = (r) =>
  r == null ? 'bg-slate-700 text-slate-300'
    : r >= 7.5 ? 'bg-emerald-500 text-white'
    : r >= 6.5 ? 'bg-sky-500 text-white'
    : r >= 5.5 ? 'bg-amber-500 text-white'
    : 'bg-rose-500 text-white';

function StatGroup({ title, rows, wide = false }) {
  const visible = rows.filter(Boolean);
  if (visible.length === 0) return null;
  return (
    <section className={wide ? 'col-span-2' : ''}>
      <h4 className="px-1 mb-1 text-[10px] font-black uppercase tracking-wider text-slate-400">{title}</h4>
      <dl className="rounded-xl border border-slate-200 divide-y divide-slate-100 bg-white">
        {visible.map(([label, value, highlight]) => (
          <div key={label} className="flex items-center justify-between gap-2 px-2.5 py-1.5 text-xs">
            <dt className="text-slate-600 truncate">{label}</dt>
            <dd className={`font-mono font-black ${highlight ? 'text-[#38003c]' : 'text-slate-900'}`}>{value}</dd>
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
      <div className="fixed inset-0 z-40 bg-slate-950/50 backdrop-blur-[2px] lg:hidden" onClick={onClose} />

      <aside
        ref={panelRef}
        style={coords ? { top: coords.top, left: coords.left } : undefined}
        role="dialog"
        aria-label={`${p.name} maç performansı`}
        className="fixed z-50 inset-x-0 bottom-0 max-h-[85vh] rounded-t-3xl lg:absolute lg:inset-auto lg:max-h-[calc(100vh-1rem)] lg:w-[340px] lg:rounded-2xl bg-slate-50 shadow-2xl ring-1 ring-black/10 flex flex-col overflow-hidden animate-panelIn"
      >
        {/* Header */}
        <div className="relative shrink-0 bg-gradient-to-br from-[#38003c] to-[#1f0022] text-white px-4 pt-4 pb-3">
          <div className="mx-auto mb-3 h-1 w-10 rounded-full bg-white/25 lg:hidden" />
          <button
            type="button"
            onClick={onClose}
            className="absolute top-3 right-3 p-1.5 rounded-full bg-white/10 hover:bg-white/20 text-white/80 hover:text-white transition-colors"
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
                className="!border-0 ring-2 ring-white/80 bg-white"
              />
              {p.captain && (
                <span className="absolute -bottom-0.5 -left-0.5 w-5 h-5 rounded-full bg-amber-400 text-slate-950 font-black text-[10px] flex items-center justify-center ring-2 ring-[#38003c]" title="Kaptan">C</span>
              )}
            </div>
            <div className="min-w-0">
              <h3 className="text-base font-black leading-tight truncate">{p.name}</h3>
              <div className="mt-1 flex items-center gap-1.5 text-xs text-white/70">
                <img src={team?.badge} alt="" className="w-4 h-4 object-contain" onError={handleTeamBadgeError} />
                <span className="truncate">{team?.name}</span>
              </div>
              <div className="mt-1.5 flex items-center gap-1.5 text-[11px] font-bold">
                <span className="font-mono text-white/60">#{p.shirt ?? '-'}</span>
                <span className="px-1.5 py-px rounded-md bg-white/10">{formatPosition(p.position)}</span>
                {isCompleted && (
                  <span className="px-1.5 py-px rounded-md bg-white/10 text-white/80">{s.is_starter ? 'İlk 11' : played ? 'Yedekten girdi' : 'Oynamadı'}</span>
                )}
              </div>
            </div>
          </div>

          <div className="mt-3 grid grid-cols-4 gap-1.5 text-center">
            <div className={`rounded-lg py-1.5 ${ratingClass(rating)}`} title={isCompleted ? 'Maç notu' : '5 maçlık form puanı'}>
              <div className="text-base font-black font-mono leading-none">{rating != null ? Number(rating).toFixed(1) : '—'}</div>
              <div className="mt-0.5 text-[10px] font-bold opacity-80">{isCompleted ? 'Not' : 'Form'}</div>
            </div>
            {isCompleted ? summary.map(([label, value]) => (
              <div key={label} className="rounded-lg py-1.5 bg-white/10">
                <div className="text-base font-black font-mono leading-none">{value}</div>
                <div className="mt-0.5 text-[10px] font-bold text-white/60">{label}</div>
              </div>
            )) : (
              <>
                <div className="col-span-2 rounded-lg py-1.5 bg-white/10">
                  <div className="text-sm font-black leading-5">{p.form_label || 'Normal'}</div>
                  <div className="mt-0.5 text-[10px] font-bold text-white/60">Form durumu</div>
                </div>
                <div className="rounded-lg py-1.5 bg-white/10">
                  <div className="text-base font-black font-mono leading-none">{p.cards_risk ?? '—'}</div>
                  <div className="mt-0.5 text-[10px] font-bold text-white/60">Kart riski</div>
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
            <p className="col-span-2 py-6 text-center text-sm text-slate-500">Bu oyuncu maçta forma giymedi.</p>
          ) : (
            <>
              {(s.goals > 0 || s.assists > 0 || s.yellow_cards > 0 || s.red_cards > 0 || s.penalties_missed > 0) && (
                <div className="col-span-2 flex flex-wrap gap-1.5">
                  {s.goals > 0 && <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-white border border-slate-200 text-xs font-bold text-slate-800"><BallIcon className="w-3.5 h-3.5" /> {s.goals} gol</span>}
                  {s.assists > 0 && <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-white border border-slate-200 text-xs font-bold text-slate-800"><span className="font-black text-[#38003c]">A</span> {s.assists} asist</span>}
                  {s.yellow_cards > 0 && <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white border border-slate-200 text-xs font-bold text-slate-800"><YellowCardIcon /> Sarı kart</span>}
                  {s.red_cards > 0 && <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white border border-slate-200 text-xs font-bold text-slate-800"><RedCardIcon /> Kırmızı kart</span>}
                  {s.penalties_missed > 0 && <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-rose-50 border border-rose-200 text-xs font-bold text-rose-700">{s.penalties_missed} penaltı kaçırdı</span>}
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
