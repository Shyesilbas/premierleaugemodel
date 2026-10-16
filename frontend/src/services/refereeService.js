import { getJson, withQuery } from './apiClient';

export const getReferees = (season) => getJson(withQuery('/api/referees', { season }));
export const getRefereeDetails = (name, season) => getJson(withQuery(`/api/referees/${encodeURIComponent(name)}`, { season }));
