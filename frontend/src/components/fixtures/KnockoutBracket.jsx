import { Trophy, Swords } from 'lucide-react';
import EmptyState from '../common/EmptyState';
import InlineError from '../common/InlineError';
import Skeleton from '../common/Skeleton';
import { REASON_SUFFIX } from '../../utils/knockout';
import { handleTeamBadgeError } from '../../utils/imageFallbacks';

const MIN_COLUMN_PX = 92; // narrowest column; below this total width the bracket scrolls sideways instead of squeezing further
const GAP_PX = 12;

const goalsOf = (leg, teamId) => {
  if (leg.home_score == null || leg.away_score == null) return null;
  return leg.home.id === teamId
    ? { goals: leg.home_score, shootout: leg.home_penalties }
    : { goals: leg.away_score, shootout: leg.away_penalties };
};

function TieCard({ tie, isFinal, align, onSelectTeam, onSelectLeg }) {
  const [first, second] = tie.teams;
  const twoLegs = tie.legs.length > 1;
  const how = REASON_SUFFIX[tie.reason];

  // Single figure per team: the aggregate for two legs, the match score for a single match.
  const figure = team => {
    if (twoLegs) return tie.aggregate ? tie.aggregate[team.id] : '-';
    const score = goalsOf(tie.legs[0], team.id);
    return score ? score.goals : '-';
  };

  return (
    <div className={`relative ${isFinal ? 'w-full' : ''}`}>
      {/* short connector towards the centre of the bracket */}
      {align === 'left' && <span aria-hidden="true" className="absolute top-1/2 -right-3 w-3 h-px bg-border" />}
      {align === 'right' && <span aria-hidden="true" className="absolute top-1/2 -left-3 w-3 h-px bg-border" />}

      <div className={`bg-background-primary border rounded overflow-hidden ${isFinal ? 'border-accent' : 'border-border'}`}>
        <div className="divide-y divide-border-light">
          {tie.teams.map(team => {
            const won = tie.winner_id === team.id;
            const decided = tie.winner_id != null;
            const shootout = !twoLegs ? goalsOf(tie.legs[0], team.id)?.shootout : null;
            return (
              <div key={team.id} className={`flex items-center gap-1.5 px-2 py-1.5 border-l-2 ${won ? 'border-accent bg-accent-soft' : 'border-transparent'}`}>
                <img src={team.logo} alt="" className="w-4 h-4 object-contain shrink-0" onError={handleTeamBadgeError} />
                <button
                  type="button"
                  onClick={() => onSelectTeam?.(team.id)}
                  title={team.name}
                  className={`flex-1 min-w-0 truncate text-left text-xs hover:underline rounded-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-border-focus ${
                    won ? 'font-semibold text-text-primary' : decided ? 'font-normal text-text-secondary' : 'font-normal text-text-primary'
                  }`}
                >
                  {isFinal ? team.name : (
                    <>
                      <span className="2xl:hidden">{team.abbr || team.name}</span>
                      <span className="hidden 2xl:inline">{team.name}</span>
                    </>
                  )}
                </button>
                <span className={`text-xs tabular-nums ${won ? 'font-semibold text-text-primary' : 'text-text-secondary'}`}>
                  {figure(team)}
                  {shootout != null && <sup className="text-text-secondary">{shootout}</sup>}
                </span>
              </div>
            );
          })}
        </div>

        <p className="flex flex-wrap items-center justify-center gap-x-1.5 px-2 py-1 text-xs border-t border-border-light text-text-secondary tabular-nums">
          {isFinal && tie.winner_id
            ? <span className="font-semibold text-accent">Şampiyon{how ? ` (${how})` : ''}</span>
            : twoLegs
              ? tie.legs.map((leg, index) => {
                const a = goalsOf(leg, first.id);
                const b = goalsOf(leg, second.id);
                return (
                  <span key={leg.match_id} className="inline-flex items-center gap-1.5">
                    {index > 0 && <span aria-hidden="true">·</span>}
                    <button
                      type="button"
                      onClick={() => onSelectLeg(leg.match_id)}
                      title={`${leg.leg}. maç: ${leg.home.name} - ${leg.away.name}`}
                      className="hover:underline rounded-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-border-focus"
                    >
                      {a && b ? `${a.goals}-${b.goals}` : 'v'}
                    </button>
                  </span>
                );
              })
              : (
                <button type="button" onClick={() => onSelectLeg(tie.legs[0].match_id)} className="hover:underline rounded-sm">
                  {tie.legs[0].status === 'COMPLETED' ? 'Maç detayı' : (tie.legs[0].kickoff_label || 'Oynanmadı').split(',')[0]}
                </button>
              )}
        </p>
      </div>
    </div>
  );
}

function Column({ title, ties, isFinal = false, align, onSelectTeam, onSelectLeg, emptyLabel }) {
  return (
    <section className="flex flex-col min-w-0" aria-label={title}>
      <h3 className={`text-xs font-semibold text-center mb-2 ${isFinal ? 'text-accent' : 'text-text-primary'}`}>{title}</h3>
      <div className="flex-1 flex flex-col justify-around gap-3">
        {ties.length === 0 && emptyLabel && (
          <p className="text-xs text-center text-text-secondary border border-dashed border-border rounded px-2 py-4">{emptyLabel}</p>
        )}
        {ties.map(tie => (
          <TieCard
            key={`${tie.stage}-${tie.teams.map(team => team.id).join('-')}`}
            tie={tie}
            isFinal={isFinal}
            align={align}
            onSelectTeam={onSelectTeam}
            onSelectLeg={onSelectLeg}
          />
        ))}
      </div>
    </section>
  );
}

export default function KnockoutBracket({ bracket, loading, error, onRetry, matchesById, onSelectMatch, onSelectTeam }) {
  if (loading) {
    return (
      <div className="grid grid-cols-5 gap-4" aria-busy="true">
        {[2, 4, 2, 4, 2].map((rows, column) => (
          <div key={column} className="space-y-3">
            <Skeleton className="h-4 w-16 mx-auto" />
            {Array.from({ length: rows }).map((_, row) => <Skeleton key={row} className="h-20" />)}
          </div>
        ))}
      </div>
    );
  }
  if (error) return <InlineError message="Turnuva ağacı yüklenemedi." onRetry={onRetry} />;

  const rounds = bracket?.rounds || [];
  if (!rounds.length) {
    return <EmptyState icon={Swords}>Eleme turları henüz belli değil. Lig aşaması bittiğinde buradan takip edebilirsiniz.</EmptyState>;
  }

  const selectLeg = matchId => {
    const match = matchesById.get(Number(matchId));
    if (match) onSelectMatch?.(match);
  };

  // Left half runs towards the centre from the left, the right half mirrors it from the right; the final sits between.
  const early = rounds.filter(round => round.stage !== 'final');
  const finalRound = rounds.find(round => round.stage === 'final');
  const split = ties => [ties.slice(0, Math.ceil(ties.length / 2)), ties.slice(Math.ceil(ties.length / 2))];
  const leftColumns = early.map(round => ({ ...round, ties: split(round.ties)[0] }));
  const rightColumns = [...early].reverse().map(round => ({ ...round, ties: split(round.ties)[1] }));
  const columnCount = leftColumns.length + 1 + rightColumns.length;

  return (
    <div className="space-y-4">
      {bracket.champion && (
        <div className="flex items-center justify-center gap-3 bg-background-primary border border-border border-l-2 border-l-accent rounded p-3">
          <Trophy className="w-5 h-5 text-accent shrink-0" strokeWidth={1.5} aria-hidden="true" />
          <img src={bracket.champion.logo} alt="" className="w-7 h-7 object-contain shrink-0" onError={handleTeamBadgeError} />
          <div>
            <p className="text-xs text-text-secondary">Şampiyon</p>
            <p className="text-base font-semibold text-text-primary">{bracket.champion.name}</p>
          </div>
        </div>
      )}

      <div className="overflow-x-auto pb-2">
        <div
          className="grid items-stretch w-full"
          style={{
            columnGap: `${GAP_PX}px`,
            // the final in the middle gets a little more room than the other columns
            gridTemplateColumns: `repeat(${leftColumns.length}, minmax(0, 1fr)) minmax(0, 1.3fr) repeat(${rightColumns.length}, minmax(0, 1fr))`,
            minWidth: `${columnCount * MIN_COLUMN_PX + (columnCount - 1) * GAP_PX}px`,
          }}
        >
          {leftColumns.map(round => (
            <Column key={`l-${round.stage}`} title={round.title} ties={round.ties} align="left" onSelectTeam={onSelectTeam} onSelectLeg={selectLeg} />
          ))}
          <Column
            title="Final"
            ties={finalRound ? finalRound.ties : []}
            isFinal
            onSelectTeam={onSelectTeam}
            onSelectLeg={selectLeg}
            emptyLabel="Henüz belli değil"
          />
          {rightColumns.map(round => (
            <Column key={`r-${round.stage}`} title={round.title} ties={round.ties} align="right" onSelectTeam={onSelectTeam} onSelectLeg={selectLeg} />
          ))}
        </div>
      </div>
    </div>
  );
}
