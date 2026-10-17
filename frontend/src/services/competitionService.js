import { getJson, requestJson, withQuery } from './apiClient';

export const getGroupedFixtures = (season) => getJson(withQuery('/api/fixtures/grouped', { season }));
export const getStandings = (season) => getJson(withQuery('/api/standings', { season }));
export const getTeams = (season) => getJson(withQuery('/api/teams', { season }));

export async function getSeasonSyncStatus() {
  const { response, data } = await requestJson('/api/admin/sync-season');
  if (!response.ok) throw new Error('Güncelleme durumu alınamadı.');
  return data;
}

export async function startSeasonSync(season, kind = 'matches') {
  const { response, data } = await requestJson(withQuery('/api/admin/sync-season', { season, kind }), { method: 'POST' });
  if (!response.ok) throw new Error(data.detail || data.message || 'Güncelleme başlatılamadı.');
  return data;
}
