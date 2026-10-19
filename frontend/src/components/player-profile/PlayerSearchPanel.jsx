import { Search, X } from 'lucide-react';
import { getTeam } from '../../data/teams';
import PlayerAvatar from '../PlayerAvatar';

export default function PlayerSearchPanel({ searchTerm, onSearchChange, players, selectedPlayerId, onSelectPlayer }) {
  return (
    <div className="space-y-3">
      <div className="bg-background-primary border border-border rounded p-4">
        <div className="relative w-full">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-text-tertiary pointer-events-none" />
          <input
            type="text"
            value={searchTerm}
            onChange={event => onSearchChange(event.target.value)}
            placeholder="Oyuncu ara..."
            className="w-full h-10 bg-background-primary border border-border rounded pl-10 pr-9 py-2 text-sm text-text-primary placeholder:text-text-muted outline-none focus:border-border-focus transition-colors"
          />
          {searchTerm && (
            <button
              type="button"
              onClick={() => onSearchChange('')}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 p-1 text-text-tertiary hover:text-text-primary rounded transition-colors"
              aria-label="Aramayı temizle"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {players.length > 0 && searchTerm.trim() && (
        <div className="bg-background-primary border border-border rounded p-3">
          <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none">
            {players.slice(0, 24).map(player => {
              const team = getTeam(player.teamId, player.teamName);
              const selected = player.id === selectedPlayerId;
              return (
                <button
                  key={player.id}
                  type="button"
                  onClick={() => onSelectPlayer(player.id)}
                  className={`flex items-center gap-2.5 px-3 py-2 rounded text-xs transition-colors shrink-0 border ${
                    selected
                      ? 'bg-primary text-white border-primary font-medium'
                      : 'bg-background-primary hover:bg-background-secondary text-text-primary border-border hover:border-card-border-hover'
                  }`}
                >
                  <PlayerAvatar player={player} size="sm" shape="circle" className="w-7 h-7" />
                  <div className="text-left min-w-0">
                    <div className="flex items-center gap-1.5 leading-tight">
                      <span className="truncate max-w-[120px] font-medium">{player.name}</span>
                      {player.shirt ? (
                        <span className={`px-1 font-mono text-xs rounded-sm ${selected ? 'text-white/80' : 'text-text-tertiary'}`}>
                          #{player.shirt}
                        </span>
                      ) : null}
                    </div>
                    <span className={`block max-w-[110px] truncate text-xs ${selected ? 'text-white/70' : 'text-text-secondary'}`}>
                      {team.short || player.teamName}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
