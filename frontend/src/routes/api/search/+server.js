import { json } from '@sveltejs/kit';
import { demoPageAllowed } from '$lib/v2/demo-view.js';
import { search } from '$lib/server/v2/search.js';

/**
 * ⌘K palette search. The palette runs in the browser and the access token is an
 * httpOnly cookie, so the query is proxied through here; the cookie stays
 * server-side and the Django endpoint scopes results to the caller's org.
 *
 * @type {import('./$types').RequestHandler}
 */
export async function GET({ url, cookies, locals }) {
  const q = url.searchParams.get('q') || '';
  try {
    const result = await search({ cookies }, q);
    if (!locals.profile?.can_preview)
      result.results = result.results.filter((row) => demoPageAllowed(row.href));
    return json(result);
  } catch (/** @type {any} */ err) {
    return json({ results: [], error: err?.message || 'Search failed' }, { status: 400 });
  }
}
