import { json } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';
import { readableError } from '$lib/server/v2/form-errors.js';
export async function GET({ cookies }) {
  try {
    return json(await apiRequest('/integrations/google/calendars/', {}, { cookies }), {
      headers: { 'Cache-Control': 'private, no-store' }
    });
  } catch (err) {
    return json({ error: readableError(err, 'Could not load calendars.') }, { status: 400 });
  }
}
