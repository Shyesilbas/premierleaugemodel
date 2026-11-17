import { loadApi, withQuery } from './apiClient';
import { registerLogosFrom } from '../data/teams';

export const searchPlayers = (params) => loadApi(withQuery('/api/players', params));
export const getPlayerProfile = (playerId, season, competition = null) =>
  loadApi(withQuery('/api/players/profile', { player_id: playerId, season, ...(competition ? { competition } : {}) })).then(registerLogosFrom);
export const getPlayerMarketValueHistory = (playerId, params) =>
  loadApi(withQuery(`/api/players/${playerId}/market-value-history`, params));
export const getPlayersCompareData = (competition = null) =>
  loadApi(withQuery('/api/players/compare-data', competition ? { competition } : {})).then(registerLogosFrom);
