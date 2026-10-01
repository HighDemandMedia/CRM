/**
 * Organization-scoped member access, pending email invitations, and team membership.
 * All mutations are authorized by the backend; cookies stay server-side.
 */
import { apiRequest } from '$lib/api-helpers.js';

/**
 * Profile.role is ADMIN | USER, the only two the backend recognises. There is
 * no MANAGER despite ApprovalRule offering it; a picker offering a value the
 * server rejects is worse than not offering it.
 */
export const ROLES = ['ADMIN', 'USER'];

/**
 * The signed-in user's id, read from the `user_id` claim of the access token.
 *
 * Used only to mark ", you" on a row and to withhold the controls a person
 * must not use on themselves. It is a display hint, never an authorization
 * decision: the server re-derives identity from the same token and is the
 * thing that actually refuses a self-role-change. Decoded, not verified.
 * Verifying our own freshly-read cookie would buy nothing.
 *
 * @param {import('@sveltejs/kit').Cookies} cookies
 * @returns {string | null}
 */
function viewerUserId(cookies) {
  const token = cookies.get('jwt_access');
  if (!token) return null;
  try {
    const payload = token.split('.')[1];
    const json = Buffer.from(payload, 'base64url').toString('utf-8');
    return JSON.parse(json).user_id ?? null;
  } catch {
    return null;
  }
}

/**
 * One person as the page reads it, from a `ProfileSerializer` row.
 *
 * `id` is the profile id; `user_id` is the User id, which is the pk every
 * `/api/user/<id>/` verb takes. Keeping both here means the template never has
 * to remember which one an action needs.
 *
 * @param {any} p
 * @param {Record<string, string[]>} teamsByProfile
 * @param {string | null} viewerId
 */
function toMember(p, teamsByProfile, viewerId) {
  const details = p.user_details ?? {};
  return {
    id: p.id,
    user_id: details.id,
    name: details.name || details.email || 'Unnamed',
    email: details.email,
    role: p.role,
    is_super_admin: !!p.is_super_admin,
    access_role_id: p.access_role_id,
    access_role_name: p.access_role_name,
    is_active: p.is_active,
    teams: teamsByProfile[p.id] ?? [],
    last_login: details.last_login ?? null,
    active_token_count: p.active_token_count ?? 0,
    is_you: !!viewerId && details.id === viewerId
  };
}

/**
 * The team-and-access page.
 *
 * `/api/users/` and `/api/teams/` are both admin-only. A non-admin who reaches
 * this page (the nav shows it to everyone) gets a clean "admins only" state
 * rather than an error: `forbidden` is the API's 403 turned into a fact the
 * page can render, not a crash.
 *
 * @param {{ cookies: import('@sveltejs/kit').Cookies }} event
 */
export async function listTeam({ cookies }) {
  let usersResp, teamsResp, invitationsResp, rolesResp;
  try {
    [usersResp, teamsResp, invitationsResp, rolesResp] = await Promise.all([
      apiRequest('/users/?limit=1000', {}, { cookies }),
      apiRequest('/teams/?limit=1000', {}, { cookies }),
      apiRequest('/invitations/', {}, { cookies }),
      apiRequest('/roles/', {}, { cookies })
    ]);
  } catch (/** @type {any} */ err) {
    if (err?.status === 403) return { forbidden: true };
    throw err;
  }

  const viewerId = viewerUserId(cookies);
  const teamRows = teamsResp?.teams ?? [];

  // profile id -> the names of the teams it belongs to, from the teams payload.
  /** @type {Record<string, string[]>} */
  const teamsByProfile = {};
  for (const t of teamRows) {
    for (const u of t.users ?? []) {
      (teamsByProfile[u.id] ??= []).push(t.name);
    }
  }

  const active = (usersResp?.active_users?.active_users ?? []).map((/** @type {any} */ p) =>
    toMember(p, teamsByProfile, viewerId)
  );
  const inactive = (usersResp?.inactive_users?.inactive_users ?? []).map((/** @type {any} */ p) =>
    toMember(p, teamsByProfile, viewerId)
  );

  const teams = teamRows.map((/** @type {any} */ t) => ({
    id: t.id,
    name: t.name,
    description: t.description || '',
    members: (t.users ?? []).map((u) => u.id),
    member_count: (t.users ?? []).length
  }));

  const admins = active.filter((/** @type {any} */ m) => m.role === 'ADMIN');

  return {
    forbidden: false,
    isSuperAdmin: active.some((m) => m.is_you && m.is_super_admin),
    active,
    inactive,
    teams,
    invitations: invitationsResp?.invitations ?? [],
    roles: ROLES,
    accessRoles: rolesResp.roles,
    totals: {
      count: active.length,
      admins: admins.length,
      never_signed_in: active.filter((/** @type {any} */ m) => !m.last_login).length,
      deactivated: inactive.length,
      // A live token outliving the account that owns it, the number worth acting on.
      tokens_on_deactivated: inactive.reduce(
        (/** @type {number} */ a, /** @type {any} */ m) => a + m.active_token_count,
        0
      )
    },
    // Whether the org would have a second admin left if one were removed. The
    // page mirrors "keep at least one admin" as a hint; the server enforces it.
    last_admin_id: admins.length === 1 ? admins[0].user_id : null
  };
}

/**
 * Invite someone: `POST /api/users/`. Admin-only server-side. Role is chosen
 * at invite time. That is legitimate on this path (an admin choosing a new
 * member's role), unlike a member setting their own.
 *
 * @param {{ cookies: import('@sveltejs/kit').Cookies }} event
 * @param {{ email: string, role: string, access_role_id?: string|null }} body
 */
export function inviteUser({ cookies }, body) {
  return apiRequest('/invitations/', { method: 'POST', body }, { cookies });
}

/**
 * Change a person's role: `PATCH /api/user/<userId>/`. The server allows this
 * only for an admin acting on someone other than themselves, so the page never
 * offers it on your own row or when it would strip the last admin.
 *
 * @param {{ cookies: import('@sveltejs/kit').Cookies }} event
 * @param {string} userId  the User id, not the profile id
 * @param {string} role
 */
export function setRole({ cookies }, userId, role) {
  return apiRequest(`/user/${userId}/`, { method: 'PATCH', body: { role } }, { cookies });
}

/**
 * Activate or deactivate: `POST /api/user/<userId>/status/`. The server refuses
 * to deactivate the last active admin.
 *
 * @param {{ cookies: import('@sveltejs/kit').Cookies }} event
 * @param {string} userId
 * @param {'Active' | 'Inactive'} status
 */
export function setStatus({ cookies }, userId, status) {
  return apiRequest(`/user/${userId}/status/`, { method: 'POST', body: { status } }, { cookies });
}

export function cancelInvitation({ cookies }, id) {
  return apiRequest(`/invitations/${id}/`, { method: 'DELETE' }, { cookies });
}
export function saveTeam({ cookies }, id, body) {
  return apiRequest(
    id ? `/teams/${id}/` : '/teams/',
    { method: id ? 'PATCH' : 'POST', body },
    { cookies }
  );
}
export function deleteTeam({ cookies }, id) {
  return apiRequest(`/teams/${id}/`, { method: 'DELETE' }, { cookies });
}
