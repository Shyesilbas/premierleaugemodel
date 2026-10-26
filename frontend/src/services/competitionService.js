import { getJson, requestJson, withQuery } from './apiClient';
import { registerLogosFrom } from '../data/teams';

export const getCompetitions = () => getJson('/api/competitions');
export const getGroupedFixtures = (season, competition = null) =>
  getJson(withQuery('/api/fixtures/grouped', { season, ...(competition ? { competition } : {}) })).then(registerLogosFrom);
export const getKnockoutBracket = (season, competition) =>
  getJson(withQuery('/api/fixtures/bracket', { season, competition })).then(registerLogosFrom);
export const getStandings = (season, competition = null) =>
  getJson(withQuery('/api/standings', { season, ...(competition ? { competition } : {}) })).then(registerLogosFrom);
export const getTeams = (season, competition = null) =>
  getJson(withQuery('/api/teams', { season, ...(competition ? { competition } : {}) })).then(registerLogosFrom);

// Admin routes need the token only when the server sets PLM_ADMIN_TOKEN; store it once with
// localStorage.setItem('plm_admin_token', '<token>').
const adminHeaders = () => {
  try {
    const token = localStorage.getItem('plm_admin_token');
    return token ? { 'X-Admin-Token': token } : {};
  } catch {
    return {};
  }
};

export async function getSeasonSyncStatus() {
  const { response, data } = await requestJson('/api/admin/sync-season', { headers: adminHeaders() });
  if (!response.ok) throw new Error('Güncelleme durumu alınamadı.');
  return data;
}

export async function startSeasonSync(season, kind = 'matches', competition = 'premier_league') {
  const { response, data } = await requestJson(withQuery('/api/admin/sync-season', { season, kind, competition }), { method: 'POST', headers: adminHeaders() });
  if (!response.ok) throw new Error(data.detail || data.message || 'Güncelleme başlatılamadı.');
  return data;
}
