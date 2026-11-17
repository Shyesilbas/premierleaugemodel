import React, { useState, useEffect, useMemo } from 'react';
import { getTeams } from '../services/competitionService';
import { COMPETITIONS, CompetitionContext } from './competitionState';

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
    hasAudit: activeCompetition.hasAudit,
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
