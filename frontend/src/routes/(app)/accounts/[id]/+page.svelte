<script>
  import RecordAction from '$lib/v2/components/RecordAction.svelte';
  import { Mail, StickyNote } from '@lucide/svelte';
  let recordTabs;
  import RecordDisclosure from '$lib/v2/components/RecordDisclosure.svelte';
  import RecordActivityEntry from '$lib/v2/components/RecordActivityEntry.svelte';
  import { useI18n } from '$lib/i18n/context.js';
  const { exactTime, ui, money } = useI18n();

  import { page } from '$app/state';
  import { configuredLabel } from '$lib/v2/pipeline-config.js';

  import RecordTabs from '$lib/v2/components/RecordTabs.svelte';
  import EmailActivity from '$lib/components/EmailActivity.svelte';
  import RecordEmails from '$lib/components/RecordEmails.svelte';
  import RecordMailWatcher from '$lib/components/RecordMailWatcher.svelte';
  let mailStatus = $state(null);
  let recordTab = $state('activity'),
    selectedThread = $state('');
  let conversationRequest = $state(0);
  function showConversation(thread) {
    selectedThread = thread;
    conversationRequest++;
    recordTab = 'emails';
  }
  import NotesEditor from '$lib/components/deals/DealNotes.svelte';
  import CreateAppointment from '$lib/v2/components/CreateAppointment.svelte';
  let scheduled = $state(false);
  import ContactAssociations from '$lib/v2/components/ContactAssociations.svelte';
  import PropertySummary from '$lib/v2/components/PropertySummary.svelte';
  let editingProperties = $state(false);
  import Attachments from '$lib/v2/components/Attachments.svelte';
  import CompanyActions from '$lib/components/companies/CompanyActions.svelte';
  import { invalidateAll } from '$app/navigation';
  import { resolve } from '$app/paths';
  import RecordIdentity from '$lib/v2/components/RecordIdentity.svelte';
  import { can } from '$lib/v2/permissions.js';
  let composeRequest = $state(0);
  function composeEmail() {
    composeRequest++;
    recordTab = 'emails';
  }

  /** @type {{ data: any, form?:any }} */
  let { data } = $props();

  let { account, deals, contacts, tickets } = $derived(data);
  let editorAccountId = '';
  $effect(() => {
    if (editorAccountId === account.id) return;
    editorAccountId = account.id;
    editingProperties = false;
    composeRequest = 0;
  });

  let overdueDeals = $derived(account.overdue_deal_count ?? 0);
</script>

<RecordMailWatcher
  kind="company"
  id={account.id}
  active={recordTab !== 'notes'}
  onStatus={(status) => (mailStatus = { ...status, recordId: account.id })}
/>

{#if scheduled}<div class="scheduled-message" role="status">
    {ui('Event scheduled.')} <a href={resolve('/calendar')}>{ui('View calendar')}</a>
  </div>{/if}

<div class="v2-scroll company-layout">
  <RecordDisclosure class="company-properties" title={ui('Properties')} collapseBelowRem={48}>
    {#snippet header()}
      <RecordIdentity
        name={account.name || `Company · ${account.id.slice(0, 8)}`}
        email={account.email || ''}
        phone={account.phone || ''}
        backHref="/accounts"
        backLabel="Companies"
        onedit={can(page.data.permissions, 'companies', 'edit')
          ? () => (editingProperties = true)
          : undefined}
        editing={editingProperties}
        onclose={() => (editingProperties = false)}
        target="Account"
        record={account}
        schema={data.propertySchema}
        onemail={composeEmail}
      >
        {#snippet actions()}
          <RecordAction
            icon={StickyNote}
            label={ui('Add note')}
            onclick={() => recordTabs?.openNotes()}
          />
          <RecordAction icon={Mail} label={ui('New email')} onclick={composeEmail} />

          <CreateAppointment
            iconOnly
            hosts={data.hosts}
            defaultHost={data.defaultHost}
            selected={new Date()}
            defaultAttendee={{ id: account.id, name: account.name, type: 'company' }}
            action={`${resolve('/calendar')}?/create`}
            onCreated={() => {
              scheduled = true;
              void invalidateAll();
            }}
          />
          <CompanyActions company={account} disabled={editingProperties} />
        {/snippet}
      </RecordIdentity>
    {/snippet}
    <PropertySummary
      schema={data.propertySchema}
      target="Account"
      record={account}
      tags={account.tags}
      entries={[
        ['Last Activity', exactTime(account.last_activity_at)],
        ['Owner', data.owners?.join(', ') || '—'],
        [
          'Preferred Communication Channel',
          { SMS: 'SMS', CALL: 'Call', EMAIL: 'Email' }[account.preferred_communication_channel] ||
            '—'
        ],
        ['Tags', data.tags?.join(', ') || '—'],
        ['Domain', account.website || '—', 'website'],
        ['Language', account.language || '—'],
        ['Industry', account.industry || '—'],
        ['Number of employees', account.number_of_employees],
        [
          'Annual revenue',
          account.annual_revenue != null ? money(account.annual_revenue, account.currency) : '—'
        ],
        ['Source', account.source_label || '—'],
        [
          'Stage',
          configuredLabel(
            page.data.pipelineConfig,
            'Account',
            account.stage,
            account.stage_label
          ) || '—'
        ],
        ['Appointment', account.appointment_at ? exactTime(account.appointment_at) : '—'],
        ['Address', account.address_line || '—'],
        ['City', account.city || '—'],
        ['State', account.state || '—'],
        ['Zip Code', account.postcode || '—'],
        ['Country', account.country_display || '—'],
        ['Currency', account.currency],
        ['Pages', account.pages?.map((p) => p.name || p.url).join(', ') || '—']
      ]}
    />
  </RecordDisclosure>
  <div class="v2-pad company-content" style="padding-bottom:32px">
    <div class="company-workspace">
      <section class="v2-card" style="padding:16px">
        <ContactAssociations
          collapsible
          contactId={account.id}
          parentKind="company"
          kind="contact"
          detailed
          items={contacts.map((c) => ({
            ...c,
            name: [c.first_name, c.last_name].filter(Boolean).join(' ') || c.name || c.email
          }))}
        />
      </section>
      <section class="v2-card" style="padding:16px">
        <ContactAssociations
          collapsible
          contactId={account.id}
          parentKind="company"
          kind="deal"
          items={deals}
          detailed
        >
          {#snippet summary()}<div class="deal-totals">
              <span
                ><strong>{account.open_deal_count ?? 0}</strong>
                {ui('open ·')}
                {money(account.open_pipeline ?? 0, data.org.currency)}</span
              >
              <span class:overdue={overdueDeals > 0}
                ><strong>{overdueDeals}</strong> {ui('past due')}</span
              >
              <span>{ui('Won')} {money(account.won_amount ?? 0, data.org.currency)}</span>
            </div>{/snippet}
        </ContactAssociations>
      </section>
      <section class="v2-card company-journal" aria-label={ui('Company notes and activity')}>
        <RecordTabs bind:this={recordTabs} bind:active={recordTab} recordId={account.id}>
          {#snippet emails()}{#key account.id}<RecordEmails
                active={recordTab === 'emails'}
                liveStatus={mailStatus?.recordId === account.id ? mailStatus : null}
                kind="company"
                recipient={account.email || ''}
                id={account.id}
                {contacts}
                initialThread={selectedThread}
                initialRequest={conversationRequest}
                {composeRequest}
              />{/key}{/snippet}
          {#snippet notes()}{#key account.id}<NotesEditor
                notes={data.activity ?? []}
              />{/key}{/snippet}
          {#snippet activity()}<div class="company-history">
              {#each data.eventHistory ?? [] as entry (entry.id)}<div class="history-entry">
                  {#if entry.emailId}<EmailActivity
                      kind="company"
                      recordId={account.id}
                      id={entry.emailId}
                      href={entry.href}
                      mail={entry.email}
                      onConversation={showConversation}
                    />
                  {:else}<RecordActivityEntry event={entry} />{/if}
                </div>{:else}<p class="v2-sub">{ui('No activity yet.')}</p>{/each}
            </div>{/snippet}
        </RecordTabs>
      </section>
      <section class="v2-card company-secondary">
        <Attachments attachments={data.attachments} collapsible />
      </section>
      <section class="v2-card company-secondary">
        <ContactAssociations
          collapsible
          contactId={account.id}
          parentKind="company"
          kind="ticket"
          items={tickets}
        />
      </section>
    </div>
  </div>
</div>

<style>
  .scheduled-message {
    padding: var(--crm-space-2) var(--crm-space-6);
    font-size: var(--crm-text-sm);
  }

  .company-layout {
    display: grid;
    grid-template-columns: 300px minmax(340px, 1fr);
    padding: var(--crm-space-5) 0 var(--crm-space-5) var(--crm-space-6);
    grid-template-rows: minmax(0, 1fr);
    min-height: 0;
  }
  .company-layout :global(.company-properties) {
    min-width: 0;
    min-height: 0;
    overflow-y: auto;
    padding: var(--crm-space-5);
    background: var(--v2-card);
    border: 0;
    border-radius: var(--crm-radius-lg);
  }
  .company-content {
    min-width: 0;
    min-height: 0;
    overflow-y: auto;
  }

  .company-workspace {
    display: grid;
    gap: 14px;
  }
  .company-journal {
    padding: 18px;
  }
  .company-history {
    max-height: 340px;
    overflow-y: auto;
  }
  .history-entry {
    padding: 10px 0;
    border-bottom: 1px solid var(--v2-line-soft);
    overflow-wrap: anywhere;
  }
  .deal-totals {
    display: flex;
    flex-wrap: wrap;
    gap: var(--crm-space-2) var(--crm-space-5);
    color: var(--v2-slate);
    font-size: var(--crm-text-xs);
  }
  .deal-totals .overdue {
    color: var(--crm-danger);
  }
  .company-secondary {
    padding: 16px;
  }
  @container crm-workspace (max-width: 48rem) {
    .company-layout {
      grid-template-columns: minmax(0, 1fr);
      grid-template-rows: max-content max-content;
      padding: var(--crm-space-3);
      gap: 14px;
      overflow-y: auto;
    }
    .company-layout :global(.company-properties) {
      padding: var(--crm-space-2) var(--crm-space-4);
    }
    .company-layout :global(.company-properties),
    .company-content {
      overflow: visible;
    }
    .company-content {
      padding: 0;
    }
  }
</style>
