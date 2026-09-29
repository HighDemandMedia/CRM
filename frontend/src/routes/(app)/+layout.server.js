import { apiRequest } from '$lib/api-helpers.js';
import { listLeads } from '$lib/server/v2/leads.js';
import { listTickets, OPEN_STATUSES } from '$lib/server/v2/tickets.js';
import { listInvoices } from '$lib/server/v2/invoices.js';
import { countAwaitingApprovals } from '$lib/server/v2/approvals.js';

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
  /** @param {any} event */
  leads: async (event) =>
    (await listLeads(event, new URLSearchParams({ limit: '1' }))).totals.count,
  /**
   * Open tickets only. A support badge counting closed ones would never go
   * down, which is the same objection as the accounts note below.
   *
   * @param {any} event
   */
  tickets: async (event) => {
    const params = new URLSearchParams({ limit: '1' });
    for (const status of OPEN_STATUSES) params.append('status', status);
    return (await listTickets(event, params)).totals.open;
  },
  /**
   * Invoices waiting on this person: drafts to send plus anything overdue to
   * chase, counted by the API per requester. Not the total invoice count.
   * That is inventory, the same objection as the accounts note below, and not
   * the outstanding *amount*, which the pills on the page already show. The
   * shell has always carried a needs-action invoice badge; this keeps it real.
   *
   * @param {any} event
   */
  invoices: async (event) =>
    (await listInvoices(event, new URLSearchParams({ limit: '1' }))).totals.action_needed,
  /**
   * Approvals waiting on *this* person: the ones only they can clear (the
   * inbox scopes `mine=true&state=pending` to the actionable set, and a
   * requester's own rows are excluded by the self-approval rule). This is work,
   * not inventory: it goes down as they decide, so it earns a badge.
   *
   * @param {any} event
   */
  approvals: async (event) => await countAwaitingApprovals(event)
  /*
   * No `accounts` entry, deliberately, even though the module is wired.
   *
   * These badges count work: leads to call, deals to move, tickets to answer.
   * "Accounts 10" counts inventory. It never goes down, nothing about it is
   * ever waiting on you, and a badge you learn to ignore teaches you to ignore
   * the ones beside it. The nav has never had an accounts count and should not
   * gain one just because the number became available.
   *
   * No `team` entry either. A people count is the same inventory objection, and
   * the one actionable number there, live tokens on deactivated accounts, is
   * admin-only (the count endpoint 403s a member) and the page already surfaces
   * it prominently. A badge only some roles can compute does not fit a shell
   * that is the same for everyone.
   */
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
    canPreview: !!event.locals.profile?.can_preview,
    isPlatformOwner: !!event.locals.profile?.is_platform_owner
  };

  const context = await apiRequest('/org/ui-context/', {}, { cookies: event.cookies });
  shell.org.terminology = context.terminology;
  shell.isSuperAdmin = !!context.is_super_admin;
  const countKeys = Object.keys(LIVE_COUNTS).filter(key => shell.canPreview || key === 'tickets');
  const counts = Promise.allSettled(
    countKeys.map(key => LIVE_COUNTS[/** @type {keyof typeof LIVE_COUNTS} */ (key)](event))
  ).then(results => {
    /** @type {Record<string, number>} */
    const values = {};
    results.forEach((result, i) => {
      if (result.status === 'fulfilled') values[countKeys[i]] = result.value;
    });
    return values;
  });
  return {
    ...shell, counts,
    permissions: context.permissions,
    propertyLayout: context.property_layout,
    pipelineConfig: context.pipelines
  };
}
