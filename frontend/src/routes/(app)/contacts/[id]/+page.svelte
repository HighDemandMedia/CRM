<script>
  import RecordActivityEntry from '$lib/v2/components/RecordActivityEntry.svelte';
  import RecordDisclosure from '$lib/v2/components/RecordDisclosure.svelte';
  import Notice from '$lib/components/Notice.svelte';
  import { onDestroy } from 'svelte';
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
  import DeleteRecord from '$lib/v2/components/DeleteRecord.svelte';
  import ContactAssociations from '$lib/v2/components/ContactAssociations.svelte';
  import ContactForm from '$lib/components/contacts/ContactForm.svelte';
  let editingProperties = $state(false);
  let editor = $state(null);
  let editorBusy = $state(false);
  let editorError = $state('');
  let editorController;
  onDestroy(() => editorController?.abort());
  async function openEditor() {
    editorController?.abort();
    const controller = new AbortController();
    editorController = controller;
    const id = contact.id;
    editorBusy = true;
    editorError = '';
    try {
      const response = await fetch(`/api/contact-editor/${id}`, { signal: controller.signal });
      if (!response.ok) throw new Error();
      const result = await response.json();
      if (contact.id !== id || controller.signal.aborted) return;
      editor = result;
      editingProperties = true;
    } catch (error) {
      if (!controller.signal.aborted && contact.id === id)
        editorError = 'Could not load contact. Please try again.';
    } finally {
      if (editorController === controller) editorBusy = false;
    }
  }
  let editorContactId = '';
  $effect(() => {
    // A reused route component must not carry another contact's editor.
    const id = contact.id;
    if (editorContactId === id) return;
    editorContactId = id;
    editingProperties = false;
    editor = null;
    editorError = '';
  });
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
  <RecordDisclosure title={ui('Properties')} class="properties">
    <div class="properties-heading">
      <ContactActions {contact} disabled={editingProperties || editorBusy} onEdit={openEditor} />
    </div>

    {#if editorBusy}<p role="status">{ui('Loading…')}</p>{/if}
    {#if editorError}<Notice message={ui(editorError)}
        >{#snippet actions()}
          <button type="button" class="v2-btn v2-btn-sm" onclick={openEditor}>{ui('Retry')}</button>
        {/snippet}</Notice
      >{/if}
    {#if editingProperties && editor}
      <ContactForm
        data={editor}
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
          ['Created by', contact.created_by || contact.created_by_email || 'Not recorded']
        ]}
      />
    {/if}
    <DeleteRecord kind="contact" id={contact.id} />
  </RecordDisclosure>
  <RecordDisclosure title={ui('Associated Objects')} class="contact-relations hdm-relations">
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
  </RecordDisclosure>
  <main class="contact-center hdm-panel">
    <RecordTabs bind:active={recordTab} recordId={contact.id}>
      {#snippet emails()}{#key contact.id}<RecordEmails
            active={recordTab === 'emails'}
            kind="contact"
            recipient={contact.email || ''}
            id={contact.id}
            initialThread={selectedThread}
            initialRequest={conversationRequest}
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
  .properties-heading {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    justify-content: space-between;
    gap: 10px;
    margin-bottom: var(--crm-space-4);
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
