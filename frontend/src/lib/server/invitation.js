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
