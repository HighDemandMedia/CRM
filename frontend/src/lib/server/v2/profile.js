import { env } from '$env/dynamic/public';
/** Loads personal profile details and the current organization name. */
import { apiRequest } from '$lib/api-helpers.js';

/** Split a single display name into first/last for the page's header.
 *  The backend stores one `name` on User; the page shows "First Last". */
function splitName(/** @type {string} */ name, /** @type {string} */ email) {
  const trimmed = (name || '').trim();
  if (!trimmed) {
    const local = (email || '').split('@')[0] || 'You';
    return { first_name: local, last_name: '' };
  }
  const sp = trimmed.indexOf(' ');
  if (sp === -1) return { first_name: trimmed, last_name: '' };
  return { first_name: trimmed.slice(0, sp), last_name: trimmed.slice(sp + 1) };
}

/**
 * The current user's account, shaped for the page.
 *
 * @param {{ cookies: import('@sveltejs/kit').Cookies }} event
 * @returns {Promise<{ profile: any, org: { name: string } }>}
 */
export async function getProfile({ cookies }) {
  const currentOrgId = cookies.get('org') || '';

  const [me, orgResp] = await Promise.all([
    apiRequest('/profile/', {}, { cookies }),
    apiRequest('/org/', {}, { cookies })
  ]);

  const u = me.user_obj || {};
  const ud = u.user_details || {};
  const name = splitName(ud.name, ud.email);

  const memberships = orgResp.profile_org_list || [];
  const orgs = memberships
    .map((/** @type {any} */ m) => ({
      id: m.org?.id ?? '',
      name: m.org?.name ?? '',
      role: m.role,
      is_current: String(m.org?.id ?? '') === String(currentOrgId)
    }))
    .filter((o) => o.id);

  // Current org name: the membership the JWT points at, falling back to the
  // first one so the header is never blank if the `org` cookie is missing.
  const current = orgs.find((o) => o.is_current) || orgs[0] || null;

  return {
    profile: {
      id: u.id,
      setup_step: u.setup_step || 'complete',
      user_details: {
        first_name: name.first_name,
        last_name: name.last_name,
        email: ud.email || ''
      },
      role: u.role,
      phone: u.phone || '',
      ui_language: u.ui_language === 'es' ? 'es' : 'en',
      language: u.language || '',
      timezone: u.timezone || '',
      organization_timezone: u.organization_timezone || 'UTC',
      notify_in_app: u.notify_in_app !== false,
      notify_mentions: u.notify_mentions !== false,
      notify_comments: u.notify_comments !== false,
      email_integration_mode: u.email_integration_mode || '',
      integrations: u.integrations,
      photo_url: u.photo_url ? new URL(u.photo_url, env.PUBLIC_DJANGO_API_URL).href : '',
      teams: u.teams || [],
      joined_at: u.date_of_joining || u.created_at || null,
      last_login: ud.last_login || null,
      orgs
    },
    org: { name: current?.name || '' }
  };
}
