<script>
  import ContactForm from '$lib/components/contacts/ContactForm.svelte';
  let editingProperties = $state(false);
  import Attachments from '$lib/v2/components/Attachments.svelte';
  import { resolve } from '$app/paths';
  import { invalidateAll } from '$app/navigation';
  import { enhance } from '$app/forms';
  import CreateAppointment from '$lib/v2/components/CreateAppointment.svelte';
  import TagBadge from '$lib/v2/components/TagBadge.svelte';
  import { Pencil } from '@lucide/svelte';
  let scheduled = $state(false);
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import { exactTime } from '$lib/v2/contact-time.js';
  import { money } from '$lib/v2/format.js';
  import { STAGE_LABEL } from '$lib/v2/enums.js';
  /** @type {{data:any, form:any}} */
  let { data, form } = $props();
  let contact = $derived(data.contact);
  let companies = $derived([
    ...(contact.account ? [contact.account] : []),
    ...contact.other_accounts
  ]);
  let note = $state('');
  let noteBusy = $state(false);
  let noteError = $state('');
</script>

<PageHeader title={contact.name}>
  {#snippet crumb()}<a href={resolve('/contacts')}>Contacts</a>{/snippet}
  {#snippet actions()}
    <CreateAppointment
      hosts={data.hosts}
      defaultHost={data.defaultHost}
      selected={new Date()}
      defaultAttendee={{ id: contact.id, name: contact.name, type: 'contact' }}
      action={`${resolve('/calendar')}?/create`}
      onCreated={() => {
        scheduled = true;
        void invalidateAll();
      }}
    />
    {#if contact.email}<a class="v2-btn" href={`mailto:${contact.email}`}>Email</a>{:else}<button
        class="v2-btn"
        type="button"
        disabled
        title="Add an email to this contact">Email</button
      >{/if}
  {/snippet}
</PageHeader>
{#if scheduled}<div class="scheduled-message" role="status">
    Event scheduled. <a href={resolve('/calendar')}>View calendar</a>
  </div>{/if}
<div class="contact-profile">
  <section class="properties" aria-label="Contact properties">
    <div class="properties-heading">
      <h2>Properties</h2>
      <button
        class="v2-btn"
        type="button"
        disabled={editingProperties}
        onclick={() => (editingProperties = true)}><Pencil size={13} />Edit</button
      >
    </div>
    <dl class="creation-info">
      <dt>Created</dt>
      <dd>{exactTime(contact.created_at)}</dd>
      <dt>Created by</dt>
      <dd>{contact.created_by_email || 'Not recorded'}</dd>
    </dl>
    {#if editingProperties}
      <ContactForm
        data={data.editor}
        result={form}
        editing
        inline
        onCancel={() => (editingProperties = false)}
        onSaved={async () => {
          await invalidateAll();
          editingProperties = false;
        }}
      />
    {:else}
      <dl class="property-values">
        {#each [['Name', contact.name], ['Contact owner', data.owners?.join(', ')], ['Phone', contact.phone], ['Email', contact.email], ['Language', contact.language], ['Source', contact.source_label], ['Stage', contact.stage_label], ['Preferred communication channel', contact.preferred_communication_channel_label], ['Appointment', contact.appointment_at ? exactTime(contact.appointment_at) : ''], ['Address', contact.address_line], ['City', contact.city], ['State', contact.state], ['Zip Code', contact.postcode], ['Country', contact.country]] as [label, value]}
          <div>
            <dt>{label}</dt>
            <dd>
              {#if label === 'Stage' && value}<span class="stage-value">{value}</span
                >{:else}{value || '—'}{/if}
            </dd>
          </div>
        {/each}
        <div>
          <dt>Tags</dt>
          <dd class="property-tags">
            {#each contact.tags as tag (tag.id)}<TagBadge {tag} />{:else}—{/each}
          </dd>
        </div>
      </dl>
    {/if}
  </section>
  <main class="contact-center">
    <section class="profile-section" aria-label="Contact notes">
      <h2>Notes</h2>
      {#if contact.description}<div class="history-entry history-body">
          {contact.description}
        </div>{/if}
      <form
        method="POST"
        action="?/note"
        use:enhance={() => {
          noteBusy = true;
          noteError = '';
          return async ({ result, update }) => {
            noteBusy = false;
            if (result.type === 'success') {
              note = '';
              await update({ reset: false });
            } else
              noteError =
                result.type === 'failure'
                  ? String(result.data?.message ?? 'Could not save note.')
                  : 'Could not save note.';
          };
        }}
      >
        <textarea
          class="v2-input"
          name="comment"
          aria-label="New note"
          rows="3"
          placeholder="Write a note…"
          bind:value={note}></textarea>
        <button type="submit" class="v2-btn add-note" disabled={noteBusy || !note.trim()}
          >{noteBusy ? 'Saving…' : 'Add note'}</button
        >
        {#if noteError}<p class="v2-error" role="alert">{noteError}</p>{/if}
      </form>
      {#each data.notes as entry (entry.id)}
        <article class="history-entry">
          <div class="history-body">{entry.body}</div>
          <div class="entry-meta">{entry.by || 'Not recorded'} · {exactTime(entry.at)}</div>
        </article>
      {:else}<p class="v2-sub">No notes.</p>{/each}
    </section>
    <section class="profile-section activity" aria-label="Contact activity">
      <h2>Activity</h2>
      <div class="activity-feed">
        {#each data.activity as event (event.id)}
          <article class="history-entry">
            <div class="history-body">{event.body}</div>
            <div class="entry-meta">{event.by || 'Not recorded'} · {exactTime(event.at)}</div>
          </article>
        {:else}<p class="v2-sub">No activity.</p>{/each}
      </div>
    </section>
  </main>
  <aside class="contact-relations">
    <section class="profile-section">
      <h2>Companies</h2>
      {#each companies as company (company.id)}
        <a class="related-item" href={resolve(`/accounts/${company.id}`)}>{company.name}</a>
      {:else}<p class="v2-sub">{contact.organization || 'No associated companies.'}</p>{/each}
    </section>
    <section class="profile-section">
      <h2>Deals</h2>
      {#each data.deals as deal (deal.id)}
        <a class="related-item" href={resolve(`/pipeline/${deal.id}`)}>
          <strong>{deal.name}</strong><span>{money(deal.amount, deal.currency)}</span>
          <small>{STAGE_LABEL[deal.stage] ?? deal.stage}</small>
        </a>
      {:else}<p class="v2-sub">No associated deals.</p>{/each}
    </section>
    <section class="profile-section">
      <h2>Attachments</h2>
      <Attachments attachments={data.attachments} action="?/note" />
    </section>
    <details class="profile-section">
      <summary
        >Tasks ({data.tasks.length})
        <span class="review-badge" title="Pending review">Review</span></summary
      >
      {#each data.tasks as task (task.id)}<a
          class="related-item"
          href={resolve(`/tasks/${task.id}`)}>{task.title}</a
        >{/each}
    </details>
    <details class="profile-section">
      <summary
        >Tickets ({data.tickets.length})
        <span class="review-badge" title="Pending review">Review</span></summary
      >
      {#each data.tickets as ticket (ticket.id)}<a
          class="related-item"
          href={resolve(`/tickets/${ticket.id}`)}>{ticket.name}</a
        >{/each}
    </details>
  </aside>
</div>

<style>
  .properties-heading {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    margin-bottom: 16px;
  }
  .properties-heading h2 {
    margin: 0;
  }
  .property-values {
    display: grid;
    gap: 19px;
    margin: 22px 0 0;
  }
  .property-values dt {
    font-size: 11px;
    color: var(--v2-slate);
    margin-bottom: 6px;
  }
  .property-values dd {
    margin: 0;
    font-size: 13px;
    line-height: 1.5;
    overflow-wrap: anywhere;
  }
  .property-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
  }
  .stage-value {
    display: inline-block;
    padding: 3px 9px;
    border-radius: 5px;
    background: #eff6ff;
    color: #1d4ed8;
    font-size: 12px;
  }
  .scheduled-message {
    padding: 8px 22px;
    font-size: 13px;
    background: #f0fdf4;
    color: #166534;
  }
  .scheduled-message a {
    color: inherit;
    margin-left: 8px;
    text-decoration: underline;
  }

  .contact-profile {
    display: grid;
    grid-template-columns: minmax(180px, 300px) minmax(240px, 1fr) minmax(180px, 280px);
    grid-template-rows: minmax(0, 1fr);
    flex: 1;
    min-height: 0;
    overflow-x: auto;
    overflow-y: hidden;
    align-items: stretch;
  }
  .properties,
  .contact-center,
  .contact-relations {
    min-width: 0;
    min-height: 0;
    overflow-y: auto;
    overscroll-behavior-y: contain;
    padding: 16px;
  }
  .properties {
    border-right: 1px solid var(--v2-line);
  }
  .contact-relations {
    border-left: 1px solid var(--v2-line);
  }
  h2 {
    font-size: 15px;
    font-weight: 600;
    margin: 0 0 16px;
  }
  .profile-section {
    margin-bottom: 24px;
  }
  .activity-feed {
    max-height: 420px;
    min-height: 180px;
    overflow-y: auto;
    border: 1px solid var(--v2-line);
    border-radius: 8px;
    padding: 0 12px;
  }
  .history-entry {
    padding: 12px 0;
    border-bottom: 1px solid var(--v2-line-soft);
  }
  .history-body {
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    font-size: 13px;
  }
  .entry-meta,
  .creation-info {
    font-size: 11px;
    color: var(--v2-slate);
    margin-top: 6px;
  }
  .creation-info dd {
    margin: 3px 0 10px;
  }
  .related-item {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 10px 0;
    color: inherit;
    text-decoration: none;
    border-bottom: 1px solid var(--v2-line-soft);
    overflow-wrap: anywhere;
    font-size: 13px;
  }
  form {
    display: grid;
    gap: 8px;
    margin-bottom: 14px;
  }
  .add-note {
    justify-self: start;
    width: auto;
  }
  .review-badge {
    display: inline-block;
    margin-left: 6px;
    font-size: 9px;
    line-height: 1.3;
    font-weight: 500;
    padding: 2px 4px;
    color: #805b19;
    background: #fff3d6;
    border-radius: 4px;
  }
  summary {
    cursor: pointer;
  }
  @media (max-width: 700px) {
    .properties,
    .contact-center,
    .contact-relations {
      padding: 12px;
    }
  }
</style>
