<script>
  import Notice from '$lib/components/Notice.svelte';
  import RecordActivityEntry from '$lib/v2/components/RecordActivityEntry.svelte';
  import RecordDisclosure from '$lib/v2/components/RecordDisclosure.svelte';
  import { useI18n } from '$lib/i18n/context.js';
  const { exactTime, ui } = useI18n();

  import EmailActivity from '$lib/components/EmailActivity.svelte';
  import RecordEmails from '$lib/components/RecordEmails.svelte';
  let recordTab = $state('activity'),
    selectedThread = $state('');
  let conversationRequest = $state(0);
  function showConversation(thread) {
    selectedThread = thread;
    conversationRequest++;
    recordTab = 'emails';
  }
  import PropertySummary from '$lib/v2/components/PropertySummary.svelte';
  import { configuredLabel } from '$lib/v2/pipeline-config.js';
  import { page } from '$app/state';

  import RecordTabs from '$lib/v2/components/RecordTabs.svelte';
  import ContactAssociations from '$lib/v2/components/ContactAssociations.svelte';
  let editingProperties = $state(false);
  function openEditor() {
    editingProperties = true;
  }
  let editorContactId = '';
  $effect(() => {
    // A reused route component must not carry another contact's editor.
    const id = contact.id;
    if (editorContactId === id) return;
    editorContactId = id;
    composeRequest = 0;
    editingProperties = false;
  });
  import Attachments from '$lib/v2/components/Attachments.svelte';
  import { resolve } from '$app/paths';
  import { invalidateAll } from '$app/navigation';
  import { enhance } from '$app/forms';
  import CreateAppointment from '$lib/v2/components/CreateAppointment.svelte';
  import ContactActions from '$lib/components/contacts/ContactActions.svelte';
  let scheduled = $state(false);
  import RecordIdentity from '$lib/v2/components/RecordIdentity.svelte';
  import { can } from '$lib/v2/permissions.js';
  let composeRequest = $state(0);
  function composeEmail() {
    composeRequest++;
    recordTab = 'emails';
  }

  /** @type {{data:any, form:any}} */
  let { data } = $props();
  let contact = $derived(data.contact);
  let companies = $derived([
    ...(contact.account ? [contact.account] : []),
    ...contact.other_accounts
  ]);
  let note = $state('');
  let noteBusy = $state(false);
  let noteError = $state('');
</script>

{#if scheduled}<div class="scheduled-message" role="status">
    {ui('Event scheduled.')} <a href={resolve('/calendar')}>{ui('View calendar')}</a>
  </div>{/if}
<div class="contact-profile hdm-profile">
  <RecordDisclosure title={ui('Properties')} class="properties">
    {#snippet header()}
      <RecordIdentity
        name={contact.name || `Contact · ${contact.id.slice(0, 8)}`}
        email={contact.email || ''}
        phone={contact.phone || ''}
        backHref="/contacts"
        backLabel="Contacts"
        onedit={can(page.data.permissions, 'contacts', 'edit') ? openEditor : undefined}
        editing={editingProperties}
        onclose={() => (editingProperties = false)}
        target="Contact"
        record={contact}
        schema={data.propertySchema}
        onemail={composeEmail}
      >
        {#snippet actions()}
          <ContactActions
            showEdit={false}
            {contact}
            disabled={editingProperties}
            onEdit={openEditor}
          />
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
        {/snippet}
      </RecordIdentity>
    {/snippet}

    <PropertySummary
      schema={data.propertySchema}
      target="Contact"
      record={contact}
      tags={contact.tags}
      entries={[
        ['Contact owner', data.owners?.join(', ')],
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
        ['Created by', contact.created_by || contact.created_by_email || 'Not recorded']
      ]}
    />
  </RecordDisclosure>
  <section class="hdm-panel contact-relations hdm-relations" aria-label={ui('Associated Objects')}>
    <div class="profile-section">
      <ContactAssociations collapsible contactId={contact.id} kind="company" items={companies} />
    </div>
    <div class="profile-section">
      <ContactAssociations collapsible contactId={contact.id} kind="deal" items={data.deals} />
    </div>
    <section class="profile-section">
      <Attachments collapsible attachments={data.attachments} action="?/note" />
    </section>
    <div class="profile-section">
      <ContactAssociations collapsible contactId={contact.id} kind="ticket" items={data.tickets} />
    </div>
  </section>
  <main class="contact-center hdm-panel">
    <RecordTabs bind:active={recordTab} recordId={contact.id}>
      {#snippet emails()}{#key contact.id}<RecordEmails
            active={recordTab === 'emails'}
            kind="contact"
            recipient={contact.email || ''}
            id={contact.id}
            initialThread={selectedThread}
            initialRequest={conversationRequest}
            {composeRequest}
          />{/key}{/snippet}
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
            {#if noteError}<Notice message={noteError} />{/if}
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
                {#if event.emailId}<EmailActivity
                    kind="contact"
                    recordId={contact.id}
                    id={event.emailId}
                    href={event.href}
                    mail={event.email}
                    onConversation={showConversation}
                  />
                {:else}<RecordActivityEntry {event} />
                {/if}
              </article>
            {:else}<p class="v2-sub">{ui('No activity.')}</p>{/each}
          </div>
        </section>
      {/snippet}
    </RecordTabs>
  </main>
</div>

<style>
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
</style>
