import { getJsonChecked, withQuery } from './apiClient';

export const getLeagueStats = (season, scope, gameweek) => getJsonChecked(
  withQuery('/api/stats', { season, scope, gameweek: scope === 'week' ? gameweek : undefined }),
  undefined,
  'İstatistikler yüklenemedi',
);
