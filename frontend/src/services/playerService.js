import { getJson, getJsonChecked, withQuery } from './apiClient';
import { registerLogosFrom } from '../data/teams';

export const searchPlayers = (params) => getJson(withQuery('/api/players', params));
export const getPlayerProfile = (playerId, season, competition = null) => 
  getJson(withQuery('/api/players/profile', { player_id: playerId, season, ...(competition ? { competition } : {}) })).then(registerLogosFrom);
export const getPlayerMarketValueHistory = (playerId, params) => getJsonChecked(withQuery(`/api/players/${playerId}/market-value-history`, params));
