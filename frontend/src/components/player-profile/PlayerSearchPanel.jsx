import { Search, X } from 'lucide-react';
import { getTeam } from '../../data/teams';
import PlayerAvatar from '../PlayerAvatar';

export default function PlayerSearchPanel({ searchTerm, onSearchChange, players, selectedPlayerId, onSelectPlayer }) {
  return (
    <>
      <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="relative flex-1 w-full">
            <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={searchTerm}
              onChange={event => onSearchChange(event.target.value)}
              placeholder="Oyuncu ara"
              className="w-full bg-white border border-slate-200 rounded-xl pl-10 pr-9 py-2.5 text-sm font-medium text-slate-900 placeholder-slate-400 outline-none focus:border-slate-400 transition-all"
            />
            {searchTerm && (
              <button
                onClick={() => onSearchChange('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-200 transition-colors"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>
      </div>

      {players.length > 0 && searchTerm.trim() && (
        <div className="bg-white border border-slate-200 rounded-2xl p-3 shadow-sm">
          <div className="flex items-center gap-2 overflow-x-auto pb-1.5 scrollbar-thin">
            {players.slice(0, 24).map(player => {
              const team = getTeam(player.teamId, player.teamName);
              const selected = player.id === selectedPlayerId;
              return (
                <button
                  key={player.id}
                  onClick={() => onSelectPlayer(player.id)}
                  className={`flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-bold transition-all shrink-0 border ${selected ? 'bg-slate-100 text-slate-950 border-slate-400' : 'bg-slate-50 hover:bg-slate-100 text-slate-700 border-slate-200'}`}
                >
                  <PlayerAvatar player={player} size="sm" className="w-7 h-7 rounded-lg" />
                  <div className="text-left min-w-0">
                    <div className="flex items-center gap-1.5 leading-tight">
                      <span className="truncate max-w-[120px]">{player.name}</span>
                      {player.shirt ? <span className="rounded bg-slate-200 px-1 font-mono text-[10px] font-bold text-slate-700">#{player.shirt}</span> : null}
                    </div>
                    <span className="block max-w-[110px] truncate text-[10px] font-medium text-slate-500">{team.short || player.teamName}</span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </>
  );
}
