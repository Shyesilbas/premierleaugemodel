import { useMemo, useState } from 'react';
import { ChevronLeft, ChevronRight, Home, Plane } from 'lucide-react';
import { handleTeamBadgeError } from '../../utils/imageFallbacks';
import { RESULT_META } from './teamProfileUtils';

const MONTH_NAMES = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık'];
const WEEKDAYS = ['Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt', 'Paz'];

// Captured once at load: the calendar only needs the current day to highlight it.
const TODAY = new Date();

const monthIndex = (date) => date.getFullYear() * 12 + date.getMonth();
const dayKey = (date) => `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`;

function NavButton({ onClick, disabled, label, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      className="h-8 w-8 rounded border border-border bg-background-primary inline-flex items-center justify-center text-text-secondary transition-colors duration-150 ease-out hover:border-card-border-hover hover:text-text-primary disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-border-focus"
    >
      {children}
    </button>
  );
}

function MatchCell({ entry, onOpen }) {
  const { opponent, isHome, isPlayed, result, scoreLabel, time, dateLabel } = entry;
  const venue = isHome ? 'ev sahibi' : 'deplasman';
  const outcome = isPlayed ? `${RESULT_META[result]?.title || ''} ${scoreLabel}` : time;

  return (
    <button
      type="button"
      onClick={() => onOpen(entry.modalMatchObj)}
      aria-label={`${dateLabel}, ${opponent.name}, ${venue}. ${outcome}`}
      className="absolute inset-0 flex flex-col items-center justify-center gap-0.5 pt-4 pb-1 cursor-pointer transition-colors duration-150 ease-out hover:bg-background-tertiary focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-border-focus"
    >
      <span className="absolute top-1 right-1 text-text-tertiary" title={isHome ? 'Ev sahibi' : 'Deplasman'}>
        {isHome
          ? <Home className="w-3.5 h-3.5" strokeWidth={1.5} aria-hidden="true" />
          : <Plane className="w-3.5 h-3.5" strokeWidth={1.5} aria-hidden="true" />}
      </span>
      <img
        src={opponent.badge}
        alt=""
        className="w-6 h-6 sm:w-8 sm:h-8 object-contain"
        onError={handleTeamBadgeError}
      />
      {isPlayed ? (
        <span className={`rounded-sm px-1 text-xs font-semibold tabular-nums ${RESULT_META[result]?.className || 'bg-status-error text-white'}`}>
          {scoreLabel}
        </span>
      ) : (
        <span className="text-xs text-text-secondary tabular-nums">{time || 'vs'}</span>
      )}
    </button>
  );
}

export default function TeamFixturesCalendar({ entries, onOpen }) {
  const dated = useMemo(() => entries.filter(entry => entry.date), [entries]);
  const undatedCount = entries.length - dated.length;

  const { minMonth, maxMonth, initialMonth } = useMemo(() => {
    if (dated.length === 0) {
      return { minMonth: monthIndex(TODAY), maxMonth: monthIndex(TODAY), initialMonth: monthIndex(TODAY) };
    }
    const months = dated.map(entry => monthIndex(entry.date));
    const nextUpcoming = dated.find(entry => !entry.isPlayed);
    const fallback = dated[dated.length - 1];
    return {
      minMonth: Math.min(...months),
      maxMonth: Math.max(...months),
      initialMonth: monthIndex((nextUpcoming || fallback).date),
    };
  }, [dated]);

  const [cursor, setCursor] = useState(initialMonth);
  const month = Math.min(Math.max(cursor, minMonth), maxMonth);
  const year = Math.floor(month / 12);
  const monthInYear = month % 12;

  const byDay = useMemo(() => {
    const map = new Map();
    dated.forEach(entry => map.set(dayKey(entry.date), entry));
    return map;
  }, [dated]);

  const daysInMonth = new Date(year, monthInYear + 1, 0).getDate();
  const leadingBlanks = (new Date(year, monthInYear, 1).getDay() + 6) % 7;
  const totalCells = Math.ceil((leadingBlanks + daysInMonth) / 7) * 7;

  const matchesThisMonth = dated.filter(entry => monthIndex(entry.date) === month).length;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-baseline gap-2">
          <h4 className="text-sm font-semibold text-text-primary tabular-nums">{MONTH_NAMES[monthInYear]} {year}</h4>
          <span className="text-xs text-text-secondary tabular-nums">{matchesThisMonth} maç</span>
        </div>
        <div className="flex items-center gap-1">
          <NavButton label="Önceki ay" disabled={month <= minMonth} onClick={() => setCursor(month - 1)}>
            <ChevronLeft className="w-4 h-4" strokeWidth={1.5} />
          </NavButton>
          <NavButton label="Sonraki ay" disabled={month >= maxMonth} onClick={() => setCursor(month + 1)}>
            <ChevronRight className="w-4 h-4" strokeWidth={1.5} />
          </NavButton>
        </div>
      </div>

      <div className="grid grid-cols-7 gap-px bg-border border border-border rounded overflow-hidden">
        {WEEKDAYS.map(day => (
          <div key={day} className="bg-background-tertiary py-1.5 text-center text-xs font-medium text-text-secondary">{day}</div>
        ))}

        {Array.from({ length: totalCells }).map((_, index) => {
          const dayNumber = index - leadingBlanks + 1;
          if (dayNumber < 1 || dayNumber > daysInMonth) {
            return <div key={index} className="bg-background-secondary min-h-16 sm:min-h-24" />;
          }
          const date = new Date(year, monthInYear, dayNumber);
          const entry = byDay.get(dayKey(date));
          const isToday = dayKey(date) === dayKey(TODAY);
          return (
            <div key={index} className="relative bg-background-primary min-h-16 sm:min-h-24">
              <span
                className={`absolute top-1 left-1 z-10 text-xs tabular-nums ${
                  isToday
                    ? 'min-w-5 h-5 px-1 rounded-sm bg-primary text-white inline-flex items-center justify-center font-medium'
                    : 'text-text-tertiary'
                }`}
              >
                {dayNumber}
              </span>
              {entry && <MatchCell entry={entry} onOpen={onOpen} />}
            </div>
          );
        })}
      </div>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-text-secondary">
        <span className="inline-flex items-center gap-1.5">
          <Home className="w-3.5 h-3.5" strokeWidth={1.5} aria-hidden="true" /> Ev sahibi
        </span>
        <span className="inline-flex items-center gap-1.5">
          <Plane className="w-3.5 h-3.5" strokeWidth={1.5} aria-hidden="true" /> Deplasman
        </span>
        <span>Saatler İngiltere saatiyle</span>
        {undatedCount > 0 && <span>{undatedCount} maçın tarihi belli değil</span>}
      </div>
    </div>
  );
}
