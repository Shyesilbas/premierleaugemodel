/** Shared JSON transport for the feature API modules. */
export async function getJson(path, options) {
  const response = await fetch(path, options);
  return response.json();
}

export async function getJsonChecked(path, options, errorMessage) {
  const response = await fetch(path, options);
  if (!response.ok) throw new Error(errorMessage || `HTTP error ${response.status}`);
  return response.json();
}

export async function requestJson(path, options) {
  const response = await fetch(path, options);
  const data = await response.json();
  return { response, data };
}

export function withQuery(path, params) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') query.set(key, value);
  });
  const search = query.toString();
  return search ? `${path}?${search}` : path;
}
