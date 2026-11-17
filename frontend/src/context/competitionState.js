import { createContext, useContext } from 'react';

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
    hasAudit: true,
    syncKinds: ['matches', 'referees', 'lineups'],
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
    hasAudit: false,
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
    hasAudit: false,
    syncKinds: ['matches'],
  },
};

export const CompetitionContext = createContext(null);

export function useCompetition() {
  const context = useContext(CompetitionContext);
  if (!context) {
    throw new Error('useCompetition must be used within a CompetitionProvider');
  }
  return context;
}
