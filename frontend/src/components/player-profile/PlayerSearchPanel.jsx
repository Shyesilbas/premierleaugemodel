import React, { useEffect, useMemo, useRef, useState } from 'react';
import { ArrowLeft, ChevronRight, Search, X } from 'lucide-react';
import { getTeam } from '../../data/teams';
import { handleTeamBadgeError } from '../../utils/imageFallbacks';
import PlayerAvatar from '../PlayerAvatar';
import { Button } from '../common/Button';
import { Card } from '../common/Card';

function foldText(s) {
  return String(s || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/ı/g, 'i')
    .replace(/İ/g, 'i')
    .toLowerCase()
    .trim();
}

const POSITION_SHORT = {
  G: 'KL',
  GK: 'KL',
  D: 'DEF',
  DEF: 'DEF',
  M: 'ORT',
  MID: 'ORT',
  F: 'FOR',
  FWD: 'FOR',
};

export default function PlayerSearchPanel({
  searchTerm,
  onSearchChange,
  players = [],
  directoryPlayers = [],
  selectedPlayerId,
  onSelectPlayer,
  onBackToDiscovery,
}) {
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const containerRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    const handleOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleOutside);
    return () => document.removeEventListener('mousedown', handleOutside);
  }, []);

  const suggestions = useMemo(() => {
    const q = foldText(searchTerm);
    if (!q) return [];
    const pool = directoryPlayers.length > 0 ? directoryPlayers : players;
    const terms = q.split(/\s+/).filter(Boolean);
    const localMatches = pool
      .filter((p) => {
        const hay = foldText(`${p.name} ${p.teamName || ''}`);
        return terms.every((t) => hay.includes(t));
      })
      .sort((a, b) => {
        const aStarts = foldText(a.name).startsWith(q) ? 0 : 1;
        const bStarts = foldText(b.name).startsWith(q) ? 0 : 1;
        if (aStarts !== bStarts) return aStarts - bStarts;
        return (Number(b.market_value_eur || 0) - Number(a.market_value_eur || 0));
      });
    const combined = localMatches.length > 0 ? localMatches : players;
    return combined.slice(0, 10);
  }, [searchTerm, directoryPlayers, players]);

  const safeIndex = Math.min(activeIndex, Math.max(0, suggestions.length - 1));

  const choosePlayer = (player) => {
    if (!player) return;
    setOpen(false);
    onSearchChange('');
    onSelectPlayer(player.id);
  };

  const handleKeyDown = (e) => {
    if (!open || suggestions.length === 0) {
      if (e.key === 'Escape') {
        onSearchChange('');
        setOpen(false);
      }
      return;
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIndex((prev) => (prev + 1) % suggestions.length);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIndex((prev) => (prev - 1 + suggestions.length) % suggestions.length);
    } else if (e.key === 'Enter' && suggestions[safeIndex]) {
      e.preventDefault();
      choosePlayer(suggestions[safeIndex]);
    } else if (e.key === 'Escape') {
      setOpen(false);
    }
  };

  return (
    <Card padding="sm" className="relative z-20">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        {selectedPlayerId != null && onBackToDiscovery && (
          <Button
            variant="secondary"
            size="md"
            leftIcon={<ArrowLeft className="h-4 w-4" strokeWidth={1.5} aria-hidden="true" />}
            onClick={onBackToDiscovery}
            className="shrink-0"
          >
            Tüm oyuncular
          </Button>
        )}

        <div ref={containerRef} className="relative flex-1 min-w-0">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-tertiary" strokeWidth={1.5} aria-hidden="true" />
          <input
            ref={inputRef}
            type="text"
            value={searchTerm}
            onFocus={() => setOpen(true)}
            onChange={(e) => {
              onSearchChange(e.target.value);
              setOpen(true);
              setActiveIndex(0);
            }}
            onKeyDown={handleKeyDown}
            placeholder="Oyuncu veya kulüp adı ile ara..."
            aria-label="Oyuncu ara"
            aria-expanded={Boolean(open && searchTerm.trim() && suggestions.length > 0)}
            className="h-9 w-full rounded border border-border bg-background-primary pl-9 pr-9 text-sm text-text-primary placeholder:text-text-muted outline-none transition-colors hover:border-card-border-hover focus:border-border-focus"
          />
          {searchTerm && (
            <button
              type="button"
              onClick={() => {
                onSearchChange('');
                setOpen(false);
                inputRef.current?.focus();
              }}
              aria-label="Aramayı temizle"
              className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded p-1 text-text-tertiary hover:text-text-primary transition-colors cursor-pointer"
            >
              <X className="h-4 w-4" strokeWidth={1.5} aria-hidden="true" />
            </button>
          )}

          {open && searchTerm.trim() && (
            <div className="absolute left-0 right-0 top-full z-30 mt-1.5 max-h-80 overflow-y-auto rounded border border-border bg-background-primary shadow-md">
              {suggestions.length === 0 ? (
                <p className="px-4 py-6 text-center text-xs text-text-secondary">
                  Eşleşen oyuncu bulunamadı.
                </p>
              ) : (
                <ul className="divide-y divide-border-light py-1" role="listbox">
                  {suggestions.map((player, idx) => {
                    const team = player.teamId ? getTeam(player.teamId, player.teamName) : null;
                    const active = idx === safeIndex;
                    const selected = String(player.id) === String(selectedPlayerId);
                    return (
                      <li key={player.id} role="option" aria-selected={selected}>
                        <button
                          type="button"
                          onMouseEnter={() => setActiveIndex(idx)}
                          onClick={() => choosePlayer(player)}
                          className={`flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm transition-colors cursor-pointer ${
                            active ? 'bg-background-tertiary text-text-primary' : 'text-text-primary hover:bg-background-secondary'
                          }`}
                        >
                          <div className="flex min-w-0 items-center gap-2.5">
                            <PlayerAvatar player={player} size="sm" shape="circle" className="w-7 h-7 shrink-0" />
                            <div className="min-w-0">
                              <div className="flex items-center gap-1.5">
                                <span className="truncate font-medium">{player.name}</span>
                                {player.position && (
                                  <span className="rounded-sm border border-border bg-background-secondary px-1.5 py-0.5 text-xs text-text-secondary">
                                    {POSITION_SHORT[player.position] || player.position}
                                  </span>
                                )}
                              </div>
                              <div className="flex items-center gap-1.5 text-xs text-text-secondary truncate">
                                {team?.badge && (
                                  <img
                                    src={team.badge}
                                    alt=""
                                    className="h-3.5 w-3.5 shrink-0 object-contain"
                                    onError={handleTeamBadgeError}
                                  />
                                )}
                                <span className="truncate">{team?.short || player.teamName || '—'}</span>
                                {player.market_value_formatted && (
                                  <>
                                    <span aria-hidden="true">·</span>
                                    <span className="tabular-nums text-text-tertiary">{player.market_value_formatted}</span>
                                  </>
                                )}
                              </div>
                            </div>
                          </div>
                          <ChevronRight className="h-4 w-4 shrink-0 text-text-muted" strokeWidth={1.5} aria-hidden="true" />
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}
