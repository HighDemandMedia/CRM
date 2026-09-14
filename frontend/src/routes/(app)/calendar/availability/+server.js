import { json } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';
export async function GET({ cookies, url }) {
  const query = new URLSearchParams();
  for (const key of ['host', 'start', 'end', 'exclude'])
    if (url.searchParams.has(key)) query.set(key, url.searchParams.get(key));
  return json(await apiRequest(`/sales-appointments/availability/?${query}`, {}, { cookies }), {
    headers: { 'Cache-Control': 'private, no-store' }
  });
}
