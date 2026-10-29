import { API_ORIGIN } from '$lib/server/api-origin.js';
import { clientIdentityHeaders } from '$lib/server/proxy-identity.js';
import { error, fail } from '@sveltejs/kit';
const path = '/api/appointment-response/';
const choices = ['accepted', 'tentative', 'declined'];
export async function load({ url, fetch, setHeaders }) {
  setHeaders({ 'Cache-Control': 'private, no-store', 'Referrer-Policy': 'no-referrer' });
  const token = url.searchParams.get('token') || '';
  const response = await fetch(`${API_ORIGIN}${path}?${new URLSearchParams({ token })}`);
  if (!response.ok && response.status !== 410)
    error(response.status, 'Unable to load this invitation. Please try again.');
  return {
    token,
    invitation: response.ok ? await response.json() : null,
    unavailable: !response.ok,
    selected: choices.includes(url.searchParams.get('response'))
      ? url.searchParams.get('response')
      : ''
  };
}
export const actions = {
  default: async ({ request, fetch, getClientAddress }) => {
    const form = await request.formData();
    const body = JSON.stringify({
      token: String(form.get('token') || ''),
      response: String(form.get('response') || '')
    });
    const response = await fetch(`${API_ORIGIN}${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...clientIdentityHeaders(path, body, getClientAddress)
      },
      body
    });
    if (!response.ok)
      return fail(response.status, {
        error:
          response.status === 410
            ? 'This invitation is no longer available. Use the latest invitation.'
            : 'Unable to save your response. Please try again.'
      });
    return { saved: true, response: (await response.json()).response };
  }
};
