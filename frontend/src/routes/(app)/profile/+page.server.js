import { googleErrorMessage } from '$lib/utils/google-feedback.js';
import { setupDestination } from '$lib/server/onboarding.js';
import { savePasswordSession } from '$lib/server/password-session.js';
import { listTimezones } from '$lib/server/v2/organization.js';
import { fail, redirect } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';
import { readableError } from '$lib/server/v2/form-errors.js';
import { getProfile } from '$lib/server/v2/profile.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ cookies, url }) {
  const [profile, timezones, password] = await Promise.all([
    getProfile({ cookies }),
    listTimezones(cookies),
    apiRequest('/auth/password/change/', {}, { cookies })
  ]);
  return {
    ...profile,
    onboarding: ['profile', 'profile_organization'].includes(profile.profile.setup_step),
    timezones,
    googleResult: url.searchParams.get('google'),
    integrationTab: url.searchParams.get('tab') === 'integrations',
    hasPassword: password.has_password && !password.can_reset_password
  };
}

/** @type {import('./$types').Actions} */
export const actions = {
  googleConnect: async ({ cookies, request, url }) => {
    const form = await request.formData();
    const service = String(form.get('service'));
    if (!['gmail', 'calendar'].includes(service))
      return fail(400, { scope: 'google', message: 'Choose a Google service.' });
    let result;
    try {
      result = await apiRequest(
        `/integrations/google/connect/${service}/`,
        { method: 'POST', body: {} },
        { cookies }
      );
    } catch (err) {
      return fail(400, {
        scope: 'google',
        message: googleErrorMessage(err)
      });
    }
    cookies.set('google_connection_state', result.state, {
      path: '/profile/google/callback',
      httpOnly: true,
      secure: url.protocol === 'https:',
      sameSite: 'lax',
      maxAge: 600
    });
    redirect(303, result.url);
  },
  googleManage: async ({ cookies, request }) => {
    const form = await request.formData();
    try {
      await apiRequest(
        '/integrations/google/',
        {
          method: 'POST',
          body: Object.fromEntries(
            ['service', 'operation', 'calendar_id'].map((key) => [key, String(form.get(key) || '')])
          )
        },
        { cookies }
      );
      return {
        scope: 'google',
        saved: true,
        googleMessage:
          form.get('operation') === 'disconnect'
            ? 'Disconnected. Cached Google data has been removed from the CRM.'
            : 'Synchronization requested. Check the connection status and last sync time for progress.'
      };
    } catch (err) {
      return fail(400, {
        scope: 'google',
        message: googleErrorMessage(err)
      });
    }
  },
  password: async ({ cookies, request }) => {
    const form = await request.formData();
    if (form.get('password') !== form.get('confirm_password'))
      return fail(400, { scope: 'password', message: 'Passwords do not match.' });
    try {
      const result = await apiRequest(
        '/auth/password/change/',
        {
          method: 'POST',
          body: {
            current_password: String(form.get('current_password') || ''),
            password: String(form.get('password') || '')
          }
        },
        { cookies }
      );
      savePasswordSession(cookies, result);
      return { scope: 'password', saved: true };
    } catch (err) {
      return fail(400, {
        scope: 'password',
        message: readableError(err, 'Could not change password.')
      });
    }
  },
  emailMode: async ({ cookies, request }) => {
    const form = await request.formData();
    try {
      await apiRequest(
        '/profile/',
        {
          method: 'PATCH',
          body: { email_integration_mode: String(form.get('email_integration_mode') || '') }
        },
        { cookies }
      );
      return { scope: 'email', saved: true };
    } catch (err) {
      return fail(400, {
        scope: 'email',
        message: readableError(err, 'Could not save email preference.')
      });
    }
  },
  // Only forward editable personal fields; account access is managed separately.
  edit: async ({ cookies, request }) => {
    const form = await request.formData();
    /** @type {Record<string, string | boolean>} */
    const body = {};
    for (const field of ['name', 'phone', 'language', 'timezone', 'ui_language']) {
      if (form.has(field)) body[field] = form.get(field)?.toString().trim() ?? '';
    }

    const completing = form.get('complete_setup') === '1';
    if (completing) body.complete_setup = true;
    let result;
    try {
      result = await apiRequest('/profile/', { method: 'PATCH', body }, { cookies });
    } catch (/** @type {any} */ err) {
      return fail(err?.status === 400 ? 400 : 500, {
        values: body,
        message: readableError(err, 'Could not save your profile.')
      });
    }

    if (completing) redirect(303, setupDestination(result.setup_step) || '/');
    return { saved: true };
  }
};
