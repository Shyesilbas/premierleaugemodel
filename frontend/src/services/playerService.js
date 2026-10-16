import { getJson, getJsonChecked, withQuery } from './apiClient';

export const searchPlayers = (params) => getJson(withQuery('/api/players', params));
export const getPlayerProfile = (playerId, season) => getJson(withQuery('/api/players/profile', { player_id: playerId, season }));
export const getPlayerMarketValueHistory = (playerId, params) => getJsonChecked(withQuery(`/api/players/${playerId}/market-value-history`, params));
