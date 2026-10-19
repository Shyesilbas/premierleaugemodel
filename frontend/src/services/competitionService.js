import { getJson, requestJson, withQuery } from './apiClient';

export const getGroupedFixtures = (season) => getJson(withQuery('/api/fixtures/grouped', { season }));
export const getStandings = (season) => getJson(withQuery('/api/standings', { season }));
export const getTeams = (season) => getJson(withQuery('/api/teams', { season }));

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

export async function startSeasonSync(season, kind = 'matches') {
  const { response, data } = await requestJson(withQuery('/api/admin/sync-season', { season, kind }), { method: 'POST', headers: adminHeaders() });
  if (!response.ok) throw new Error(data.detail || data.message || 'Güncelleme başlatılamadı.');
  return data;
}
