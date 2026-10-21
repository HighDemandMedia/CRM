import { error, redirect } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';
import { savePasswordSession } from '$lib/server/password-session.js';
import { describeError } from '$lib/server/log-safe.js';

/**
 * Legacy sign-in destination: enter the current workspace without a chooser.
 * Organization switching remains in the profile menu. The app layout enforces
 * onboarding and live permissions after this redirect.
 * @type {import('./$types').PageServerLoad}
 */
export async function load({ cookies, locals, setHeaders }) {
  setHeaders({ 'Cache-Control': 'private, no-store' });
  if (!locals.user) redirect(303, '/login');
  if (cookies.get('crm_invitation')) redirect(303, '/invite');
  if (locals.org?.id) redirect(303, '/');

  let result;
  try {
    const user = await apiRequest('/auth/me/', {}, { cookies });
    if (!Array.isArray(user.organizations)) throw new Error('Missing organization list');
    // Only use API-authorized memberships, never an organization from the URL.
    const organization = user.organizations[0];
    if (!organization) return { canCreateOrganization: user.is_platform_owner === true };
    const refresh = cookies.get('jwt_refresh');
    result = await apiRequest(
      '/auth/switch-org/',
      {
        method: 'POST',
        body: { org_id: organization.id, ...(refresh ? { refresh } : {}) }
      },
      { cookies }
    );
    if (!result?.access_token || !result?.refresh_token || !result?.current_org?.id)
      throw new Error('Incomplete organization session');
  } catch (err) {
    console.error('Organization entry failed:', describeError(err));
    if (err?.status === 401) {
      for (const name of ['jwt_access', 'jwt_refresh', 'org']) cookies.delete(name, { path: '/' });
      redirect(303, '/login');
    }
    error(err?.status === 403 ? 403 : 503, 'Could not open your organization.');
  }

  savePasswordSession(cookies, result);
  redirect(303, '/');
}
