import React from 'react';
import { useCompetition } from '../../context/CompetitionContext';

// One logo button per competition. The chosen one gets an accent outline on a white tile, so the dark logo stays readable.
export default function CompetitionSelector({ compact = false }) {
  const { competitionKey, selectCompetition, competitionsList } = useCompetition();

  return (
    <div
      role="tablist"
      aria-label="Turnuva Seçici"
      className={`inline-flex items-center gap-1 p-1 bg-background-tertiary border border-border rounded ${
        compact ? 'w-full justify-between' : ''
      }`}
    >
      {competitionsList.map((comp) => {
        const isSelected = comp.key === competitionKey;
        return (
          <button
            key={comp.key}
            type="button"
            role="tab"
            aria-selected={isSelected}
            aria-label={comp.name}
            title={comp.name}
            onClick={() => selectCompetition(comp.key)}
            className={`h-10 px-3 rounded border flex items-center justify-center transition-colors duration-150 cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-border-focus ${
              compact ? 'flex-1' : ''
            } ${
              isSelected
                ? 'bg-background-primary border-accent'
                : 'border-transparent opacity-60 hover:opacity-100 hover:bg-background-secondary'
            }`}
          >
            <img src={comp.logo} alt="" className="h-7 w-auto object-contain" />
          </button>
        );
      })}
    </div>
  );
}
