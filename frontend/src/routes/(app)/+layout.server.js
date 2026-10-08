import { canOpenSettingsPath } from '$lib/v2/settings-access.js';
import { error, redirect } from '@sveltejs/kit';
import { setupDestination } from '$lib/server/onboarding.js';
import { normalizeLocale } from '$lib/i18n/messages.js';
import { apiRequest } from '$lib/api-helpers.js';
import { listTickets, OPEN_STATUSES } from '$lib/server/v2/tickets.js';

/**
 * Counts actually rendered by Sidebar and SectionTabs.
 *
 * Leaving a migrated module on its fixture count puts "Leads 24" in the
 * sidebar beside "18 open" in the page, and a nav badge that disagrees with
 * the page it links to is worse than no badge.
 *
 * Only fetch a count if the shell displays it. The notification bell fetches
 * its own feed after mount; unused totals must not delay the initial render.
 */
const LIVE_COUNTS = {
  tickets: async (event) => {
    const params = new URLSearchParams({ limit: '1' });
    for (const status of OPEN_STATUSES) params.append('status', status);
    return (await listTickets(event, params)).totals.open;
  }
};

/**
 * Required shell settings share one authenticated request. Optional navigation
 * badges stream afterwards so a slow counter cannot hold a page or parent().
 * No shared cache: permissions and configuration stay specific to this session.
 * @type {import('./$types').LayoutServerLoad}
 */
export async function load(event) {
  const shell = {
    accountUser: event.locals.user || { name: '', email: '' },
    accountId: event.locals.org?.id || '',
    counts: /** @type {Record<string, number>} */ ({}),
    org: {
      name: event.locals.org?.name || 'High Demand Media CRM',
      terminology: /** @type {Record<string, string> | undefined} */ (undefined),
      // The currency for figures that are sums rather than one record: pipeline
      // totals, invoice ageing, goal progress. A per-record currency cannot
      // label a sum, and `money()` falls back to a hardcoded USD when it is not
      // told, which printed a dollar sign over a euro figure on every page that
      // forgot. It lives here rather than in each page loader because 17 of
      // them needed it and copying the same line 17 times is how the first one
      // fell out of step.
      //
      // This does not make a mixed-currency sum correct: the API adds `amount`
      // across rows regardless of currency, so an org running more than one
      // gets an addition that should not have happened, and no symbol repairs
      // it. Read from the JWT's org settings, which is also where a new deal's
      // currency comes from.
      currency: /** @type {any} */ (event.locals).org_settings?.default_currency || 'USD'
    },
    // Server-derived from the JWT (never the client). Display-only: it lets the
    // shell hide destinations a member can only reach to be turned away. The
    // backend still enforces every one of those gates, so this is UX, not a
    // security control. Defaults to the non-admin view when the claim is absent.
    role: event.locals.profile?.role ?? 'USER',
    isSuperAdmin: !!event.locals.profile?.is_super_admin,
    demoMode: !!event.locals.profile?.is_demo,
    canPreview: false,
    isPlatformOwner: !!event.locals.profile?.is_platform_owner
  };

  const context = await apiRequest('/org/ui-context/', {}, { cookies: event.cookies });
  const destination = setupDestination(context.setup_step);
  // Reading pathname makes this gate run again on module navigation, including client-side links.
  const pathname = event.url?.pathname;
  if (destination && pathname !== destination) redirect(303, destination);
  if (!canOpenSettingsPath(context.permissions, pathname))
    error(403, 'You do not have permission to access these settings.');
  const uiLocale = normalizeLocale(context.ui_language);
  if (event.cookies.get('crm_language') !== uiLocale) {
    event.cookies.set('crm_language', uiLocale, {
      path: '/',
      httpOnly: true,
      sameSite: 'lax',
      secure: event.url?.protocol === 'https:',
      maxAge: 31536000
    });
  }
  shell.org.terminology = context.terminology;
  shell.isSuperAdmin = !!context.is_super_admin;
  // The database may have changed since the access token was issued.
  shell.role = context.permissions?.is_admin === true ? 'ADMIN' : 'USER';
  const countKeys = Object.keys(LIVE_COUNTS);
  const counts = Promise.allSettled(
    countKeys.map((key) => LIVE_COUNTS[/** @type {keyof typeof LIVE_COUNTS} */ (key)](event))
  ).then((results) => {
    /** @type {Record<string, number>} */
    const values = {};
    results.forEach((result, i) => {
      if (result.status === 'fulfilled') values[countKeys[i]] = result.value;
    });
    return values;
  });
  return {
    ...shell,
    uiLocale,
    counts,
    permissions: context.permissions,
    propertyLayout: context.property_layout,
    ticketSettings: context.ticket_settings,
    pipelineConfig: context.pipelines
  };
}
