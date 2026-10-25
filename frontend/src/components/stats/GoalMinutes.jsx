import { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { StatsCard } from './statsParts';

function Bars({ labels, scored, conceded, max }) {
  return (
    <div className="grid gap-2" style={{ gridTemplateColumns: `repeat(${labels.length}, minmax(0, 1fr))` }}>
      {labels.map((label, index) => (
        <div key={label} className="flex flex-col items-center gap-2 min-w-0">
          <div className="flex items-end justify-center gap-1 h-36 w-full">
            <div className="flex flex-col items-center justify-end h-full w-5 sm:w-7">
              <span className="mb-1 text-xs font-medium text-text-primary tabular-nums">{scored[index]}</span>
              <div className="w-full rounded-sm bg-primary" style={{ height: `${max ? (scored[index] / max) * 100 : 0}%` }} />
            </div>
            {conceded && (
              <div className="flex flex-col items-center justify-end h-full w-5 sm:w-7">
                <span className="mb-1 text-xs text-text-secondary tabular-nums">{conceded[index]}</span>
                <div className="w-full rounded-sm bg-text-muted" style={{ height: `${max ? (conceded[index] / max) * 100 : 0}%` }} />
              </div>
            )}
          </div>
          <span className="text-xs text-text-secondary tabular-nums">{label}</span>
        </div>
      ))}
    </div>
  );
}

function ViewButton({ active, onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={`h-10 px-3 text-sm font-medium transition-colors duration-150 ease-out cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-border-focus ${
        active ? 'bg-primary text-white' : 'bg-background-primary text-text-secondary hover:text-text-primary'
      }`}
    >
      {children}
    </button>
  );
}

export default function GoalMinutes({ data, isWeek, gameweek, cumulativeLabel }) {
  const [teamId, setTeamId] = useState('all');
  const [view, setView] = useState('scope');
  const showScope = isWeek && view === 'scope';
  const labels = data?.labels || [];
  const team = data?.teams?.find(entry => String(entry.team.id) === String(teamId));

  let scored = showScope ? data?.league_scope || [] : data?.league || [];
  let conceded = null;
  if (team) {
    scored = showScope ? team.scope_scored : team.scored;
    conceded = showScope ? team.scope_conceded : team.conceded;
  }
  const total = scored.reduce((sum, value) => sum + value, 0);
  const concededTotal = conceded ? conceded.reduce((sum, value) => sum + value, 0) : 0;
  const max = Math.max(1, ...scored, ...(conceded || []));

  return (
    <StatsCard title="Gol dakikaları" meta={showScope ? `Hafta ${gameweek}` : cumulativeLabel}>
      <div className="p-4 flex flex-col gap-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div className="flex flex-wrap items-end gap-2">
            <div className="flex flex-col gap-1">
              <label htmlFor="goal-minutes-team" className="text-xs text-text-secondary">Takım</label>
              <div className="relative">
                <select
                  id="goal-minutes-team"
                  value={teamId}
                  onChange={event => setTeamId(event.target.value)}
                  className="appearance-none h-10 min-w-48 pl-3 pr-9 rounded border border-border bg-background-primary text-sm font-medium text-text-primary cursor-pointer transition-colors duration-150 ease-out hover:border-card-border-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-border-focus"
                >
                  <option value="all">Tüm lig</option>
                  {(data?.teams || []).map(entry => (
                    <option key={entry.team.id} value={entry.team.id}>{entry.team.name}</option>
                  ))}
                </select>
                <ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-tertiary" strokeWidth={1.5} aria-hidden="true" />
              </div>
            </div>

            {isWeek && (
              <div className="flex flex-col gap-1">
                <span className="text-xs text-text-secondary">Dönem</span>
                <div className="inline-flex rounded border border-border overflow-hidden" role="group" aria-label="Dönem">
                  <ViewButton active={view === 'scope'} onClick={() => setView('scope')}>Bu hafta</ViewButton>
                  <ViewButton active={view === 'cumulative'} onClick={() => setView('cumulative')}>Hafta {gameweek} itibarıyla</ViewButton>
                </div>
              </div>
            )}
          </div>

          <div className="flex items-center gap-4 text-xs text-text-secondary">
            <span className="inline-flex items-center gap-1.5"><span aria-hidden="true" className="w-2.5 h-2.5 rounded-sm bg-primary" />Atılan gol</span>
            {conceded && <span className="inline-flex items-center gap-1.5"><span aria-hidden="true" className="w-2.5 h-2.5 rounded-sm bg-text-muted" />Yenen gol</span>}
            <span className="tabular-nums">Toplam {total}{conceded ? ` / ${concededTotal}` : ''}</span>
          </div>
        </div>

        {total === 0 && concededTotal === 0 ? (
          <p className="py-8 text-center text-sm text-text-secondary">
            {showScope && team ? 'Bu takımın bu haftaki maçında gol olmadı ya da maç oynanmadı.' : 'Bu kapsamda gol kaydı yok.'}
          </p>
        ) : (
          <Bars labels={labels} scored={scored} conceded={conceded} max={max} />
        )}
      </div>
    </StatsCard>
  );
}
