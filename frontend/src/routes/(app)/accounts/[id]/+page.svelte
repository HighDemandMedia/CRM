<script>
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
  /**
   * The account is a workspace, not a form.
   *
   * v1 rendered an account as ~28 stacked label/value rows, so answering
   * "what is going on with Northwind?" meant visiting four other pages. Here
   * the deals, people, tickets and invoices are on the page, and the next
   * action names the problem that spans them.
   *
   * All four panels come from the single detail response, the API already
   * returned them, so this costs no extra round trips.
   */
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import NextAction from '$lib/v2/components/NextAction.svelte';
  import StatCard from '$lib/v2/components/StatCard.svelte';
  import Pill from '$lib/v2/components/Pill.svelte';
  import Avatar from '$lib/v2/components/Avatar.svelte';
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

  let openDeals = $derived(deals.filter((/** @type {any} */ d) => !d.stage.startsWith('CLOSED_')));
  let stalled = $derived(openDeals.filter((/** @type {any} */ d) => d.aging_status === 'red'));
  // `past_due` is decided by the same rule as the header figure. See
  // `isPastDue` in the data layer. The invoice's own `is_overdue` flag counts
  // drafts, and a rail that disagrees with its header discredits both.
  let pastDue = $derived(invoices.filter((/** @type {any} */ i) => i.past_due));

  /** One sentence that connects problems across objects. Every clause is a
      fact on this page: a stalled deal, or an invoice past its due date. */
  let headline = $derived(
    stalled.length && pastDue.length
      ? `${stalled[0].name} is stalled and ${pastDue[0].invoice_number} is past due, same account, two problems.`
      : stalled.length
        ? `${stalled[0].name} has not moved in ${stalled[0].days_in_current_stage} days.`
        : pastDue.length
          ? `${pastDue[0].invoice_number} is past due, ${money(pastDue[0].amount_due, pastDue[0].currency)}.`
          : null
  );
</script>

<PageHeader title={account.name} record>
  {#snippet crumb()}
    <a href={resolve('/accounts')}>Companies</a>
    <ChevronRight size={12} />
    <span>{account.industry || 'No industry'}</span>
  {/snippet}
  {#snippet sub()}
    {[
      account.industry,
      account.number_of_employees ? `${account.number_of_employees} staff` : null,
      /* Derived: the close date of the first deal won here. There is no
         contract model, so this is what "customer since" can honestly mean. */
      account.first_won_on
        ? `customer since ${longDate(account.first_won_on)}`
        : 'No deals won yet',
      owners.length ? `owned by ${owners[0]}` : null
    ]
      .filter(Boolean)
      .join(' · ')}
  {/snippet}

  {#snippet actions()}
    <CreateAppointment
      hosts={data.hosts}
      defaultHost={data.defaultHost}
      selected={new Date()}
      defaultAttendee={{ id: account.id, name: account.name, type: 'company' }}
      action={`${resolve('/calendar')}?/create`}
      onCreated={() => { scheduled = true; void invalidateAll(); }}
    />
  {/snippet}
</PageHeader>
{#if scheduled}<div class="scheduled-message" role="status">Event scheduled. <a href={resolve('/calendar')}>View calendar</a></div>{/if}

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
        entries={[
          ['Name', account.name],
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
          ['Stage', account.stage_label || '—'],
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
    <div class="v2-stats" style="margin-bottom:16px">
      <StatCard
        label="Revenue won"
        value={account.won_amount ? money(account.won_amount, data.org.currency) : '—'}
        tone={account.won_amount ? 'moss' : 'slate'}
        detail={account.won_count
          ? `${account.won_count} deal${account.won_count === 1 ? '' : 's'} won`
          : 'Nothing won yet'}
      />
      <StatCard
        label="Open pipeline"
        value={account.open_pipeline ? money(account.open_pipeline, data.org.currency) : '—'}
        detail={account.open_deal_count
          ? `${account.open_deal_count} open deal${account.open_deal_count === 1 ? '' : 's'}`
          : 'No open deals'}
      />
      <StatCard
        label="Past due"
        value={account.overdue_amount ? money(account.overdue_amount, data.org.currency) : '—'}
        tone={account.overdue_amount ? 'rust' : 'slate'}
        detail={pastDue.length
          ? pastDue.map((/** @type {any} */ i) => i.invoice_number).join(', ')
          : 'Nothing past due'}
      />
      <StatCard
        label="Open tickets"
        value={String(account.open_tickets ?? 0)}
        tone={tickets.some((/** @type {any} */ t) => t.priority === 'Urgent') ? 'rust' : 'slate'}
        detail={tickets.length ? `${tickets[0].name} · ${tickets[0].priority}` : 'None open'}
      />
    </div>

    {#if headline}
      <div style="margin-bottom:16px">
        <!--
          The invoice half of this had an `href` it should not have had: it
          pointed at `/invoices/<uuid>` while invoices is still fixtures
          keyed by slugs, so the one button on the page labelled "the thing
          that needs you" answered 404. Found by following the page's own
          outbound links rather than by reading it.

          Without an `href` the action stays a button that does nothing, which
          is the same wrong answer more quietly, so when the target is not
          wired the action is dropped entirely and the sentence stands on its
          own. It comes back when invoices is.
        -->
        <NextAction
          label="Needs you"
          text={headline}
          action={stalled.length ? 'Open the deal' : null}
          href={stalled.length ? `/pipeline/${stalled[0].id}` : null}
          tone="rust"
        />
      </div>
    {/if}

    <!-- align-items:start so each card is its own height. Stretched to match
         its neighbour, a one-row panel ends in a tall blank area that reads as
         content that failed to load. -->
    <div
      style="display:grid;grid-template-columns:1fr 1fr;gap:14px;align-items:start"
      class="v2-account-grid"
    >
      <section class="v2-card" style="padding:16px">
        <ContactAssociations
          contactId={account.id}
          parentKind="company"
          kind="contact"
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
        />
      </section>
      <section class="v2-card company-attachments" aria-label="Company notes">
        <h2>Notes</h2>
        <div style="max-height:320px;overflow-y:auto">
          {#each data.activity ?? [] as note (note.id)}
            <div style="padding:10px 0;border-bottom:1px solid var(--v2-line)">
              <div style="white-space:pre-wrap;overflow-wrap:anywhere">{note.body}</div>
              <p class="v2-sub">{note.by} · {exactTime(note.at)}</p>
            </div>
          {:else}<p class="v2-sub">No notes yet.</p>{/each}
        </div>
      </section>
      {#if data.eventHistory?.length}<section class="v2-card company-attachments">
          <h2>Activity</h2>
          {#each data.eventHistory as entry (entry.id)}<div
              style="padding:10px 0;border-bottom:1px solid var(--v2-line)"
            >
              <div>{entry.body}</div>
              <p class="v2-sub">{entry.by} · {exactTime(entry.at)}</p>
            </div>{/each}
        </section>{/if}
      <section class="v2-card company-attachments">
        <h2>Attachments</h2>
        <Attachments attachments={data.attachments} />
      </section>

      <!-- Tickets -->
      <section class="v2-card" style="overflow:hidden">
        <div class="v2-card-head">
          <span class="section-title"
            ><span class="v2-label">Tickets</span><span class="review-badge" title="Pending review"
              >Review</span
            ></span
          >
          <a href={resolve('/tickets')}>View all</a>
        </div>
        {#each tickets as t (t.id)}
          <!-- A link again: tickets is wired, so a real id sent to
               `/tickets/<uuid>` opens the ticket. -->
          <a
            href={resolve(`/tickets/${t.id}`)}
            style="display:flex;gap:12px;align-items:center;padding:11px 15px;border-bottom:1px solid var(--v2-line-soft);color:inherit;text-decoration:none"
          >
            <span style="flex:1;font-size:13px;min-width:0">{t.name}</span>
            <span class="v2-sub" style="font-size:11.5px">{t.status}</span>
            <Pill tone={PRIORITY_TONE[t.priority]}>{t.priority}</Pill>
          </a>
        {:else}
          <p class="v2-sub" style="padding:14px 15px;font-size:12.5px">
            No tickets. <a href={resolve(`/tickets/new?account=${account.id}`)}>Raise one</a> if something
            is wrong.
          </p>
        {/each}
      </section>

      <!-- Invoices -->
      <section class="v2-card" style="overflow:hidden">
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
      </section>
    </div>
  </div>
</div>

<DeleteRecord kind="company" id={account.id} />

<style>
  .scheduled-message { padding: 8px 24px; font-size: 13px; }
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
    grid-template-columns: 260px minmax(340px, 1fr);
    grid-template-rows: minmax(0, 1fr);
    min-height: 0;
  }
  .company-properties {
    min-height: 0;
    overflow-y: auto;
    padding: 20px;
    border-right: 1px solid var(--v2-line);
  }
  .company-properties h2 {
    font-size: 15px;
    margin: 0 0 20px;
  }
  .company-content {
    min-width: 0;
    min-height: 0;
    overflow-y: auto;
  }

  .company-attachments {
    padding: 16px;
  }
  .company-attachments h2 {
    font-size: 14px;
    margin: 0 0 14px;
  }

  @media (max-width: 1080px) {
    .v2-account-grid {
      grid-template-columns: 1fr !important;
    }
  }
</style>
