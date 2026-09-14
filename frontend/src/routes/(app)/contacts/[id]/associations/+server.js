import { json } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';
export async function GET({ cookies, params, url }) {
  const query = new URLSearchParams({
    kind: url.searchParams.get('kind') ?? '',
    search: url.searchParams.get('search') ?? ''
  });
  return json(await apiRequest(`/contacts/${params.id}/associations/?${query}`, {}, { cookies }), {
    headers: { 'Cache-Control': 'private, no-store' }
  });
}
