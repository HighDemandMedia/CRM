import { json } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';
export async function GET({ cookies }) {
  try {
    await apiRequest('/roles/export/tickets/', {}, { cookies });
    return json({ allowed: true }, { headers: { 'Cache-Control': 'private, no-store' } });
  } catch (error) {
    return json(
      { allowed: false },
      { status: error.status || 500, headers: { 'Cache-Control': 'private, no-store' } }
    );
  }
}
