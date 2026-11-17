import { invalidateApiCache, loadApi, loadApiFresh, requestJson, withQuery } from './apiClient';
import { registerLogosFrom } from '../data/teams';

export const getCompetitions = () => loadApi('/api/competitions');
export const getGroupedFixtures = (season, competition = null) =>
  loadApiFresh(withQuery('/api/fixtures/grouped', { season, ...(competition ? { competition } : {}) })).then(registerLogosFrom);
export const getKnockoutBracket = (season, competition) =>
  loadApiFresh(withQuery('/api/fixtures/bracket', { season, competition })).then(registerLogosFrom);
export const getStandings = (season, competition = null) =>
  loadApiFresh(withQuery('/api/standings', { season, ...(competition ? { competition } : {}) })).then(registerLogosFrom);
export const getTeams = (season, competition = null) =>
  loadApiFresh(withQuery('/api/teams', { season, ...(competition ? { competition } : {}) })).then(registerLogosFrom);
export const getPendingMatches = (season, competition = null) =>
  loadApiFresh(withQuery('/api/fixtures/pending', { season, ...(competition ? { competition } : {}) }));

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
  const { response, data } = await requestJson('/api/admin/sync-season', { cache: 'no-store', headers: adminHeaders() });
  if (!response.ok) throw new Error('Güncelleme durumu alınamadı.');
  if (data?.status === 'completed') invalidateApiCache();
  return data;
}

export async function startSeasonSync(season, kind = 'matches', competition = 'premier_league') {
  const { response, data } = await requestJson(
    withQuery('/api/admin/sync-season', { season, kind, competition }),
    { method: 'POST', headers: adminHeaders() },
  );
  if (!response.ok) throw new Error(data.detail || data.message || 'Güncelleme başlatılamadı.');
  return data;
}

export async function startMatchBatchRefresh(season, competition = 'premier_league', matchIds = null) {
  const { response, data } = await requestJson(
    withQuery('/api/admin/matches/refresh-batch', { season, competition }),
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...adminHeaders() },
      body: JSON.stringify(matchIds ? { match_ids: matchIds } : {}),
    },
  );
  if (!response.ok) throw new Error(data.detail || data.message || 'Toplu maç güncellemesi başlatılamadı.');
  return data;
}

export async function getMatchBatchRefreshStatus() {
  const { response, data } = await requestJson('/api/admin/matches/refresh-batch', { cache: 'no-store', headers: adminHeaders() });
  if (!response.ok) throw new Error('Toplu güncelleme durumu alınamadı.');
  if (data?.status === 'completed') invalidateApiCache();
  return data;
}

export async function startSingleMatchRefresh(matchId, season, competition = 'premier_league') {
  const { response, data } = await requestJson(
    withQuery(`/api/admin/matches/${matchId}/refresh`, { season, competition }),
    { method: 'POST', headers: adminHeaders() },
  );
  if (!response.ok) throw new Error(data.detail || data.message || 'Maç verisi yenilenemedi.');
  return data;
}

export async function getSingleMatchRefreshStatus(matchId) {
  const { response, data } = await requestJson(`/api/admin/matches/${matchId}/refresh`, { cache: 'no-store', headers: adminHeaders() });
  if (!response.ok) throw new Error('Maç yenileme durumu alınamadı.');
  if (data?.status === 'completed') invalidateApiCache();
  return data;
}
