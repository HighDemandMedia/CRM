<script>
  import { page } from '$app/state';
  import { configuredLabel } from '$lib/v2/pipeline-config.js';
  import PropertySummary from '$lib/v2/components/PropertySummary.svelte';
  import { untrack } from 'svelte';
  import { enhance } from '$app/forms';
  import { resolve } from '$app/paths';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import RecordTabs from '$lib/v2/components/RecordTabs.svelte';
  import TicketAssociates from './TicketAssociates.svelte';
  import TicketFields from './TicketFields.svelte';
  import Attachments from '$lib/v2/components/Attachments.svelte';
  import { dueDateLabel, statusLabel as defaultStatusLabel, priorityLabel } from './options.js';
  const statusLabel = (key) =>
    configuredLabel(page.data.pipelineConfig, 'Case', key, defaultStatusLabel(key));
  let { data, form, onadvanced } = $props();
  let ticket = $derived(data.ticket);
  let editing = $state(false),
    resolving = $state(false),
    busy = $state(false),
    note = $state('');
  let values = $state(untrack(() => ({ ...data.editOptions.form })));
  const date = (v) =>
    v ? new Date(v).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : '—';
  const overdue = $derived(ticket.is_open && ticket.due_at && new Date(ticket.due_at) < new Date());
  function edit() {
    values = { ...data.editOptions.form, contacts: [...data.editOptions.form.contacts] };
    editing = true;
  }
  function modal(node) {
    node.showModal();
    return {
      destroy() {
        node.close();
      }
    };
  }
  function save() {
    busy = true;
    return async ({ result, update }) => {
      await update({ reset: false });
      busy = false;
      if (result.type === 'success') editing = false;
    };
  }
  function postNote() {
    busy = true;
    return async ({ result, update }) => {
      await update({ reset: false });
      busy = false;
      if (result.type === 'success') note = '';
    };
  }
</script>

<PageHeader title={ticket.name || ticket.ticket_code || `Ticket · ${ticket.id.slice(0, 8)}`} record>
  {#snippet crumb()}<a href={resolve('/tickets')}>Tickets</a><span>{ticket.ticket_code}</span><span
      class="status">{statusLabel(ticket.status)}</span
    >{/snippet}
  {#snippet actions()}{#if ticket.is_open}<button
        class="v2-btn v2-btn-primary"
        onclick={() => (resolving = true)}>Resolve</button
      >{:else}<form method="POST" action="?/setStatus" use:enhance>
        <button class="v2-btn" name="status" value="New">Reopen</button>
      </form>{/if}{#if ticket.status === 'Resolved'}<form
        method="POST"
        action="?/setStatus"
        use:enhance
      >
        <button class="v2-btn" name="status" value="Closed">Close</button>
      </form>{/if}{/snippet}
</PageHeader>
{#if form?.error}<p class="v2-error message" role="alert">{form.error}</p>{/if}
<div class="profile">
  <aside>
    <div class="heading">
      <h2>Properties</h2>
      {#if !editing}<button class="v2-btn" onclick={edit}>Edit</button>{/if}
    </div>
    {#if editing}<form method="POST" action="?/properties" use:enhance={save}>
        <TicketFields bind:values options={data.editOptions} showAssociates={false} />
        <div class="actions">
          <button class="v2-btn v2-btn-primary" disabled={busy}>Save</button><button
            class="v2-btn"
            type="button"
            onclick={() => (editing = false)}>Cancel</button
          >
        </div>
      </form>
    {:else}<PropertySummary
        target="Case"
        record={ticket}
        entries={[
          ['Name', ticket.name],
          ['Assigned to', ticket.assignee ?? '—'],
          ['Priority', priorityLabel(ticket.priority)],
          ['Status', statusLabel(ticket.status)],
          ['Category', ticket.category],
          ['Due date', dueDateLabel(ticket.due_at) + (overdue ? ' · Overdue' : ''), 'due_at'],
          ['Source', ticket.source],
          ...(ticket.status === 'Pending'
            ? [['Waiting on', ticket.waiting_reason || '—', 'waiting_reason']]
            : []),
          ['Created', date(ticket.opened_at)],
          ['Last Activity', date(ticket.last_activity)]
        ]}
      />{/if}
  </aside>
  <main>
    <section class="description">
      <h2>Description</h2>
      <p class="body">{ticket.description || '—'}</p>
      {#if ticket.resolution_note}<div class="resolution">
          <h3>Resolution</h3>
          <p class="body">{ticket.resolution_note}</p>
        </div>{/if}
    </section>
    <RecordTabs>
      {#snippet notes()}<div class="notes">
          {#each data.conversation.filter((entry) => entry.kind === 'note') as entry}<article>
              <p class="body">{entry.body}</p>
              <small>{entry.author} · {date(entry.at)}</small>
            </article>{:else}<p class="muted">No notes yet.</p>{/each}
        </div>
        {#if data.canReply}<form method="POST" action="?/reply" use:enhance={postNote}>
            <input type="hidden" name="internal" value="on" /><textarea
              class="v2-input"
              name="body"
              bind:value={note}
              placeholder="Add an internal note…"
              rows="3"
              aria-label="Internal note"></textarea><button
              class="v2-btn v2-btn-primary add"
              disabled={busy || !note.trim()}>Add note</button
            >
          </form>{/if}{/snippet}
      {#snippet activity()}<div class="activity">
          {#each data.activity.filter( (entry) => ['CREATE', 'UPDATE', 'STATUS_CHANGED', 'PRIORITY_CHANGED', 'ASSIGN'].includes(entry.action) ) as entry}<article
            >
              <strong>{entry.label}</strong><small>{entry.by || 'System'} · {date(entry.at)}</small
              >{#each Object.entries(entry.changes?.changes ?? {}) as [key, change]}<p
                  class="muted"
                >
                  {key.replaceAll('_', ' ')}: {String(change.before ?? '—')} → {String(
                    change.after ?? '—'
                  )}
                </p>{/each}{#if entry.changes?.before !== undefined}<p class="muted">
                  {entry.changes.before} → {entry.changes.after}
                </p>{/if}
            </article>{:else}<p class="muted">No changes yet.</p>{/each}
        </div>{/snippet}
    </RecordTabs>
  </main>
  <aside>
    <h2>Associations</h2>
    {#if editing}<TicketAssociates bind:values options={data.editOptions} />{:else}
      {#each ticket.contacts as contact}<a
          class="association"
          href={resolve(`/contacts/${contact.id}`)}
          ><small>Contact</small><strong>{contact.name}</strong></a
        >{/each}{#if ticket.account}<a
          class="association"
          href={resolve(`/accounts/${ticket.account.id}`)}
          ><small>Company</small><strong>{ticket.account.name}</strong></a
        >{/if}{#if ticket.deal}<a class="association" href={resolve(`/pipeline/${ticket.deal}`)}
          ><small>Deal</small><strong
            >{data.editOptions.deals?.find((d) => d.id === ticket.deal)?.name ??
              'Open deal'}</strong
          ></a
        >{/if}<button class="v2-btn" onclick={edit}>+ Association</button>{/if}
    <section class="attachments">
      <Attachments
        attachments={data.attachments.map((file) => ({ ...file, href: file.url }))}
        allowUpload={data.canReply}
      />
    </section>
  </aside>
</div>
{#if resolving}<dialog
    use:modal
    onclose={() => (resolving = false)}
    aria-labelledby="resolve-title"
    class="dialog"
  >
    <h2 id="resolve-title">Resolve ticket</h2>
    <form
      method="POST"
      action="?/resolve"
      use:enhance={() => {
        busy = true;
        return async ({ result, update }) => {
          await update();
          busy = false;
          if (result.type === 'success') resolving = false;
        };
      }}
    >
      <label
        >Resolution note<textarea class="v2-input" name="resolution_note" required rows="4"
        ></textarea></label
      >{#if form?.error}<p role="alert" class="v2-error">{form.error}</p>{/if}
      <div class="actions">
        <button class="v2-btn" type="button" onclick={() => (resolving = false)}>Cancel</button
        ><button class="v2-btn v2-btn-primary" disabled={busy}>Resolve</button>
      </div>
    </form>
  </dialog>{/if}

<style>
  .profile {
    display: grid;
    grid-template-columns: 280px minmax(300px, 1fr) 260px;
    gap: var(--crm-space-4);
    flex: 1;
    min-height: 0;
    padding: 18px var(--crm-space-6);
    overflow: auto;
  }
  .profile > aside,
  .profile > main {
    background: var(--v2-bg);
    padding: var(--crm-space-5);
    border-radius: var(--crm-radius-lg);
    overflow: auto;
    min-width: 0;
  }
  h2 {
    font-size: var(--crm-text-sm);
    font-weight: 650;
    margin: 0 0 18px;
  }
  .heading {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 18px;
  }
  .heading h2 {
    margin: 0;
  }
  .status {
    background: var(--v2-paper);
    padding: var(--crm-space-1) var(--crm-space-2);
    border-radius: var(--crm-radius-sm);
  }
  .body {
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    font-size: var(--crm-text-sm);
    line-height: 1.6;
  }
  .actions {
    display: flex;
    gap: var(--crm-space-2);
    margin-top: var(--crm-space-5);
  }
  .notes,
  .activity {
    max-height: 45vh;
    overflow: auto;
  }
  article {
    padding: 14px 0;
    border-bottom: 1px solid var(--v2-line);
  }
  small {
    display: block;
    font-size: var(--crm-text-xs);
    color: var(--v2-muted);
    margin-top: 5px;
  }
  .muted {
    color: var(--v2-muted);
    font-size: var(--crm-text-sm);
  }
  .v2-input {
    width: 100%;
    margin-top: var(--crm-space-3);
  }
  .add {
    margin-top: 10px;
  }
  .association {
    display: block;
    text-decoration: none;
    color: inherit;
    padding: var(--crm-space-3);
    background: var(--v2-paper);
    border-radius: var(--crm-radius-md);
    margin: 10px 0;
    font-size: var(--crm-text-sm);
  }
  .attachments {
    margin-top: 30px;
  }
  .resolution {
    margin: var(--crm-space-5) 0;
    background: var(--v2-paper);
    padding: var(--crm-space-3);
    border-radius: var(--crm-radius-md);
  }
  h3 {
    font-size: var(--crm-text-xs);
  }
  .description {
    margin-bottom: var(--crm-space-6);
  }
  .message {
    padding: 0 var(--crm-space-6);
  }
  .dialog::backdrop {
    background: var(--crm-overlay);
  }
  .dialog {
    border: 0;
    background: var(--v2-bg);
    border-radius: var(--crm-radius-lg);
    padding: var(--crm-space-6);
    width: min(460px, 100%);
  }
  @media (max-width: 1100px) {
    .profile {
      grid-template-columns: 260px 1fr;
    }
    .profile > aside:last-child {
      grid-column: 1/-1;
    }
  }
  @media (max-width: 700px) {
    .profile {
      display: block;
      padding: var(--crm-space-3);
    }
    .profile > aside,
    .profile > main {
      margin-bottom: var(--crm-space-3);
      overflow: visible;
    }
  }
</style>
