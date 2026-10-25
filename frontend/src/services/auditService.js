import { getJson, withQuery } from './apiClient';

export const getModelAudit = (season, force = false, competition = null) => getJson(withQuery('/api/model-audit', {
  season,
  force_recalc: force ? 'true' : undefined,
  ...(competition ? { competition } : {})
}));
