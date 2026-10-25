import { getJson, getJsonChecked, requestJson, withQuery } from './apiClient';
import { registerLogosFrom } from '../data/teams';

export async function getTeamStaff(season, teamId, options, competition = null) {
  const { response, data } = await requestJson(withQuery('/api/teams/staff', { season, team_id: teamId, ...(competition ? { competition } : {}) }), options);
  return response.ok ? data : null;
}
export async function getTeamManagers(season, competition = null) {
  const { response, data } = await requestJson(withQuery('/api/teams/staff', { season, ...(competition ? { competition } : {}) }));
  return response.ok ? data : { managers: {} };
}
export const getTeamProfile = (teamId, season, options, competition = null) =>
  getJson(withQuery('/api/teams/profile', { team_id: teamId, season, ...(competition ? { competition } : {}) }), options).then(registerLogosFrom);
export const getManagerChanges = (season, options) => getJsonChecked(withQuery('/api/teams/manager-changes', { season }), options, 'Manager history request failed');
export const getTeamScenarios = (teamId, season, options) => getJsonChecked(withQuery('/api/teams/scenarios', { team_id: teamId, season }), options, 'Score-state profile request failed');
export const getTeamTactics = (teamId, season, options) => getJsonChecked(withQuery('/api/teams/tactics', { team_id: teamId, season }), options, 'Tactical profile request failed');
export const getTeamAttackingLeaders = (teamId, season, options) => getJsonChecked(withQuery('/api/teams/attacking-leaders', { team_id: teamId, season }), options, 'Attacking leaders request failed');
export const getManagerPerformance = (teamId, managerName, options) => getJsonChecked(withQuery('/api/teams/manager-performance', {
  team_id: teamId,
  season: 'all',
  manager_name: managerName,
}), options, 'Manager performance request failed');
export const getTeamTransfers = (teamId, season) => getJsonChecked(withQuery(`/api/teams/${teamId}/transfers`, { season }));
