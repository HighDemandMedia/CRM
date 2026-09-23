<script>
  import { configuredLabel } from '$lib/v2/pipeline-config.js';
  import { page } from '$app/state';

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
  import Pill from '$lib/v2/components/Pill.svelte';
  import { money, shortDate, longDate } from '$lib/v2/format.js';
  import {
    STAGE_LABEL,
    PRIORITY_TONE,
    INVOICE_STATUS_TONE,
    invoiceStatusLabel
  } from '$lib/v2/enums.js';
  import { ChevronRight, Mail } from '@lucide/svelte';

  /** @type {{ data: any, form?:any }} */
  let { data, form } = $props();

  let { account, deals, contacts, tickets, invoices, owners } = $derived(data);

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
      <PropertySummary target="Account" record={account}
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
          ['Stage', configuredLabel(page.data.pipelineConfig, 'Account', account.stage, account.stage_label) || '—'],
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

      {#if !page.data.demoMode}
      <!-- Invoices -->
      <details class="v2-card company-secondary">
        <summary
          >Invoices <span>{invoices.length}</span><span class="review-badge">Review</span></summary
        >
        <div class="v2-card-head">
          <span class="section-title"
            ><span class="v2-label">Invoices</span><span class="review-badge" title="Pending review"
              >Review</span
            ></span
          >
          <a href={resolve('/invoices')}>View all</a>
        </div>
        {#each invoices as inv (inv.id)}
          <!-- A link now: invoices is wired, so a real id sent to
               `/invoices/<uuid>` opens the invoice. -->
          <a
            href={resolve(`/invoices/${inv.id}`)}
            style="display:flex;gap:12px;align-items:center;padding:11px 15px;border-bottom:1px solid var(--v2-line-soft);color:inherit;text-decoration:none"
          >
            <span class="v2-num" style="font-size:12.5px">{inv.invoice_number}</span>
            <Pill tone={inv.past_due ? 'rust' : INVOICE_STATUS_TONE[inv.status]}>
              {inv.past_due ? 'Past due' : invoiceStatusLabel(inv.status)}
            </Pill>
            <span class="v2-num" style="margin-left:auto;font-weight:600;font-size:13px">
              {money(inv.past_due ? inv.amount_due : inv.total_amount, inv.currency)}
            </span>
          </a>
        {:else}
          <p class="v2-sub" style="padding:14px 15px;font-size:12.5px">Nothing billed yet.</p>
        {/each}
      </details>
      {/if}
    </div>
  </div>
</div>

<DeleteRecord kind="company" id={account.id} />

<style>
  .scheduled-message {
    padding: 8px 24px;
    font-size: 13px;
  }
  .properties-heading {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    margin-bottom: 16px;
  }
  .properties-heading h2 {
    margin: 0;
    font-size: 15px;
    font-weight: 600;
  }
  .property-pages {
    display: grid;
    gap: 8px;
    font-size: 13px;
    overflow-wrap: anywhere;
  }
  .property-pages > span {
    font-size: 11px;
    color: var(--v2-slate);
  }

  .section-title {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .review-badge {
    font-size: 9px;
    line-height: 1.3;
    font-weight: 500;
    padding: 2px 4px;
    color: #805b19;
    background: #fff3d6;
    border-radius: 4px;
  }

  .company-layout {
    display: grid;
    grid-template-columns: 300px minmax(340px, 1fr);
    padding: 20px 0 20px 22px;
    grid-template-rows: minmax(0, 1fr);
    min-height: 0;
  }
  .company-properties {
    min-height: 0;
    overflow-y: auto;
    padding: 20px;
    background: var(--v2-card);
    border: 0;
    border-radius: 12px;
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
    gap: 8px 20px;
    color: var(--v2-slate);
    font-size: 12px;
  }
  .deal-totals .overdue {
    color: #b42318;
  }
  .company-secondary > summary {
    cursor: pointer;
    padding: 14px 16px;
    font-size: 14px;
    font-weight: 600;
  }
  .company-secondary > summary span {
    margin-left: 8px;
    font-size: 12px;
    color: var(--v2-slate);
    font-weight: 400;
  }
  .secondary-content {
    padding: 0 16px 16px;
  }
  @media (max-width: 800px) {
    .company-layout {
      grid-template-columns: minmax(0, 1fr);
      grid-template-rows: auto auto;
      padding: 12px;
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
