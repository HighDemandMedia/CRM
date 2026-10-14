import { error } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';
import { previewInvitation } from '$lib/server/invitation.js';
import agreement from '$lib/server/legal/dpa.json';

/** @type {import('./$types').PageServerLoad} */
export async function load({ cookies, locals, url, setHeaders }) {
  setHeaders({ 'Cache-Control': 'private, no-store', 'X-Robots-Tag': 'noindex, nofollow' });
  let authorized = false;
  const token = cookies.get('crm_invitation');
  if (token) {
    try {
      const invitation = await previewInvitation(token);
      authorized = invitation.legal?.organization_authority_required === true;
    } catch (err) {
      const status = err?.response?.status;
      if (![400, 401, 403, 404].includes(status))
        error(503, 'Could not verify access. Please try again.');
    }
  }
  if (!authorized && locals.user) {
    let context;
    try {
      // Always verify live server permissions, not client flags or decoded JWT roles.
      context = await apiRequest('/org/ui-context/', {}, { cookies });
    } catch (err) {
      if ([401, 403, 404].includes(err?.status))
        error(403, 'This agreement is available to organization administrators.');
      error(503, 'Could not verify access. Please try again.');
    }
    authorized = context.permissions?.is_admin === true;
  }
  if (!authorized)
    error(403, 'Open your administrator invitation or sign in as an organization administrator.');
  const language = (url.searchParams.get('lang') || cookies.get('crm_language') || 'en').startsWith(
    'es'
  )
    ? 'es'
    : 'en';
  return {
    language,
    version: agreement.version,
    draft: agreement.draft,
    document: agreement.documents[language]
  };
}
