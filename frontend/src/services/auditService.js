import { getJson, withQuery } from './apiClient';

export const getModelAudit = (season, force = false) => getJson(withQuery('/api/model-audit', {
  season,
  force_recalc: force ? 'true' : undefined,
}));
