import { fail, redirect } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';
import { apiRequest } from '$lib/api-helpers.js';
import { readableError } from '$lib/server/v2/form-errors.js';
import { previewInvitation } from '$lib/server/invitation.js';
import { passwordError } from '$lib/server/password-session.js';
export async function load({ url, cookies, locals }) {
  const token = url.searchParams.get('token');
  if (token && /^[A-Za-z0-9_-]{20,128}$/.test(token)) {
    cookies.set('crm_invitation', token, {
      path: '/',
      httpOnly: true,
      secure: env.NODE_ENV === 'production',
      sameSite: 'lax',
      maxAge: 7 * 86400
    });
    redirect(303, '/invite');
  }
  let invitation = null,
    error = '';
  if (!locals.user && cookies.get('crm_invitation')) {
    try {
      invitation = await previewInvitation(cookies.get('crm_invitation'));
    } catch (err) {
      error = passwordError(err, 'Could not open this invitation. Please try again.');
    }
    if (invitation && !invitation.existing_account) redirect(303, '/register');
  }
  if (locals.user && cookies.get('crm_invitation')) {
    try {
      invitation = await apiRequest(
        '/auth/accept-invitation/',
        { method: 'POST', body: { token: cookies.get('crm_invitation'), preview: true } },
        { cookies }
      );
    } catch (err) {
      error = readableError(err, 'Could not open this invitation.');
    }
  }
  return {
    hasInvitation: !!cookies.get('crm_invitation'),
    signedIn: !!locals.user,
    invitation,
    error
  };
}
export const actions = {
  accept: async ({ cookies }) => {
    const token = cookies.get('crm_invitation');
    if (!token) return fail(400, { error: 'Open the link from your invitation email.' });
    try {
      await apiRequest(
        '/auth/accept-invitation/',
        { method: 'POST', body: { token } },
        { cookies }
      );
    } catch (err) {
      return fail(400, { error: readableError(err, 'Could not accept this invitation.') });
    }
    cookies.delete('crm_invitation', { path: '/' });
    redirect(303, '/org');
  }
};
