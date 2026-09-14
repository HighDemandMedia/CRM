import { json } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';
export async function GET({ cookies, url }) {
  const query = new URLSearchParams({ search: url.searchParams.get('search') ?? '' });
  return json(await apiRequest(`/sales-appointments/attendees/?${query}`, {}, { cookies }), {
    headers: { 'Cache-Control': 'private, no-store' }
  });
}
