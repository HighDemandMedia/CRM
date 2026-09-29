import { json } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';
export async function GET({ cookies, params }) {
  if (!/^[0-9a-f-]{36}$/i.test(params.id))
    return json({ error: 'Invalid email.' }, { status: 400 });
  try {
    return json(await apiRequest(`/integrations/google/mail/${params.id}/`, {}, { cookies }), {
      headers: { 'Cache-Control': 'private, no-store' }
    });
  } catch {
    return json(
      { error: 'Email unavailable or access denied.' },
      { status: 404, headers: { 'Cache-Control': 'private, no-store' } }
    );
  }
}
