import axios from 'axios';
import { API_ORIGIN } from '$lib/server/api-origin.js';
import { signedJson } from '$lib/server/proxy-identity.js';

export async function previewInvitation(token, getClientAddress) {
  const payload = signedJson('/api/auth/password/invitation/', { token }, getClientAddress);
  const response = await axios.post(`${API_ORIGIN}/api/auth/password/invitation/`, payload.body, {
    timeout: 15000,
    headers: payload.headers
  });
  return response.data;
}

/** Classify both the public Axios preview and authenticated API failures. */
export function invitationFailure(error) {
  const status = error?.response?.status ?? error?.status;
  const body = error?.response?.data ?? error?.body;
  const known = [
    'invitation_accepted',
    'invitation_expired',
    'invitation_cancelled',
    'invitation_invalid'
  ];
  if (known.includes(body?.code)) return body.code;
  if (status === 429) return 'rate_limited';
  if (!status || status >= 500 || status === 408) return 'temporary';
  return 'invitation_invalid';
}
