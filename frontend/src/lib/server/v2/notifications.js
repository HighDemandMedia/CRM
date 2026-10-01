/**
 * In-app notifications: the wiring behind /v2/notifications.
 *
 * Server-only. The feed is `GET /notifications/`, which already scopes to
 * `recipient=request.profile` (a user only ever sees their own). The writes
 * are `POST /notifications/<id>/read/` and `POST /notifications/read-all/`, both
 * recipient-scoped the same way, so nothing here can touch another person's
 * feed, and the page's job is only to call them.
 *
 * The one transform that matters is the LINK. `Notification.link` is a stored
 * *client* path a reader navigates to, and it comes in two shapes: old rows from
 * before the producer fix carry `/cases/<id>` (which no client serves), new CRM
 * rows carry `/tickets/<id>`, and product-support rows carry `/help/<id>`.
 * `resolvedLink` rebuilds a fresh internal path from a recognised prefix and
 * returns '' for anything else, so a stored value can
 * never be rendered as an arbitrary href (an `http(s)://…` or `javascript:` link
 * that slipped into the column can't become a live link or an open redirect),
 * and a correctly-produced `/tickets/` link is not left pointing at the v1 route.
 */
import { apiRequest } from '$lib/api-helpers.js';

/** Verbs the backend actually dispatches. Everything else has no copy and is
 *  flagged on the page as "no producer" rather than shown as a raw identifier. */
export const PRODUCED_VERBS = [
  'task.reminder',
  'calendar.reminder',
  'webform.submitted',
  'case.mentioned',
  'case.commented',
  'support.replied',
  'support.status_changed'
];

/**
 * A stored notification link → a safe internal destination, or '' if it is not
 * a link we recognise. Both `/cases/<id>` (pre-fix rows) and `/tickets/<id>`
 * (current rows) normalise to `/tickets/<id>`. Product support normalises to
 * `/help/<id>`, and accepts the `/support/<id>` spelling its producer wrote
 * before the page was renamed, for the same reason `/cases/` is still accepted.
 *
 * @param {unknown} link
 * @returns {string}
 */
export { resolvedLink } from '$lib/v2/notification-content.js';
import { resolvedLink } from '$lib/v2/notification-content.js';

/** One API notification → the row shape the page renders. */
function toRow(/** @type {any} */ n) {
  return {
    ...n,
    known_verb: PRODUCED_VERBS.includes(n.verb),
    resolved_link: resolvedLink(n.link)
  };
}

const FEED_LIMIT = 20;

/**
 * The recipient's feed, shaped for the page.
 *
 * @param {{ cookies: import('@sveltejs/kit').Cookies, url?: URL }} event
 */
export async function getNotifications({ cookies, url }) {
  const requested = Number(url?.searchParams.get('page') || 1);
  const page = Number.isSafeInteger(requested) && requested > 0 ? Math.min(requested, 1000000) : 1;
  const status = ['read', 'unread'].includes(url?.searchParams.get('status') || '')
    ? url.searchParams.get('status')
    : 'all';
  const params = new URLSearchParams({
    limit: String(FEED_LIMIT),
    offset: String((page - 1) * FEED_LIMIT)
  });
  if (status !== 'all') params.set(status, 'true');
  const resp = await apiRequest(`/notifications/?${params}`, {}, { cookies });
  const results = (resp.results || []).map(toRow);
  return {
    results,
    pagination: {
      page,
      size: FEED_LIMIT,
      status,
      pages: Math.max(1, Math.ceil((resp.count || 0) / FEED_LIMIT))
    },
    totals: {
      count: resp.count ?? results.length,
      unread: resp.unread_count ?? results.filter((n) => n.read_at === null).length,
      // Rows still carrying the dead `/cases/` prefix. Counted within the feed
      // the page is showing, surfaced once as a footnote (a tripwire for a
      // producer regression, not a per-row badge).
      broken_links: results.filter(
        (n) => typeof n.link === 'string' && n.link.startsWith('/cases/')
      ).length
    }
  };
}

/**
 * Unread count for the nav badge. A cheap `limit=1` call that still returns the
 * authoritative `unread_count` over the whole feed.
 *
 * @param {{ cookies: import('@sveltejs/kit').Cookies }} event
 */
export async function countUnread({ cookies }) {
  const resp = await apiRequest('/notifications/?limit=1', {}, { cookies });
  return resp.unread_count ?? 0;
}

/**
 * Mark one notification read. Idempotent server-side.
 *
 * @param {{ cookies: import('@sveltejs/kit').Cookies }} event
 * @param {string} id
 */
export async function markNotificationRead({ cookies }, id) {
  return apiRequest(`/notifications/${id}/read/`, { method: 'POST' }, { cookies });
}

/**
 * Mark every unread notification read.
 *
 * @param {{ cookies: import('@sveltejs/kit').Cookies }} event
 */
export async function markAllNotificationsRead({ cookies }) {
  return apiRequest('/notifications/read-all/', { method: 'POST', body: {} }, { cookies });
}
