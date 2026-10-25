import { getJson, withQuery } from './apiClient';
import { registerLogosFrom } from '../data/teams';

export const getReferees = (season, competition = null) => 
  getJson(withQuery('/api/referees', { season, ...(competition ? { competition } : {}) }));
export const getRefereeDetails = (name, season, competition = null) => 
  getJson(withQuery(`/api/referees/${encodeURIComponent(name)}`, { season, ...(competition ? { competition } : {}) })).then(registerLogosFrom);
