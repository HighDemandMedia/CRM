import { json } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';
import { readableError } from '$lib/server/v2/form-errors.js';

const message = (err, fallback) => Array.isArray(err.body) ? err.body.join(' ') : readableError(err, fallback);

export async function GET({params, url, cookies}) {
  const query = new URLSearchParams();
  for (const key of ['q', 'secondary']) if (url.searchParams.has(key)) query.set(key, url.searchParams.get(key));
  try {
    return json(await apiRequest(`/contacts/${params.id}/merge/?${query}`, {}, {cookies}), {headers: {'cache-control':'no-store'}});
  } catch (err) {return json({error:message(err, 'Could not compare contacts.')}, {status:err.status || 400});}
}
export async function POST({params, request, cookies}) {
  try {
    return json(await apiRequest(`/contacts/${params.id}/merge/`, {method:'POST', body:await request.json()}, {cookies}));
  } catch (err) {return json({error:message(err, 'Could not merge contacts.')}, {status:err.status || 400});}
}
