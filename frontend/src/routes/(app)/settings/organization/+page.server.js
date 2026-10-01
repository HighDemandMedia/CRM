import { apiRequest } from '$lib/api-helpers.js';
import { fail, redirect } from '@sveltejs/kit';
import {
  getOrgSettings,
  listTimezones,
  updateOrgSettings,
  EDITABLE_FIELDS
} from '$lib/server/v2/organization.js';
import { readableError } from '$lib/server/v2/form-errors.js';
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** @type {import('./$types').PageServerLoad} */
export async function load({ cookies }) {
  const [settings, timezones] = await Promise.all([
    getOrgSettings({ cookies }),
    listTimezones(cookies)
  ]);
  return { ...settings, timezones };
}

/** @type {import('./$types').Actions} */
export const actions = {
  save: async ({ cookies, request }) => {
    const form = await request.formData();
    /** @type {Record<string, unknown>} */
    const body = {};
    for (const field of EDITABLE_FIELDS) {
      if (form.has(field)) body[field] = form.get(field)?.toString().trim() ?? '';
    }
    try {
      await updateOrgSettings({ cookies }, body);
    } catch (/** @type {any} */ err) {
      return fail(err?.status === 403 ? 403 : 400, {
        values: body,
        message: readableError(err, 'Could not save organization details.')
      });
    }
    return { saved: true };
  },
  switchOrg: async ({ cookies, request }) => {
    const form = await request.formData();
    const orgId = form.get('org_id')?.toString() ?? '';

    if (!UUID_RE.test(orgId)) {
      return fail(400, { scope: 'switch', message: 'Invalid organisation.' });
    }

    // Sent so the backend retires the token we are replacing; it belongs to the
    // caller (the API checks) or is ignored.
    const outgoingRefresh = cookies.get('jwt_refresh');
    const payload = outgoingRefresh
      ? { org_id: orgId, refresh: outgoingRefresh }
      : { org_id: orgId };

    /** @type {any} */
    let result;
    try {
      result = await apiRequest(
        '/auth/switch-org/',
        { method: 'POST', body: payload },
        { cookies }
      );
    } catch (/** @type {any} */ err) {
      // 403 is the honest one: you asked for an org you are not a member of.
      const message =
        err?.status === 403
          ? 'You are not a member of that organisation.'
          : readableError(err, 'Could not switch organisation.');
      return fail(err?.status === 403 ? 403 : 500, { scope: 'switch', message });
    }

    const secure = process.env.NODE_ENV === 'production';
    cookies.set('jwt_access', result.access_token, {
      path: '/',
      httpOnly: true,
      sameSite: 'lax',
      secure,
      maxAge: 60 * 60 * 24
    });
    cookies.set('jwt_refresh', result.refresh_token, {
      path: '/',
      httpOnly: true,
      sameSite: 'lax',
      secure,
      maxAge: 60 * 60 * 24 * 365
    });
    cookies.set('org', orgId, {
      path: '/',
      sameSite: 'strict',
      maxAge: 60 * 60 * 24 * 365
    });

    throw redirect(303, '/settings/organization');
  }
};
