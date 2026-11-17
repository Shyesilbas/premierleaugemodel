import React, { useEffect, useMemo, useRef, useState } from 'react';
import { CornerDownLeft, Search, Shield, X } from 'lucide-react';
import { useCompetition } from '../../context/competitionState';
import { getTeam } from '../../data/teams';
import { getTeams } from '../../services/competitionService';
import { getPlayersCompareData } from '../../services/playerService';
import { handleTeamBadgeError } from '../../utils/imageFallbacks';
import PlayerAvatar from '../PlayerAvatar';

function foldText(s) {
  return String(s || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/ı/g, 'i')
    .replace(/İ/g, 'i')
    .toLowerCase()
    .trim();
}

export default function CommandPalette({ isOpen, onClose, onSelectPlayer, onSelectTeam }) {
  const { activeCompetition, competitionKey } = useCompetition();
  const [directory, setDirectory] = useState({ competition: '', players: [], teams: [] });

  useEffect(() => {
    if (!isOpen) return undefined;
    if (directory.competition === competitionKey && directory.players.length > 0) return undefined;
    let active = true;
    const season = activeCompetition?.default_season || '2026_27';
    Promise.all([
      getPlayersCompareData(competitionKey).catch(() => ({ profiles: [] })),
      getTeams(season, competitionKey).catch(() => ({ teams: [] })),
    ]).then(([comparePayload, teamsPayload]) => {
      if (!active) return;
      setDirectory({
        competition: competitionKey,
        players: comparePayload?.profiles || [],
        teams: (teamsPayload?.teams || []).map((t) => getTeam(t.id, t.name)),
      });
    });
    return () => {
      active = false;
    };
  }, [isOpen, competitionKey, activeCompetition?.default_season, directory.competition, directory.players.length]);

  if (!isOpen) return null;

  const players = directory.competition === competitionKey ? directory.players : [];
  const teams = directory.competition === competitionKey ? directory.teams : [];

  return (
    <CommandPaletteDialog
      competitionName={activeCompetition?.name || 'Premier League'}
      players={players}
      teams={teams}
      onClose={onClose}
      onSelectPlayer={onSelectPlayer}
      onSelectTeam={onSelectTeam}
    />
  );
}

function CommandPaletteDialog({ competitionName, players, teams, onClose, onSelectPlayer, onSelectTeam }) {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const dialogRef = useRef(null);
  const inputRef = useRef(null);
  const listRef = useRef(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return undefined;
    if (!dialog.open) {
      dialog.setAttribute('closedby', 'any');
      dialog.showModal();
    }
    const timer = window.setTimeout(() => inputRef.current?.focus(), 20);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog || 'closedBy' in HTMLDialogElement.prototype) return undefined;

    const isOutside = (e) => {
      const r = dialog.getBoundingClientRect();
      return e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom;
    };

    let pressedOutside = false;
    const onDown = (e) => {
      pressedOutside = isOutside(e);
    };
    const onUp = (e) => {
      if (pressedOutside && isOutside(e)) onClose();
      pressedOutside = false;
    };
    dialog.addEventListener('pointerdown', onDown);
    dialog.addEventListener('pointerup', onUp);
    return () => {
      dialog.removeEventListener('pointerdown', onDown);
      dialog.removeEventListener('pointerup', onUp);
    };
  }, [onClose]);

  const q = foldText(query);

  const matchedTeams = useMemo(() => {
    if (!q) return teams.slice(0, 4);
    return teams
      .filter((t) => foldText(t.name).includes(q) || foldText(t.short).includes(q) || foldText(t.abbr).includes(q))
      .slice(0, 5);
  }, [teams, q]);

  const matchedPlayers = useMemo(() => {
    if (!q) return players.slice(0, 6);
    const terms = q.split(/\s+/).filter(Boolean);
    return players
      .filter((p) => {
        const hay = foldText(`${p.name} ${p.teamName || ''}`);
        return terms.every((term) => hay.includes(term));
      })
      .sort((a, b) => {
        const aStarts = foldText(a.name).startsWith(q) ? 0 : 1;
        const bStarts = foldText(b.name).startsWith(q) ? 0 : 1;
        return aStarts - bStarts;
      })
      .slice(0, 8);
  }, [players, q]);

  const items = useMemo(() => {
    const combined = [];
    matchedTeams.forEach((team) => combined.push({ type: 'team', team }));
    matchedPlayers.forEach((player) => combined.push({ type: 'player', player }));
    return combined;
  }, [matchedTeams, matchedPlayers]);

  const safeIndex = Math.min(selectedIndex, Math.max(0, items.length - 1));

  useEffect(() => {
    if (!listRef.current) return;
    const activeEl = listRef.current.querySelector(`[data-index="${safeIndex}"]`);
    if (activeEl) activeEl.scrollIntoView({ block: 'nearest' });
  }, [safeIndex]);

  const selectItem = (item) => {
    if (!item) return;
    if (item.type === 'team') {
      onSelectTeam(item.team.id);
    } else {
      onSelectPlayer(item.player.id);
    }
    onClose();
  };

  const handleKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (items.length > 0 ? (prev + 1) % items.length : 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (items.length > 0 ? (prev - 1 + items.length) % items.length : 0));
    } else if (e.key === 'Enter' && items[safeIndex]) {
      e.preventDefault();
      selectItem(items[safeIndex]);
    }
  };

  return (
    <dialog
      ref={dialogRef}
      onClose={onClose}
      aria-label="Hızlı arama"
      className="modal-dialog w-full max-w-xl p-0 bg-background-primary border border-border rounded-md shadow-md overflow-hidden"
    >
      <div className="flex flex-col max-h-[80vh]" onKeyDown={handleKeyDown}>
        <div className="flex items-center gap-3 px-4 py-3 border-b border-border bg-background-primary">
          <Search className="w-4 h-4 text-text-tertiary shrink-0" strokeWidth={1.5} aria-hidden="true" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            placeholder={`${competitionName}: takım veya oyuncu ara...`}
            className="flex-1 bg-transparent text-sm text-text-primary placeholder:text-text-muted outline-none"
          />
          {query && (
            <button
              type="button"
              onClick={() => {
                setQuery('');
                setSelectedIndex(0);
                inputRef.current?.focus();
              }}
              className="p-1 text-text-tertiary hover:text-text-primary rounded transition-colors cursor-pointer"
              aria-label="Aramayı temizle"
            >
              <X className="w-4 h-4" strokeWidth={1.5} aria-hidden="true" />
            </button>
          )}
          <kbd className="hidden sm:inline-block rounded-sm border border-border bg-background-tertiary px-1.5 py-0.5 text-xs font-mono text-text-muted">
            ESC
          </kbd>
        </div>

        <div ref={listRef} className="overflow-y-auto p-2 space-y-3 bg-background-primary">
          {items.length === 0 ? (
            <p className="py-10 text-center text-sm text-text-secondary">
              Eşleşen takım veya oyuncu bulunamadı.
            </p>
          ) : (
            <>
              {matchedTeams.length > 0 && (
                <section>
                  <p className="px-2.5 py-1 text-xs font-medium text-text-tertiary">Takımlar</p>
                  <div className="space-y-0.5">
                    {matchedTeams.map((team, idx) => {
                      const active = idx === safeIndex;
                      return (
                        <button
                          key={team.id}
                          type="button"
                          data-index={idx}
                          onMouseEnter={() => setSelectedIndex(idx)}
                          onClick={() => selectItem({ type: 'team', team })}
                          className={`w-full flex items-center justify-between gap-3 px-2.5 py-2 rounded text-left text-sm transition-colors cursor-pointer ${
                            active ? 'bg-background-tertiary text-text-primary' : 'text-text-primary hover:bg-background-tertiary/60'
                          }`}
                        >
                          <div className="flex items-center gap-2.5 min-w-0">
                            <img
                              src={team.badge}
                              alt=""
                              className="w-6 h-6 object-contain shrink-0"
                              onError={handleTeamBadgeError}
                            />
                            <span className="font-medium truncate">{team.name}</span>
                          </div>
                          <span className="inline-flex items-center gap-1 text-xs text-text-muted shrink-0">
                            <Shield className="w-3.5 h-3.5" strokeWidth={1.5} aria-hidden="true" />
                            <span>Kulüp</span>
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </section>
              )}

              {matchedPlayers.length > 0 && (
                <section>
                  <p className="px-2.5 py-1 text-xs font-medium text-text-tertiary">Oyuncular</p>
                  <div className="space-y-0.5">
                    {matchedPlayers.map((player, i) => {
                      const idx = matchedTeams.length + i;
                      const active = idx === safeIndex;
                      const team = player.teamId ? getTeam(player.teamId, player.teamName) : null;
                      return (
                        <button
                          key={player.id}
                          type="button"
                          data-index={idx}
                          onMouseEnter={() => setSelectedIndex(idx)}
                          onClick={() => selectItem({ type: 'player', player })}
                          className={`w-full flex items-center justify-between gap-3 px-2.5 py-2 rounded text-left text-sm transition-colors cursor-pointer ${
                            active ? 'bg-background-tertiary text-text-primary' : 'text-text-primary hover:bg-background-tertiary/60'
                          }`}
                        >
                          <div className="flex items-center gap-2.5 min-w-0">
                            <PlayerAvatar player={player} size="sm" shape="circle" className="w-7 h-7" />
                            <div className="min-w-0">
                              <p className="font-medium truncate">{player.name}</p>
                              <p className="text-xs text-text-secondary truncate">
                                {[player.teamName, player.position].filter(Boolean).join(' · ')}
                              </p>
                            </div>
                          </div>
                          {team?.badge && (
                            <img
                              src={team.badge}
                              alt=""
                              className="w-5 h-5 object-contain shrink-0"
                              onError={handleTeamBadgeError}
                            />
                          )}
                        </button>
                      );
                    })}
                  </div>
                </section>
              )}
            </>
          )}
        </div>

        <div className="flex items-center justify-between px-4 py-2 border-t border-border-light bg-background-secondary text-xs text-text-muted">
          <span>Gezinmek için ok tuşları</span>
          <span className="inline-flex items-center gap-1">
            <CornerDownLeft className="w-3.5 h-3.5" strokeWidth={1.5} aria-hidden="true" />
            <span>Seç</span>
          </span>
        </div>
      </div>
    </dialog>
  );
}
