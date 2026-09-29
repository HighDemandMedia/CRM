import { API_ORIGIN } from '$lib/server/api-origin.js';
import axios from 'axios';
import { fail, redirect } from '@sveltejs/kit';
import { passwordError, savePasswordSession } from '$lib/server/password-session.js';
import { previewInvitation } from '$lib/server/invitation.js';

export async function load({ locals, cookies }) {
  if (locals.user) redirect(303, cookies.get('crm_invitation') ? '/invite' : '/org');
  const token = cookies.get('crm_invitation');
  if (!token) return { invited: false };
  let invitation;
  try {
    invitation = await previewInvitation(token);
  } catch (error) {
    return {
      invited: true,
      error: passwordError(error, 'Could not open this invitation. Please try again.')
    };
  }
  if (invitation.existing_account) redirect(303, '/invite');
  return { invited: true, invitation };
}

export const actions = {
  default: async ({ request, cookies }) => {
    const form = await request.formData();
    const values = Object.fromEntries(
      ['name', 'email', 'organization', 'timezone'].map((key) => [
        key,
        String(form.get(key) || '').trim()
      ])
    );
    const password = String(form.get('password') || '');
    if (password !== String(form.get('confirm_password') || ''))
      return fail(400, { error: 'Passwords do not match.', values });
    let data;
    const invitation = cookies.get('crm_invitation');
    try {
      const response = await axios.post(
        `${API_ORIGIN}/api/auth/password/register/`,
        {
          name: values.name,
          email: values.email,
          timezone: values.timezone || 'UTC',
          password,
          ...(invitation ? { invitation } : { organization: values.organization })
        },
        { timeout: 15000 }
      );
      data = response.data;
    } catch (error) {
      return fail(error.response?.status === 429 ? 429 : 400, {
        error: passwordError(error, 'Account could not be created. Please try again.'),
        values
      });
    }
    savePasswordSession(cookies, data);
    cookies.delete('crm_invitation', { path: '/' });
    redirect(303, data.current_org ? '/' : '/org');
  }
};
