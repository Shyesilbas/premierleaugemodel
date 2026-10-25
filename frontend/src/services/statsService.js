import { getJsonChecked, withQuery } from './apiClient';

export const getLeagueStats = (season, scope, gameweek, competition = null) => getJsonChecked(
  withQuery('/api/stats', {
    season,
    scope,
    gameweek: scope === 'week' ? gameweek : undefined,
    ...(competition ? { competition } : {})
  }),
  undefined,
  'İstatistikler yüklenemedi',
);
