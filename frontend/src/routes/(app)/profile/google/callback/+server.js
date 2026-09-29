import { redirect } from '@sveltejs/kit';
import { timingSafeEqual } from 'node:crypto';
import { apiRequest } from '$lib/api-helpers.js';
export async function GET({ cookies, url }) {
  const expected = cookies.get('google_connection_state') || '';
  const received = url.searchParams.get('state') || '';
  cookies.delete('google_connection_state', { path: '/profile/google/callback' });
  const valid =
    expected &&
    Buffer.byteLength(expected) === Buffer.byteLength(received) &&
    timingSafeEqual(Buffer.from(expected), Buffer.from(received));
  if (!valid || url.searchParams.has('error') || !url.searchParams.get('code'))
    redirect(303, '/profile?google=cancelled');
  try {
    await apiRequest(
      '/integrations/google/callback/',
      { method: 'POST', body: { state: received, code: url.searchParams.get('code') } },
      { cookies }
    );
  } catch {
    redirect(303, '/profile?google=failed');
  }
  redirect(303, '/profile?google=connected');
}
