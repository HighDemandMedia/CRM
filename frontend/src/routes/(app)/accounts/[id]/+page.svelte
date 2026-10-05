<script>
  import { page } from '$app/state';
  import { configuredLabel } from '$lib/v2/pipeline-config.js';

  import RecordTabs from '$lib/v2/components/RecordTabs.svelte';
  import NotesEditor from '$lib/components/deals/DealNotes.svelte';
  import CreateAppointment from '$lib/v2/components/CreateAppointment.svelte';
  let scheduled = $state(false);
  import DeleteRecord from '$lib/v2/components/DeleteRecord.svelte';
  import ContactAssociations from '$lib/v2/components/ContactAssociations.svelte';
  import PropertySummary from '$lib/v2/components/PropertySummary.svelte';
  import { Pencil } from '@lucide/svelte';
  let editingProperties = $state(false);
  import { exactTime } from '$lib/v2/contact-time.js';
  import Attachments from '$lib/v2/components/Attachments.svelte';
  import CompanyForm from '$lib/components/companies/CompanyForm.svelte';
  import { invalidateAll } from '$app/navigation';
  import { resolve } from '$app/paths';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import { money } from '$lib/v2/format.js';
  import { ChevronRight, Mail } from '@lucide/svelte';

  /** @type {{ data: any, form?:any }} */
  let { data, form } = $props();

  let { account, deals, contacts, tickets } = $derived(data);

  let overdueDeals = $derived(account.overdue_deal_count ?? 0);
</script>

<PageHeader title={account.name || `Company · ${account.id.slice(0, 8)}`} record>
  {#snippet crumb()}
    <a href={resolve('/accounts')}>Companies</a>
    <ChevronRight size={12} />
    <span>{account.industry || 'No industry'}</span>
  {/snippet}
  {#snippet sub()}
    {[account.website, account.industry].filter(Boolean).join(' · ')}
  {/snippet}

  {#snippet actions()}
    {#if account.email}<a class="v2-btn" href={`mailto:${account.email}`}><Mail size={15} />Email</a
      >{/if}
    <CreateAppointment
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
  {/snippet}
</PageHeader>
{#if scheduled}<div class="scheduled-message" role="status">
    Event scheduled. <a href={resolve('/calendar')}>View calendar</a>
  </div>{/if}

<div class="v2-scroll company-layout">
  <aside class="company-properties" aria-label="Company properties">
    <div class="properties-heading">
      <h2>Properties</h2>
      <button
        class="v2-btn"
        type="button"
        disabled={editingProperties}
        onclick={() => (editingProperties = true)}><Pencil size={13} />Edit</button
      >
    </div>
    {#if editingProperties}
      <CompanyForm
        data={{ ...data.editor, org: data.org }}
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
        target="Account"
        record={account}
        tags={account.tags}
        entries={[
          ['Name', account.name],
          ['Last Activity', exactTime(account.last_activity_at)],
          ['Owner', data.owners?.join(', ') || '—'],
          ['Phone', account.phone || '—'],
          ['Email', account.email || '—'],
          [
            'Preferred Communication Channel',
            { SMS: 'SMS', CALL: 'Call', EMAIL: 'Email' }[account.preferred_communication_channel] ||
              '—'
          ],
          ['Tags', data.tags?.join(', ') || '—'],
          ['Domain', account.website || '—'],
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
          ['Address', data.editor.form.address_line || '—'],
          ['City', account.city || '—'],
          ['State', data.editor.form.state || '—'],
          ['Zip Code', data.editor.form.postcode || '—'],
          ['Country', account.country_display || '—']
        ]}
      />
      {#if account.pages?.length}<div class="property-pages">
          <span>Pages</span>{#each account.pages as page}<a
              href={page.url}
              target="_blank"
              rel="noopener noreferrer">{page.name || page.url}</a
            >{/each}
        </div>{/if}
    {/if}
  </aside>
  <div class="v2-pad company-content" style="padding-bottom:32px">
    <div class="company-workspace">
      <section class="v2-card" style="padding:16px">
        <ContactAssociations
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
          contactId={account.id}
          parentKind="company"
          kind="deal"
          items={deals}
          detailed
        >
          {#snippet summary()}<div class="deal-totals">
              <span
                ><strong>{account.open_deal_count ?? 0}</strong> open · {money(
                  account.open_pipeline ?? 0,
                  data.org.currency
                )}</span
              >
              <span class:overdue={overdueDeals > 0}><strong>{overdueDeals}</strong> past due</span>
              <span>Won {money(account.won_amount ?? 0, data.org.currency)}</span>
            </div>{/snippet}
        </ContactAssociations>
      </section>
      <section class="v2-card company-journal" aria-label="Company notes and activity">
        <RecordTabs>
          {#snippet notes()}{#key account.id}<NotesEditor
                notes={data.activity ?? []}
              />{/key}{/snippet}
          {#snippet activity()}<div class="company-history">
              {#each data.eventHistory ?? [] as entry (entry.id)}<div class="history-entry">
                  <div>{entry.body}</div>
                  <p class="v2-sub">{entry.by} · {exactTime(entry.at)}</p>
                </div>{:else}<p class="v2-sub">No activity yet.</p>{/each}
            </div>{/snippet}
        </RecordTabs>
      </section>
      <details class="v2-card company-secondary">
        <summary>Attachments <span>{data.attachments.length}</span></summary>
        <div class="secondary-content"><Attachments attachments={data.attachments} /></div>
      </details>
      <details class="v2-card company-secondary">
        <summary>Tickets <span>{tickets.length}</span></summary>
        <div class="secondary-content">
          <ContactAssociations
            contactId={account.id}
            parentKind="company"
            kind="ticket"
            items={tickets}
          />
        </div>
      </details>
    </div>
  </div>
</div>

<DeleteRecord kind="company" id={account.id} />

<style>
  .scheduled-message {
    padding: var(--crm-space-2) var(--crm-space-6);
    font-size: var(--crm-text-sm);
  }
  .properties-heading {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    margin-bottom: var(--crm-space-4);
  }
  .properties-heading h2 {
    margin: 0;
    font-size: var(--crm-text-sm);
    font-weight: 600;
  }
  .property-pages {
    display: grid;
    gap: var(--crm-space-2);
    font-size: var(--crm-text-sm);
    overflow-wrap: anywhere;
  }
  .property-pages > span {
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
  }

  .company-layout {
    display: grid;
    grid-template-columns: 300px minmax(340px, 1fr);
    padding: var(--crm-space-5) 0 var(--crm-space-5) var(--crm-space-6);
    grid-template-rows: minmax(0, 1fr);
    min-height: 0;
  }
  .company-properties {
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
  .company-secondary > summary {
    cursor: pointer;
    padding: 14px var(--crm-space-4);
    font-size: var(--crm-text-sm);
    font-weight: 600;
  }
  .company-secondary > summary span {
    margin-left: var(--crm-space-2);
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
    font-weight: 400;
  }
  .secondary-content {
    padding: 0 var(--crm-space-4) var(--crm-space-4);
  }
  @media (max-width: 800px) {
    .company-layout {
      grid-template-columns: minmax(0, 1fr);
      grid-template-rows: auto auto;
      padding: var(--crm-space-3);
      gap: 14px;
      overflow-y: auto;
    }
    .company-properties,
    .company-content {
      overflow: visible;
    }
    .company-content {
      padding: 0;
    }
  }
</style>
