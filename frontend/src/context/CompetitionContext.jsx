import React, { createContext, useContext, useState, useEffect, useMemo } from 'react';

export const COMPETITIONS = {
  premier_league: {
    key: 'premier_league',
    logo: '/competitions/premier_league.svg',
    id: 39,
    name: 'Premier League',
    shortName: 'Premier League',
    abbr: 'EPL',
    country: 'İngiltere',
  },
  champions_league: {
    key: 'champions_league',
    logo: '/competitions/champions_league.svg',
    id: 2,
    name: 'UEFA Champions League',
    shortName: 'Champions League',
    abbr: 'UCL',
    country: 'Avrupa',
  },
  europa_league: {
    key: 'europa_league',
    logo: '/competitions/europa_league.svg',
    id: 3,
    name: 'UEFA Europa League',
    shortName: 'Europa League',
    abbr: 'UEL',
    country: 'Avrupa',
  },
};

const CompetitionContext = createContext(null);

export function CompetitionProvider({ children }) {
  const [competitionKey, setCompetitionKey] = useState(() => {
    try {
      return localStorage.getItem('plm_competition') || 'premier_league';
    } catch {
      return 'premier_league';
    }
  });

  const activeCompetition = useMemo(() => {
    return COMPETITIONS[competitionKey] || COMPETITIONS.premier_league;
  }, [competitionKey]);

  useEffect(() => {
    document.documentElement.dataset.competition = activeCompetition.key;
  }, [activeCompetition]);

  const selectCompetition = (key) => {
    if (COMPETITIONS[key]) {
      setCompetitionKey(key);
      try {
        localStorage.setItem('plm_competition', key);
      } catch {}
    }
  };

  const value = {
    competitionKey,
    activeCompetition,
    selectCompetition,
    isPremierLeague: competitionKey === 'premier_league',
    isChampionsLeague: competitionKey === 'champions_league',
    isEuropaLeague: competitionKey === 'europa_league',
    competitionsList: Object.values(COMPETITIONS),
  };

  return (
    <CompetitionContext.Provider value={value}>
      {children}
    </CompetitionContext.Provider>
  );
}

export function useCompetition() {
  const context = useContext(CompetitionContext);
  if (!context) {
    throw new Error('useCompetition must be used within a CompetitionProvider');
  }
  return context;
}
