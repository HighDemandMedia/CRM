<script>
  import { useI18n } from '$lib/i18n/context.js';
  const { exactTime, ui } = useI18n();

  import EmailActivity from '$lib/components/EmailActivity.svelte';
  import PropertySummary from '$lib/v2/components/PropertySummary.svelte';
  import { configuredLabel } from '$lib/v2/pipeline-config.js';
  import { page } from '$app/state';

  import RecordTabs from '$lib/v2/components/RecordTabs.svelte';
  import DeleteRecord from '$lib/v2/components/DeleteRecord.svelte';
  import ContactAssociations from '$lib/v2/components/ContactAssociations.svelte';
  import ContactForm from '$lib/components/contacts/ContactForm.svelte';
  let editingProperties = $state(false);
  import Attachments from '$lib/v2/components/Attachments.svelte';
  import { resolve } from '$app/paths';
  import { invalidateAll } from '$app/navigation';
  import { enhance } from '$app/forms';
  import CreateAppointment from '$lib/v2/components/CreateAppointment.svelte';
  import TagBadge from '$lib/v2/components/TagBadge.svelte';
  import ContactActions from '$lib/components/contacts/ContactActions.svelte';
  let scheduled = $state(false);
  import PageHeader from '$lib/v2/components/PageHeader.svelte';

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

<PageHeader title={contact.name || `Contact · ${contact.id.slice(0, 8)}`} record>
  {#snippet sub()}{[contact.email, contact.phone].filter(Boolean).join(' · ')}{/snippet}
  {#snippet crumb()}<a href={resolve('/contacts')}>{ui('Contacts')}</a>{/snippet}
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
    {#if contact.email}<a class="v2-btn" href={`mailto:${contact.email}`}>{ui('Email')}</a
      >{:else}<button
        class="v2-btn"
        type="button"
        disabled
        title={ui('Add an email to this contact')}>{ui('Email')}</button
      >{/if}
  {/snippet}
</PageHeader>
{#if scheduled}<div class="scheduled-message" role="status">
    {ui('Event scheduled.')} <a href={resolve('/calendar')}>{ui('View calendar')}</a>
  </div>{/if}
<div class="contact-profile hdm-profile">
  <section class="properties hdm-panel" aria-label={ui('Contact properties')}>
    <div class="properties-heading">
      <h2>{ui('Properties')}</h2>
      <ContactActions
        {contact}
        disabled={editingProperties}
        onEdit={() => (editingProperties = true)}
      />
    </div>

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
      <PropertySummary
        target="Contact"
        record={contact}
        tags={contact.tags}
        entries={[
          ['Name', contact.name],
          ['Contact owner', data.owners?.join(', ')],
          ['Phone', contact.phone],
          ['Email', contact.email],
          ['Language', contact.language],
          ['Source', contact.source_label],
          [
            'Stage',
            configuredLabel(page.data.pipelineConfig, 'Contact', contact.stage, contact.stage_label)
          ],
          ['Preferred communication channel', contact.preferred_communication_channel_label],
          ['Appointment', contact.appointment_at ? exactTime(contact.appointment_at) : ''],
          ['Address', contact.address_line],
          ['City', contact.city],
          ['State', contact.state],
          ['Zip Code', contact.postcode],
          ['Country', contact.country],
          ['Tags', ''],
          ['Last Activity', exactTime(contact.last_activity_at)],
          ['Created', exactTime(contact.created_at)],
          ['Created by', contact.created_by_email || 'Not recorded']
        ]}
      />
    {/if}
  </section>
  <main class="contact-center hdm-panel">
    <RecordTabs>
      {#snippet notes()}
        <section class="profile-section" aria-label={ui('Contact notes')}>
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
              aria-label={ui('New note')}
              rows="3"
              placeholder={ui('Write a note…')}
              bind:value={note}></textarea>
            <button type="submit" class="v2-btn add-note" disabled={noteBusy || !note.trim()}
              >{noteBusy ? ui('Saving…') : ui('Add note')}</button
            >
            {#if noteError}<p class="v2-error" role="alert">{noteError}</p>{/if}
          </form>
          {#each data.notes as entry (entry.id)}
            <article class="history-entry">
              <div class="history-body">{entry.body}</div>
              <div class="entry-meta">{entry.by || ui('Not recorded')} · {exactTime(entry.at)}</div>
            </article>
          {:else}<p class="v2-sub">{ui('No notes.')}</p>{/each}
        </section>
      {/snippet}
      {#snippet activity()}
        <section class="profile-section activity" aria-label={ui('Contact activity')}>
          <div class="activity-feed">
            {#each data.activity as event (event.id)}
              <article class="history-entry">
                <div class="history-body">{event.body}</div>
                {#if event.emailId}<EmailActivity id={event.emailId} href={event.href} />{/if}
                <div class="entry-meta">
                  {event.by || ui('Not recorded')} · {exactTime(event.at)}
                </div>
              </article>
            {:else}<p class="v2-sub">{ui('No activity.')}</p>{/each}
          </div>
        </section>
      {/snippet}
    </RecordTabs>
  </main>
  <aside class="contact-relations hdm-panel hdm-relations">
    <div class="profile-section">
      <ContactAssociations contactId={contact.id} kind="company" items={companies} />
    </div>
    <div class="profile-section">
      <ContactAssociations contactId={contact.id} kind="deal" items={data.deals} />
    </div>
    <section class="profile-section">
      <Attachments attachments={data.attachments} action="?/note" />
    </section>
    <div class="profile-section">
      <ContactAssociations contactId={contact.id} kind="ticket" items={data.tickets} />
    </div>
  </aside>
</div>

<DeleteRecord kind="contact" id={contact.id} />

<style>
  .properties-heading {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    margin-bottom: var(--crm-space-4);
  }
  .properties-heading h2 {
    margin: 0;
  }
  .scheduled-message {
    padding: var(--crm-space-2) var(--crm-space-6);
    font-size: var(--crm-text-sm);
    background: var(--crm-success-bg);
    color: var(--crm-success);
  }
  .scheduled-message a {
    color: inherit;
    margin-left: var(--crm-space-2);
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
    padding: var(--crm-space-4);
  }
  .properties {
    border-right: 1px solid var(--v2-line);
  }
  .contact-relations {
    border-left: 1px solid var(--v2-line);
  }
  h2 {
    font-size: var(--crm-text-sm);
    font-weight: 600;
    margin: 0 0 var(--crm-space-4);
  }
  .profile-section {
    margin-bottom: var(--crm-space-6);
  }
  .activity-feed {
    min-height: 180px;
    padding: 0;
  }
  .history-entry {
    padding: var(--crm-space-3) 0;
    border-bottom: 1px solid var(--v2-line-soft);
  }
  .history-body {
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    font-size: var(--crm-text-sm);
  }
  .entry-meta {
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
    margin-top: 6px;
  }

  form {
    display: grid;
    gap: var(--crm-space-2);
    margin-bottom: 14px;
  }
  .add-note {
    justify-self: start;
    width: auto;
  }

  @media (max-width: 700px) {
    .properties,
    .contact-center,
    .contact-relations {
      padding: var(--crm-space-3);
    }
  }
</style>
