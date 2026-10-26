import React, { createContext, useContext, useState, useEffect, useMemo } from 'react';
import { getTeams } from '../services/competitionService';

export const COMPETITIONS = {
  premier_league: {
    key: 'premier_league',
    logo: '/competitions/premier_league.svg',
    id: 39,
    name: 'Premier League',
    shortName: 'Premier League',
    abbr: 'EPL',
    country: 'İngiltere',
    kind: 'league',
    richData: true,
    hasModel: true,
    syncKinds: ['matches', 'referees', 'lineups'],
  },
  la_liga: {
    key: 'la_liga',
    logo: '/competitions/la_liga.png',
    id: 140,
    name: 'LaLiga',
    shortName: 'LaLiga',
    abbr: 'LL',
    country: 'İspanya',
    kind: 'league',
    richData: false,
    hasModel: true,
    syncKinds: ['matches'],
  },
  champions_league: {
    key: 'champions_league',
    logo: '/competitions/champions_league.svg',
    id: 2,
    name: 'UEFA Champions League',
    shortName: 'Champions League',
    abbr: 'UCL',
    country: 'Avrupa',
    kind: 'cup',
    richData: false,
    hasModel: false,
    syncKinds: ['matches'],
  },
  europa_league: {
    key: 'europa_league',
    logo: '/competitions/europa_league.svg',
    id: 3,
    name: 'UEFA Europa League',
    shortName: 'Europa League',
    abbr: 'UEL',
    country: 'Avrupa',
    kind: 'cup',
    richData: false,
    hasModel: false,
    syncKinds: ['matches'],
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

  // Club badges are registered from the responses that carry them. Load every non-Premier-League competition's clubs up
  // front, so a page opened directly (statistics, a lineup, a player) still knows each club's badge.
  useEffect(() => {
    Object.values(COMPETITIONS)
      .filter(competition => !competition.richData)
      .forEach(competition => { getTeams('all', competition.key).catch(() => {}); });
  }, []);

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
    // Capabilities drive the tabs, so a competition added to COMPETITIONS gets the same pages without more checks.
    isCup: activeCompetition.kind === 'cup',
    isLeague: activeCompetition.kind === 'league',
    hasModel: activeCompetition.hasModel,
    hasRichData: activeCompetition.richData,
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
