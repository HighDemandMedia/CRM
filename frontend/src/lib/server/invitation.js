import axios from 'axios';
import { API_ORIGIN } from '$lib/server/api-origin.js';

export async function previewInvitation(token) {
  const response = await axios.post(
    `${API_ORIGIN}/api/auth/password/invitation/`,
    { token },
    { timeout: 15000 }
  );
  return response.data;
}
