import { json } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';
import { readableError, stageRequirements } from '$lib/server/v2/form-errors.js';
import { getOrgPeopleAndTeams } from '$lib/server/v2/org-people.js';
const endpoints = {
  Contact: 'contacts',
  Account: 'accounts',
  Opportunity: 'opportunities',
  Task: 'tasks',
  Case: 'cases'
};
export async function POST({ cookies, request }) {
  const { target, id, values } = await request.json();
  if (
    !Object.hasOwn(endpoints, target) ||
    !/^[0-9a-f-]{36}$/i.test(id) ||
    !values ||
    typeof values !== 'object' ||
    Array.isArray(values)
  )
    return json({ error: 'Invalid stage change.' }, { status: 400 });
  try {
    await apiRequest(
      `/${endpoints[target]}/${id}/`,
      { method: 'PATCH', body: values },
      { cookies }
    );
    return json({ saved: true });
  } catch (error) {
    return json(
      {
        error: readableError(error, 'Could not save the change.'),
        stageRequirements: stageRequirements(error)
      },
      { status: error.status || 400 }
    );
  }
}
export async function GET({ cookies, url }) {
  const relation = url.searchParams.get('relation');
  const query = url.searchParams.get('q') || '';
  try {
    if (relation === 'Profile') {
      const { people } = await getOrgPeopleAndTeams(cookies);
      return json(
        {
          options: people
            .filter((p) => `${p.name} ${p.email}`.toLowerCase().includes(query.toLowerCase()))
            .map((p) => ({ value: p.id, label: p.name }))
        },
        { headers: { 'Cache-Control': 'private, no-store' } }
      );
    }
    const endpoint =
      relation === 'Tags'
        ? 'tags'
        : Object.hasOwn(endpoints, relation)
          ? endpoints[relation]
          : null;
    if (!endpoint) return json({ options: [] });
    const data = await apiRequest(
      `/${endpoint}/?limit=50&search=${encodeURIComponent(query)}`,
      {},
      { cookies }
    );
    const rows =
      data.results ??
      data.active_accounts?.open_accounts ??
      data.opportunities ??
      data.cases ??
      data.contact_obj_list ??
      data.account_obj_list ??
      data.opportunity_obj_list ??
      data.cases_list ??
      data.task_list ??
      data.tasks ??
      data.tags ??
      [];
    return json(
      {
        options: rows.map((row) => ({
          value: row.id,
          ...(relation === 'Tags' ? { color: row.color } : {}),
          label: row.name || row.title || [row.first_name, row.last_name].filter(Boolean).join(' ')
        }))
      },
      { headers: { 'Cache-Control': 'private, no-store' } }
    );
  } catch {
    return json({ error: 'Could not load options. Try searching again.' }, { status: 400 });
  }
}
