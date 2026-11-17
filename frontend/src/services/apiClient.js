/**
 * Shared JSON transport and in-memory request deduplication/ETag cache
 * for all frontend service modules.
 */

const apiCache = new Map();

export function withQuery(path, params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') query.set(key, String(value));
  });
  const search = query.toString();
  return search ? `${path}?${search}` : path;
}

export async function getJson(path, options) {
  const response = await fetch(path, options);
  return response.json();
}

export async function getJsonChecked(path, options, errorMessage) {
  const response = await fetch(path, options);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(errorMessage || body?.detail || body?.message || `HTTP error ${response.status}`);
  }
  return body;
}

export async function requestJson(path, options) {
  const response = await fetch(path, options);
  const data = await response.json().catch(() => ({}));
  return { response, data };
}

/**
 * Deduplicated GET per session; concurrent and later callers share the resolved promise.
 * Rejects evict the key so a user retry can recover cleanly.
 */
export async function loadApi(path, options) {
  if (options?.signal) {
    return getJsonChecked(path, options);
  }
  if (!apiCache.has(path)) {
    const req = getJsonChecked(path, options).catch((error) => {
      apiCache.delete(path);
      throw error;
    });
    apiCache.set(path, req);
  }
  return apiCache.get(path);
}

/**
 * Always validates with the backend (`Cache-Control: no-cache` + server ETag).
 * Unchanged resources return a fast 304 Not Modified without re-downloading JSON;
 * refreshed fixtures/matches immediately deliver updated data.
 */
export async function loadApiFresh(path, options) {
  return getJsonChecked(path, { cache: 'no-cache', ...options });
}

export async function postApi(path, body, options = {}) {
  return getJsonChecked(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    body: body === undefined ? undefined : JSON.stringify(body),
    ...options,
  });
}

export function invalidateApiCache(prefix = '') {
  if (!prefix) {
    apiCache.clear();
    return;
  }
  for (const key of apiCache.keys()) {
    if (key.startsWith(prefix)) apiCache.delete(key);
  }
}
