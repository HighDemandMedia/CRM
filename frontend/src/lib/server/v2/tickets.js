import { userName } from '$lib/utils/user-name.js';
/** Server-side ticket API adapter. Tenant and access checks remain in the API. */
import { error, redirect } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';
import { attachmentHref } from '$lib/server/v2/files.js';

/** Statuses where somebody still owes the customer something. Mirrors `cases.views.OPEN_STATUSES`. */
export const OPEN_STATUSES = ['New', 'Assigned', 'Pending'];

/**
 * @param {any} profile
 */
function profileName(profile) {
  return userName(profile, 'Unknown');
}

/**
 * @param {any} account
 */
function accountLink(account) {
  return account ? { id: account.id, name: account.name ?? '' } : null;
}

/**
 * The subset of a Django case the v2 pages read.
 *
 * `first_response_deadline` and both breach flags come from the serializer.
 * They are business-hours calculations that also account for pause time, and
 * reimplementing them in the browser would produce a second, quietly different
 * answer on the same screen.
 *
 * @param {any} row
 */
function toRow(row) {
  const assignees = row.assigned_to ?? [];
  return {
    id: row.id,
    custom_fields: row.custom_fields ?? {},
    ticket_code: row.ticket_code ?? '',
    category: row.category ?? 'General',
    source: row.source ?? 'Internal',
    due_at: row.due_at ?? null,
    waiting_reason: row.waiting_reason ?? '',
    resolution_note: row.resolution_note ?? '',
    deal: row.deal ?? null,
    last_activity: row.last_activity_at ?? row.created_at,
    last_activity_at: row.last_activity_at ?? row.created_at,
    name: row.name ?? '',
    status: row.status,
    priority: row.priority,
    // Nullable on the model, and null in plenty of seeded rows.
    case_type: row.case_type ?? null,
    description: row.description ?? '',
    account: accountLink(row.account),
    contacts: (row.contacts ?? []).map((/** @type {any} */ contact) => ({
      id: contact.id,
      name: [contact.first_name, contact.last_name].filter(Boolean).join(' ').trim()
    })),
    assignee: assignees.length ? profileName(assignees[0]) : null,
    assignee_count: assignees.length,
    opened_at: row.created_at,
    closed_on: row.closed_on ?? null,
    first_response_at: row.first_response_at ?? null,
    first_response_hours: row.sla_first_response_hours ?? null,
    first_response_deadline: row.first_response_sla_deadline ?? null,
    first_response_breached: Boolean(row.is_sla_first_response_breached),
    resolution_hours: row.sla_resolution_hours ?? null,
    resolution_deadline: row.resolution_sla_deadline ?? null,
    resolution_breached: Boolean(row.is_sla_resolution_breached),
    // The amber band between on-track and breached. Server-computed: it is a
    // fraction of this ticket's own target, and only the backend knows how
    // that target maps onto the org's business calendar.
    first_response_at_risk: Boolean(row.is_sla_first_response_at_risk),
    resolution_at_risk: Boolean(row.is_sla_resolution_at_risk),
    resolved_at: row.resolved_at ?? null,
    // Non-zero means the escalation task has already chased this one.
    escalation_count: row.escalation_count ?? 0,
    paused_at: row.sla_paused_at ?? null,
    child_count: row.child_count ?? 0,
    parent: row.parent_summary ?? null,
    // Everyone's logged time on this ticket, which is not what
    // `/cases/<id>/time-entries/` returns to an agent: that list is narrowed
    // to their own rows, so a panel adding it up would tell a team of three
    // the ticket had taken a third of the time it had. Absent on the list
    // endpoint (`slim=true`), hence the null.
    time_summary: row.time_summary ?? null,
    is_open: !['Resolved', 'Closed', 'Rejected', 'Duplicate'].includes(row.status)
  };
}

/**
 * Every filter param `listTickets` will forward. The descriptor in
 * `$lib/v2/filters.js` must not name a key absent from this list; a test in
 * `filters.test.js` enforces that, because the failure mode otherwise is a chip
 * on screen and an unfiltered list underneath it.
 */
export const FILTER_FIELDS = ['assigned_to', 'priority', 'case_type', 'sla_breached', 'tags'];

/**
 * The queue, newest first.
 *
 * `slim=true` drops the account and contact catalogues the endpoint used to
 * attach to every list response. They are for the form, not the queue, and
 * they were most of a 190 KB payload for five tickets.
 *
 * The API narrows this list for non-admins to tickets they raised, are
 * assigned to, or watch, so what comes back is already what this person may
 * see, and, since the detail view now enforces the same rule, every row here
 * opens.
 *
 * @param {{ cookies: import('@sveltejs/kit').Cookies }} event
 * @param {URLSearchParams} [params]
 */
export async function listTickets({ cookies }, params) {
  const query = new URLSearchParams(params ?? undefined);
  if (!query.has('limit')) query.set('limit', '25');
  query.set('slim', 'true');

  const response = await apiRequest(`/cases/?${query}`, {}, { cookies });
  const rows = (response.cases ?? []).map(toRow);

  return {
    results: rows,
    totals: {
      // Counted over the whole filtered queue by the API, not over this page.
      count: response.cases_count ?? rows.length,
      open: response.open_count ?? 0,
      urgent: response.urgent_count ?? 0,
      awaiting_reply: response.awaiting_first_reply ?? 0,
      shown: rows.length
    }
  };
}

/**
 * Fold comments, internal notes and threaded emails into one conversation.
 *
 * Three tables, one thing a human is looking at. The direction rule is the one
 * `cases/signals.py::_evaluate_reopen` already uses to decide whether a comment
 * should reopen a ticket: a comment with a `commented_by` came from our side,
 * and one without came from the customer. Emails carry their own direction.
 *
 * @param {any} response
 */
function toConversation(response) {
  /** @type {any[]} */
  const entries = [];

  for (const comment of response.comments ?? []) {
    const author = comment.commented_by;
    entries.push({
      id: `c-${comment.id}`,
      kind: 'comment',
      direction: author ? 'out' : 'in',
      // A reply written in the customer portal carries the contact who wrote
      // it, so name them. "The customer" is still the answer for an inbound
      // email or anything else that arrived without an author.
      author: author
        ? author.user_details?.email || 'Support'
        : comment.commented_by_contact?.name || 'The customer',
      at: comment.commented_on,
      body: comment.comment ?? ''
    });
  }

  for (const note of response.internal_notes ?? []) {
    entries.push({
      id: `n-${note.id}`,
      kind: 'note',
      direction: 'note',
      author: note.commented_by?.user_details?.email || 'Support',
      at: note.commented_on,
      body: note.comment ?? ''
    });
  }

  for (const message of response.email_messages ?? []) {
    entries.push({
      id: `e-${message.id}`,
      kind: 'email',
      direction: message.direction === 'outbound' ? 'out' : 'in',
      author: message.from_address ?? 'Unknown sender',
      at: message.received_at,
      subject: message.subject ?? '',
      body: message.body_text ?? ''
    });
  }

  entries.sort((a, b) => new Date(a.at).getTime() - new Date(b.at).getTime());
  return entries;
}

/**
 * One ticket, its conversation, and the ticket's context.
 *
 * `alsoOpen` needs a second request because the detail endpoint has no idea
 * what else is happening on that account. It asks for open tickets on the same
 * account and drops this one.
 *
 * @param {{ cookies: import('@sveltejs/kit').Cookies }} event
 * @param {string} id
 */
export async function getTicket({ cookies }, id) {
  const response = await fetchDetail(cookies, id);
  const ticket = toRow(response.cases_obj);

  /** @type {any[]} */
  let alsoOpen = [];
  if (ticket.account) {
    const query = new URLSearchParams({ limit: '6', slim: 'true', account: ticket.account.id });
    for (const status of OPEN_STATUSES) query.append('status', status);
    const siblings = await apiRequest(`/cases/?${query}`, {}, { cookies });
    alsoOpen = (siblings.cases ?? [])
      .filter((/** @type {any} */ row) => row.id !== ticket.id)
      .slice(0, 5)
      .map(toRow);
  }

  return {
    ticket,
    conversation: toConversation(response),
    // Filed against this ticket, not guessed at. See the header note.
    articles: (response.solutions ?? []).map((/** @type {any} */ article) => ({
      id: article.id,
      title: article.title ?? '',
      status: article.status,
      is_published: Boolean(article.is_published),
      updated_at: article.updated_at ?? article.created_at
    })),
    alsoOpen,
    contacts: ticket.contacts,
    attachments: (response.attachments ?? []).map((/** @type {any} */ file) => ({
      id: file.id,
      canDelete: file.can_delete === true,
      name: file.file_name ?? '',
      // Resolved to an absolute URL so the rail can offer it as a download; the
      // rail used to render the name as dead text even though the path was here.
      url: attachmentHref(file.id),
      at: file.created_at
    })),
    // `ActivitySerializer` (`common/serializer.py`) names the time
    // `created_at` and the verb `action_display`, and puts the actor's email
    // one level in, under `user.user_details`.
    //
    // This read `row.timestamp` and `row.user.email`, neither of which the
    // serializer has ever emitted, so every row in the rail rendered as
    // "System · — ago". A comment here used to justify `timestamp` by saying
    // two classes named `ActivitySerializer` existed and the shadowing one
    // used it; there is one class today, and
    // `common/tests/test_activity_serializer_shapes.py` pins its shape.
    activity: (response.activities ?? []).map((/** @type {any} */ row) => ({
      id: row.id,
      action: row.action,
      label: row.action_display || row.action,
      at: row.created_at,
      changes: row.metadata ?? {},
      by: row.user?.user_details?.email ?? null
    })),
    // The API's own answer about whether this person may reply, rather than a
    // guess from their role. It used to disagree with the endpoint.
    canReply: response.comment_permission === true
  };
}

/** Scalar fields the ticket forms own. Everything else is server-derived. */
export const EDITABLE_FIELDS = [
  'category',
  'source',
  'due_at',
  'waiting_reason',
  'resolution_note',
  'deal',
  'name',
  'status',
  'priority',
  'case_type',
  'description',
  'closed_on',
  'account'
];

/**
 * The choice lists the forms need, taken from the API rather than hardcoded.
 *
 * Status, priority and type come back as Django choice pairs, so a select
 * built from them cannot offer a value the serializer will reject.
 *
 * @param {import('@sveltejs/kit').Cookies} cookies
 */
async function listChoices(cookies) {
  const [response, deals] = await Promise.all([
    apiRequest('/cases/?limit=1', {}, { cookies }),
    apiRequest('/opportunities/?limit=100', {}, { cookies }).catch(() => ({ opportunities: [] }))
  ]);

  /** @param {any[]} pairs */
  const choices = (pairs) => (pairs ?? []).map((pair) => ({ value: pair[0], label: pair[1] }));

  const accounts = (response.accounts_list ?? []).map((/** @type {any} */ account) => ({
    id: account.id,
    name: account.name ?? ''
  }));
  accounts.sort((/** @type {any} */ a, /** @type {any} */ b) => a.name.localeCompare(b.name));

  const contacts = (response.contacts_list ?? []).map((/** @type {any} */ contact) => ({
    id: contact.id,
    name: [contact.first_name, contact.last_name].filter(Boolean).join(' ').trim()
  }));
  contacts.sort((/** @type {any} */ a, /** @type {any} */ b) => a.name.localeCompare(b.name));

  return {
    deals: (deals.opportunities ?? []).map((row) => ({ id: row.id, name: row.name })),
    statuses: choices(response.status),
    priorities: choices(response.priority),
    caseTypes: choices(response.type_of_case),
    accounts,
    contacts,
    // `users` is new: the endpoint computed this list and then discarded it.
    owners: (response.users ?? []).map((/** @type {any} */ user) => ({
      id: user.id,
      name: userName(user),
      email: user.user__email || ''
    }))
  };
}

/**
 * Everything the create form needs, in one call.
 *
 * @param {{ cookies: import('@sveltejs/kit').Cookies }} event
 * @param {string | null} [accountId] account to preselect, when arriving from one
 */
export async function getTicketFormOptions({ cookies }, accountId = null, contactId = null) {
  const choices = await listChoices(cookies);
  const known = choices.accounts.some((/** @type {any} */ row) => row.id === accountId);
  return {
    ...choices,
    defaults: {
      status: 'New',
      priority: 'Normal',
      case_type: '',
      account: known ? accountId : '',
      contacts: choices.contacts.some((row) => row.id === contactId) ? [contactId] : []
    }
  };
}

/**
 * The ticket plus what the edit form needs in order to explain itself.
 *
 * @param {{ cookies: import('@sveltejs/kit').Cookies }} event
 * @param {string} id
 */
export async function getTicketForEdit({ cookies }, id) {
  const [response, choices] = await Promise.all([fetchDetail(cookies, id), listChoices(cookies)]);
  const raw = response.cases_obj;
  const ticket = toRow(raw);

  return {
    ticket,
    ...choices,
    form: {
      resolution_note: ticket.resolution_note,
      category: ticket.category,
      source: ticket.source,
      due_at: ticket.due_at ?? '',
      waiting_reason: ticket.waiting_reason,
      deal: ticket.deal ?? '',
      account: ticket.account?.id ?? '',
      name: ticket.name,
      status: ticket.status,
      priority: ticket.priority,
      case_type: ticket.case_type ?? '',
      description: ticket.description,
      closed_on: ticket.closed_on ?? '',
      // Binds to a Profile id, not a display name.
      assigned_to: raw.assigned_to?.[0]?.id ?? '',
      contacts: (raw.contacts ?? []).map((/** @type {any} */ contact) => contact.id)
    },
    server: {
      account: ticket.account,
      assignee_count: (raw.assigned_to ?? []).length,
      team_count: (raw.teams ?? []).length,
      tag_count: (raw.tags ?? []).length,
      contact_count: (raw.contacts ?? []).length,
      child_count: ticket.child_count
    }
  };
}

/**
 * Turn form values into a request body.
 *
 * Absent stays absent. A field the form did not send is a field the save
 * leaves alone, which is the whole reason for PATCH below.
 *
 * @param {Record<string, any>} values
 */
function toBody(values) {
  /** @type {Record<string, any>} */
  const body = {};
  for (const field of EDITABLE_FIELDS) {
    if (!(field in values)) continue;
    const value = values[field];
    body[field] =
      value === '' && !['waiting_reason', 'resolution_note'].includes(field) ? null : value;
  }
  // Single-select owner, so the list is empty or one long. Only present when
  // the form decided it changed. See the action for why that matters.
  if ('assigned_to' in values) {
    body.assigned_to = values.assigned_to ? [values.assigned_to] : [];
  }
  if ('contacts' in values) {
    body.contacts = values.contacts ?? [];
  }
  return body;
}

/**
 * Save the edit form.
 *
 * PATCH, not PUT. Five for five now. `CaseDetailView.put` runs
 * `contacts.clear()`, `teams.clear()`, `assigned_to.clear()` and
 * `tags.clear()` unconditionally before re-adding whatever the body carried,
 * so one PUT from a form that holds a single owner would drop every
 * co-assignee, every team and every tag on the ticket. `patch` guards each
 * relation with `if "<field>" in params`.
 *
 * @param {{ cookies: import('@sveltejs/kit').Cookies }} event
 * @param {string} id
 * @param {Record<string, any>} values
 */
export async function updateTicket({ cookies }, id, values) {
  return await apiRequest(`/cases/${id}/`, { method: 'PATCH', body: toBody(values) }, { cookies });
}

/**
 * The parent/child tree this ticket sits in.
 *
 * Returns `{ root, focus_id }`. **`root` is the top of the whole tree, not this
 * ticket**: `CaseTreeView` walks up to the highest ancestor in the org so a
 * child URL still shows the full incident. The subtree that a close would
 * actually touch has to be found inside it, which
 * `routes/(app)/tickets/[id]/close.js` does.
 *
 * @param {{ cookies: import('@sveltejs/kit').Cookies }} event
 * @param {string} id
 */
export async function getTicketTree({ cookies }, id) {
  return await apiRequest(`/cases/${id}/tree/`, {}, { cookies });
}

/**
 * Close the ticket, and optionally every open descendant of it.
 *
 * `cascade` is always sent explicitly. The endpoint falls back to the org's
 * `auto_close_children_on_parent_close` only when the key is ABSENT, so a
 * caller that omits it hands the decision to a setting the person confirming
 * never saw. The confirm step seeds its checkbox from that setting instead,
 * which is what the setting is for, and then says what it is doing.
 *
 * `resolution_comment` lands in the `PARENT_CLOSED_CASCADE` activity row on
 * each cascaded child, so it is the only explanation anyone opening one of
 * those tickets will find.
 *
 * @param {{ cookies: import('@sveltejs/kit').Cookies }} event
 * @param {string} id
 * @param {{ cascade: boolean, resolution_comment?: string }} args
 */
export async function closeTicketWithChildren({ cookies }, id, { cascade, resolution_comment }) {
  return await apiRequest(
    `/cases/${id}/close-with-children/`,
    {
      method: 'POST',
      body: { cascade: Boolean(cascade), resolution_comment: resolution_comment ?? '' }
    },
    { cookies }
  );
}

/**
 * Create a ticket.
 *
 * No `org` and no `created_by` in the body: `CaseListView.post` sets both from
 * `request.profile`. `account` is checked against the caller's org before it is
 * accepted. It used to take anybody's.
 *
 * @param {{ cookies: import('@sveltejs/kit').Cookies }} event
 * @param {Record<string, any>} values
 */
export async function createTicket({ cookies }, values) {
  return await apiRequest('/cases/', { method: 'POST', body: toBody(values) }, { cookies });
}

/**
 * Post a reply, or an internal note, optionally with a file.
 *
 * The first public reply is what stamps `first_response_at` on the ticket.
 * That happens in a signal, so it holds however the comment was made. An
 * internal note deliberately does not stamp it: a note to the team is not an
 * answer to the customer.
 *
 * `CaseDetailView.post` saves the attachment in a block SEPARATE from the
 * comment (and ignores `is_internal` for it), so a file may ride with a reply
 * or arrive on its own. The field name is `case_attachment`. The file rides as
 * multipart; a plain reply stays JSON so the common path is unchanged.
 *
 * @param {{ cookies: import('@sveltejs/kit').Cookies }} event
 * @param {string} id
 * @param {{ body: string, internal?: boolean, file?: File|null }} reply
 */
export async function replyToTicket({ cookies }, id, reply) {
  if (reply.file) {
    const form = new FormData();
    if (reply.body) form.set('comment', reply.body);
    form.set('is_internal', String(Boolean(reply.internal)));
    form.set('case_attachment', reply.file);
    return await apiRequest(`/cases/${id}/`, { method: 'POST', body: form }, { cookies });
  }
  return await apiRequest(
    `/cases/${id}/`,
    { method: 'POST', body: { comment: reply.body, is_internal: Boolean(reply.internal) } },
    { cookies }
  );
}

/**
 * Bulk-update tickets. `fields` is a subset of
 * { status, priority, case_type, closed_on, assigned_to: string[], tags: string[] }.
 * The backend enforces per-case write access and the close gate, so this only
 * forwards; it never gates.
 * @param {{ cookies: any }} evt
 * @param {string[]} ids
 * @param {Record<string, any>} fields
 */
export async function bulkUpdateTickets({ cookies }, ids, fields) {
  return await apiRequest(
    '/cases/bulk/update/',
    { method: 'POST', body: { ids, fields } },
    { cookies }
  );
}

/**
 * Bulk soft-delete tickets. Backend deletes only those the caller may delete
 * (admin or creator) and reports the rest as no_access.
 * @param {{ cookies: any }} evt
 * @param {string[]} ids
 */
export async function bulkDeleteTickets({ cookies }, ids) {
  return await apiRequest('/cases/bulk/delete/', { method: 'POST', body: { ids } }, { cookies });
}

/**
 * Count a bulk `results` array by outcome status, for the summary banner.
 * Each entry also carries an `id` and, on some outcomes, a `detail`; only
 * `status` is read here.
 * @param {Array<{status: string, [key: string]: any}>} results
 */
export function summarizeBulk(results) {
  const out = {
    updated: 0,
    deleted: 0,
    no_access: 0,
    approval_required: 0,
    closed_on_required: 0,
    invalid: 0
  };
  for (const r of results ?? []) {
    if (r.status in out) out[r.status] += 1;
  }
  return out;
}

/**
 * `CaseDetailView.get` answers 404 for another org's ticket. Deliberately not
 * 403, which would confirm the id exists, and 403 for a ticket inside the org
 * that this profile neither raised, nor is assigned to, nor watches.
 *
 * It has a third answer the fixtures had no equivalent for: a ticket that was
 * merged into another one comes back as a 200 carrying `redirect_to`, so the
 * duplicate's URL keeps working and lands on the survivor.
 *
 * @param {import('@sveltejs/kit').Cookies} cookies
 * @param {string} id
 */
async function fetchDetail(cookies, id) {
  /** @type {any} */
  let response;
  try {
    response = await apiRequest(`/cases/${id}/`, {}, { cookies });
  } catch (/** @type {any} */ err) {
    // On the status, not on the wording.
    if (err?.status === 404) {
      error(404, 'That ticket does not exist, or it belongs to another team.');
    }
    if (err?.status === 403) {
      error(403, 'This ticket belongs to somebody else. Ask an admin if you need it.');
    }
    throw err;
  }
  if (response?.redirect_to) {
    redirect(307, `/tickets/${response.redirect_to}`);
  }
  return response;
}
