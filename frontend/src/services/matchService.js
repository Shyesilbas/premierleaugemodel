import { getJson, requestJson, withQuery } from './apiClient';

export const getMatchDetails = (matchId) => getJson(`/api/match/${matchId}/details`);
export const getMatchOdds = (matchId) => getJson(`/api/match/${matchId}/odds`);
export async function getRecentMatchForm(matchId) {
  const { response, data } = await requestJson(`/api/match/${matchId}/recent-form`);
  return response.ok ? data : { form: {} };
}

export function getMatchPrediction(homeId, awayId, matchId, season, competition) {
  return getJson(withQuery('/api/predict', {
    home_id: homeId,
    away_id: awayId,
    match_id: matchId,
    season: season && season !== '2026_27' ? season : undefined,
    competition: competition && competition !== 'premier_league' ? competition : undefined,
  }));
}
