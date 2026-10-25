import PlayerAvatar from '../PlayerAvatar';
import { StatsCard } from './statsParts';

const ROWS = ['F', 'M', 'D', 'G'];

function PitchPlayer({ player }) {
  return (
    <div className="flex flex-col items-center gap-1 w-20 sm:w-24 min-w-0">
      <PlayerAvatar player={player} size="md" shape="circle" fallback="initials" className="border border-white/60" />
      <span className="max-w-full truncate text-xs font-medium text-white">{player.name}</span>
      <span className="rounded-sm bg-background-primary px-1.5 text-xs font-semibold tabular-nums text-text-primary">
        {player.rating.toFixed(1)}
      </span>
    </div>
  );
}

export default function TeamOfScope({ data, title, scopeLabel }) {
  const players = data?.players || [];
  const meta = data?.average_rating != null
    ? `${data.formation} · ortalama ${data.average_rating.toFixed(1)}`
    : data?.formation;

  return (
    <StatsCard title={title} meta={meta} className="h-full">
      {players.length === 0 ? (
        <p className="px-4 py-8 text-center text-sm text-text-secondary">Kadro için yeterli oyuncu verisi yok.</p>
      ) : (
        <div className="p-4 flex flex-col gap-3">
          <div className="relative rounded border border-border bg-pitch px-2 py-5 flex flex-col gap-5">
            <div aria-hidden="true" className="absolute inset-x-0 top-1/2 border-t border-white/20" />
            {ROWS.map(group => (
              <div key={group} className="relative flex items-start justify-around gap-1">
                {players.filter(p => p.position === group).map(player => (
                  <PitchPlayer key={player.id} player={player} />
                ))}
              </div>
            ))}
          </div>
          <p className="text-xs text-text-secondary">
            Model reytingi{data.min_matches > 1 ? `, en az ${data.min_matches} maç` : ''}. {scopeLabel}
            {!data.complete && ' Bazı mevkiler için yeterli oyuncu bulunamadı.'}
          </p>
        </div>
      )}
    </StatsCard>
  );
}
