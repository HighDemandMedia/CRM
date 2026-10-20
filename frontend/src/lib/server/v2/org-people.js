/** Server-only people/teams lookup, restricted by the current user's record policy. */
import { apiRequest } from '$lib/api-helpers.js';

/** A profile as the pickers label it. */
function personName(profile) {
  const d = profile?.user_details ?? {};
  return d.name || d.email || 'Unnamed';
}

/**
 * @param {import('@sveltejs/kit').Cookies} cookies
 * @param {{ module?: string, action?: 'view' | 'reassign' }} [options]
 * @returns {Promise<{ people: { id: string, name: string, email: string }[], teams: { id: string, name: string }[] }>}
 */
export async function getOrgPeopleAndTeams(cookies, { module, action = 'view' } = {}) {
  try {
    const query = new URLSearchParams();
    if (module) query.set('module', module);
    if (action !== 'view') query.set('action', action);
    const suffix = query.size ? `?${query}` : '';
    const resp = await apiRequest(`/users/get-teams-and-users/${suffix}`, {}, { cookies });
    return {
      people: (resp?.profiles ?? []).map((/** @type {any} */ p) => ({
        id: p.id,
        name: personName(p),
        email: p.user_details?.email ?? ''
      })),
      teams: (resp?.teams ?? []).map((/** @type {any} */ t) => ({ id: t.id, name: t.name }))
    };
  } catch {
    return { people: [], teams: [] };
  }
}

/**
 * The viewer's own PROFILE id, for the "Mine" presets.
 *
 * Matched by email because no id is available any other way: the JWT carries
 * `user_email` but no profile id, and `locals.user.id` is the User id, not the
 * Profile id that `assigned_to` filters on. Those are different tables and
 * mixing them has silently broken checks in this codebase before.
 *
 * Returns null when nothing matches, and callers must then hide the preset
 * rather than render a link that filters to nobody.
 *
 * @param {{id: string, email?: string}[]} people
 * @param {string | undefined} viewerEmail
 * @returns {string | null}
 */
export function resolveMe(people, viewerEmail) {
  if (!viewerEmail) return null;
  const wanted = viewerEmail.toLowerCase();
  return people.find((p) => (p.email ?? '').toLowerCase() === wanted)?.id ?? null;
}
