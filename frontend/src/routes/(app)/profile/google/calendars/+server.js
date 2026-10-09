import { json } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';
import { googleErrorMessage } from '$lib/utils/google-feedback.js';
export async function GET({ cookies }) {
  try {
    return json(await apiRequest('/integrations/google/calendars/', {}, { cookies }), {
      headers: { 'Cache-Control': 'private, no-store' }
    });
  } catch (err) {
    return json(
      { error: googleErrorMessage(err) },
      { status: 400, headers: { 'Cache-Control': 'private, no-store' } }
    );
  }
}
