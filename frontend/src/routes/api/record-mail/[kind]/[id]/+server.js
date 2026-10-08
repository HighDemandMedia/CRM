import { json } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';

/** @param {any} event */
async function forward({ cookies, params, url, request }) {
  const headers = { 'Cache-Control': 'private, no-store' };
  if (!['contact', 'company'].includes(params.kind) || !/^[0-9a-f-]{36}$/i.test(params.id))
    return json({ error: 'Invalid record.' }, { status: 400, headers });
  const query = new URLSearchParams();
  for (const key of ['offset', 'direction', 'q', 'contact', 'thread']) {
    if (url.searchParams.has(key)) query.set(key, url.searchParams.get(key));
  }
  try {
    const result = await apiRequest(
      `/integrations/google/records/${params.kind}/${params.id}/mail/?${query}`,
      { method: request.method },
      { cookies }
    );
    return json(result, { headers });
  } catch (error) {
    const status = [400, 401, 403, 404, 429].includes(error?.status) ? error.status : 503;
    return json({ error: 'Could not load emails. Please try again.' }, { status, headers });
  }
}
export const GET = forward;
export const POST = forward;
