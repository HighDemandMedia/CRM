import { error, fail, redirect } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';
import { setupDestination } from '$lib/server/onboarding.js';
import { listTimezones, updateOrgSettings } from '$lib/server/v2/organization.js';
import { fieldErrors, readableError } from '$lib/server/v2/form-errors.js';
import { settingsAccess } from '$lib/v2/settings-access.js';

async function pendingContext(cookies) {
  const context = await apiRequest('/org/ui-context/', {}, { cookies });
  if (!setupDestination(context.setup_step) || context.lifecycle?.read_only) redirect(303, '/');
  return context;
}

function requireOrganizationAccess(context) {
  if (settingsAccess(context.permissions, 'organization') !== 'manage')
    error(403, 'Organization management permission required.');
}

/** @type {import('./$types').PageServerLoad} */
export async function load({ cookies, url, setHeaders }) {
  setHeaders({ 'Cache-Control': 'private, no-store', 'Referrer-Policy': 'no-referrer' });
  const context = await pendingContext(cookies);
  const organizationStep =
    context.setup_step === 'organization' && url.searchParams.get('step') !== 'profile';
  const [profile, timezones] = await Promise.all([
    apiRequest('/profile/', {}, { cookies }),
    listTimezones(cookies)
  ]);
  let organization = null;
  if (organizationStep) {
    requireOrganizationAccess(context);
    organization = await apiRequest('/org/settings/', {}, { cookies });
  }
  return {
    step: organizationStep ? 'organization' : 'profile',
    includesOrganization: context.setup_step !== 'profile',
    profile: profile.user_obj,
    organization,
    timezones
  };
}

/** @type {import('./$types').Actions} */
export const actions = {
  default: async ({ cookies, request }) => {
    const context = await pendingContext(cookies);
    const form = await request.formData();
    const step = form.get('step');
    if (!['profile', 'organization'].includes(String(step)))
      return fail(400, { message: 'Choose a setup step.', values: null, errors: {} });
    if (step === 'organization') {
      requireOrganizationAccess(context);
      if (context.setup_step !== 'organization')
        return fail(400, { message: 'Complete your profile first.', values: null, errors: {} });
    }
    const fields =
      step === 'profile'
        ? ['name', 'ui_language', 'timezone']
        : ['name', 'default_currency', 'default_country', 'timezone'];
    const values = Object.fromEntries(
      fields.map((key) => [key, String(form.get(key) || '').trim()])
    );
    let next;
    try {
      if (step === 'profile') {
        const result = await apiRequest(
          '/profile/',
          {
            method: 'PATCH',
            body: { ...values, complete_setup: true }
          },
          { cookies }
        );
        cookies.set('crm_language', values.ui_language, {
          path: '/',
          httpOnly: true,
          sameSite: 'lax',
          secure: new URL(request.url).protocol === 'https:',
          maxAge: 31536000
        });
        next = setupDestination(result.setup_step) || '/';
      } else {
        await updateOrgSettings({ cookies }, { ...values, complete_setup: true });
        next = '/';
      }
    } catch (err) {
      const validation = err?.status === 400;
      return fail(validation ? 400 : err?.status === 403 ? 403 : 503, {
        values,
        message: validation
          ? readableError(err, 'Check your details and try again.')
          : 'Could not save your setup. Please try again.',
        errors: validation ? fieldErrors(err) : {}
      });
    }
    redirect(303, next);
  }
};
