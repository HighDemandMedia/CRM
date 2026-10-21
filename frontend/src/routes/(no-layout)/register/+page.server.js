import { googleAvailable, googleError, generateOAuthUrl } from '$lib/server/google-oauth.js';
import { signedJson } from '$lib/server/proxy-identity.js';
import { API_ORIGIN } from '$lib/server/api-origin.js';
import axios from 'axios';
import { fail, redirect } from '@sveltejs/kit';
import { passwordError, savePasswordSession } from '$lib/server/password-session.js';
import { previewInvitation, invitationFailure } from '$lib/server/invitation.js';
import { legalFormValues } from '$lib/legal.js';

export async function load({ locals, cookies, getClientAddress, url }) {
  if (locals.user) redirect(303, cookies.get('crm_invitation') ? '/invite' : '/org');
  const token = cookies.get('crm_invitation');
  if (!token) return { invited: false };
  let invitation;
  try {
    invitation = await previewInvitation(token, getClientAddress);
  } catch (error) {
    const issue = invitationFailure(error);
    if (issue.startsWith('invitation_')) cookies.delete('crm_invitation', { path: '/' });
    return {
      invited: true,
      issue,
      error: passwordError(error, 'Could not open this invitation. Please try again.')
    };
  }
  if (invitation.existing_account) redirect(303, '/invite');
  return {
    invited: true,
    invitation,
    google_available: googleAvailable(),
    password: url?.searchParams.get('method') === 'password',
    googleError: url?.searchParams.has('error') ? googleError(url.searchParams.get('error')) : ''
  };
}

export const actions = {
  google: async ({ request, cookies, getClientAddress }) => {
    const token = cookies.get('crm_invitation');
    if (!token) return fail(403, { error: 'An invitation is required to create an account.' });
    const form = await request.formData();
    let invitation;
    try {
      invitation = await previewInvitation(token, getClientAddress);
    } catch (error) {
      return fail(400, {
        error: passwordError(error, 'Could not open this invitation. Please try again.')
      });
    }
    const legal = legalFormValues(form);
    if (
      invitation.legal?.version &&
      (legal.legal_version !== invitation.legal.version ||
        !legal.accept_terms ||
        !['en', 'es'].includes(legal.legal_locale) ||
        (invitation.legal.organization_authority_required && !legal.organization_authority))
    ) {
      return fail(400, { error: 'Review and accept the terms before continuing.' });
    }
    const destination = await generateOAuthUrl(cookies, false, {
      token,
      email: invitation.email,
      legal
    });
    if (!destination) return fail(503, { error: googleError('unavailable') });
    redirect(303, destination);
  },
  password: async ({ request, cookies, getClientAddress }) => {
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
    if (!invitation)
      return fail(403, { error: 'An invitation is required to create an account.', values });
    try {
      const payload = signedJson(
        '/api/auth/password/register/',
        {
          name: values.name,
          email: values.email,
          timezone: values.timezone || 'UTC',
          password,
          ...legalFormValues(form),
          ...(invitation ? { invitation } : { organization: values.organization })
        },
        getClientAddress
      );
      const response = await axios.post(`${API_ORIGIN}/api/auth/password/register/`, payload.body, {
        headers: payload.headers,
        timeout: 15000
      });
      data = response.data;
    } catch (error) {
      return fail(error.response?.status === 429 ? 429 : 400, {
        error: passwordError(error, 'Account could not be created. Please try again.'),
        values
      });
    }
    savePasswordSession(cookies, data);
    cookies.delete('crm_invitation', { path: '/' });
    redirect(303, data.current_org ? '/onboarding' : '/org');
  }
};
