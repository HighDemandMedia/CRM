<script>
  import { exactTime } from '$lib/v2/contact-time.js';
  import { configuredStages } from '$lib/v2/pipeline-config.js';
  import { page } from '$app/state';

  import RecordTabs from '$lib/v2/components/RecordTabs.svelte';
  import StageProgress from '$lib/v2/components/StageProgress.svelte';
  import DeleteRecord from '$lib/v2/components/DeleteRecord.svelte';
  import ContactAssociations from '$lib/v2/components/ContactAssociations.svelte';
  import PropertySummary from '$lib/v2/components/PropertySummary.svelte';
  import { Pencil } from '@lucide/svelte';
  let editingProperties = $state(false);
  import Attachments from '$lib/v2/components/Attachments.svelte';
  import DealNotes from '$lib/components/deals/DealNotes.svelte';
  import DealForm from '$lib/components/deals/DealForm.svelte';
  import { invalidateAll } from '$app/navigation';
  import { resolve } from '$app/paths';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import Timeline from '$lib/v2/components/Timeline.svelte';
  import { money, longDate } from '$lib/v2/format.js';
  import { STAGES, STAGE_LABEL } from '$lib/v2/enums.js';
  import { ChevronRight } from '@lucide/svelte';

  /** @type {{ data: any, form?:any }} */
  let { data, form } = $props();

  let { deal, lineItems, contacts } = $derived(data);
  let stageOptions = $derived(
    configuredStages(
      page.data.pipelineConfig,
      'Opportunity',
      STAGES.map((value) => ({ value, label: STAGE_LABEL[value] }))
    )
  );

  /**
   * The discount is per line item: `OpportunityLineItem.save()` computes
   * subtotal, then discount_amount, then total, and Opportunity has no
   * discount field at all. So the footer adds up what the lines actually
   * carry; it does not derive a deal-level discount from the difference
   * between the lines and `deal.amount`. That difference cannot exist:
   * `recalculate_amount()` sets amount to the sum of the line totals.
   */
  let subtotal = $derived(lineItems.reduce((a, li) => a + li.subtotal, 0));
  let discount = $derived(lineItems.reduce((a, li) => a + li.discount_amount, 0));
</script>

<PageHeader title={deal.name || `Deal · ${deal.id.slice(0, 8)}`} record>
  {#snippet crumb()}
    <a href={resolve('/pipeline')}>Deals</a>
    <ChevronRight size={12} />
    {#if deal.account.id}<a href={resolve(`/accounts/${deal.account.id}`)}>{deal.account.name}</a
      >{/if}
  {/snippet}
</PageHeader>

<div class="deal-layout">
  <div class="v2-main">
    <section class="deal-overview" aria-label="Deal overview">
      <div class="deal-value">
        <span>Amount</span><strong>{money(deal.amount, deal.currency)}</strong>
      </div>
      <div>
        <span class="overview-label">Stage</span><StageProgress
          stage={deal.stage}
          stages={stageOptions}
        />
      </div>
      <div>
        <span class="overview-label">Close date</span><strong
          >{deal.closed_on ? longDate(deal.closed_on) : '—'}</strong
        >
      </div>
      <div><span class="overview-label">Deal owner</span><strong>{deal.owner || '—'}</strong></div>
      {#if deal.days_in_current_stage > 0}<p class="stage-age">
          {deal.days_in_current_stage}
          {deal.days_in_current_stage === 1 ? 'day' : 'days'} in stage
        </p>{/if}
    </section>

    <div class="v2-scroll">
      <div class="v2-pad" style="padding-top:14px;padding-bottom:32px">
        <section class="v2-card deal-journal" aria-label="Deal notes and activity">
          <RecordTabs>
            {#snippet notes()}{#key deal.id}<DealNotes notes={data.notes} />{/key}{/snippet}
            {#snippet activity()}<div class="deal-history">
                <Timeline events={data.activity} />
              </div>{/snippet}
          </RecordTabs>
        </section>
        <details class="v2-card deal-secondary">
          <summary>Attachments <span>{data.attachments.length}</span></summary>
          <div class="secondary-content"><Attachments attachments={data.attachments} /></div>
        </details>

        {#if lineItems.length}
          <details class="v2-card deal-secondary">
            <summary>Line items <span>{lineItems.length}</span></summary>
            <div class="line-items-scroll">
              <table class="v2-table">
                <thead>
                  <tr>
                    <th>Product</th>
                    <th class="v2-r">Qty</th>
                    <th class="v2-r">Unit price</th>
                    <th class="v2-r">Discount</th>
                    <th class="v2-r">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {#each lineItems as li (li.id)}
                    <tr>
                      <td>{li.name}</td>
                      <td class="v2-r v2-num">{li.quantity}</td>
                      <td class="v2-r v2-num">{money(li.unit_price, deal.currency)}</td>
                      <!-- Blank, not "0", where there is no discount. A column of
                         zeroes reads as a discount that happened to be nothing. -->
                      <td class="v2-r v2-num v2-muted">
                        {li.discount_amount > 0
                          ? `−${money(li.discount_amount, deal.currency)}`
                          : ''}
                      </td>
                      <td class="v2-r v2-num">{money(li.total, deal.currency)}</td>
                    </tr>
                  {/each}
                </tbody>
              </table>
              <div
                style="display:flex;justify-content:flex-end;gap:24px;padding:11px 14px;border-top:1px solid var(--v2-line);font-size:13px"
              >
                {#if discount > 0}
                  <span class="v2-muted">Subtotal</span>
                  <span class="v2-num v2-muted">{money(subtotal, deal.currency)}</span>
                  <span class="v2-muted">Discounts</span>
                  <span class="v2-num v2-muted">−{money(discount, deal.currency)}</span>
                {/if}
                <span style="font-weight:650">Total</span>
                <span class="v2-num" style="font-weight:650"
                  >{money(deal.amount, deal.currency)}</span
                >
              </div>
            </div>
          </details>
        {/if}
      </div>
    </div>
  </div>

  <aside class="v2-rail deal-properties" aria-label="Deal properties">
    <div style="margin-bottom:20px">
      <ContactAssociations
        contactId={deal.id}
        parentKind="deal"
        kind="contact"
        detailed
        items={contacts.map((c) => ({
          ...c,
          name: [c.first_name, c.last_name].filter(Boolean).join(' ') || c.name || c.email
        }))}
      />
    </div>
    <div style="margin-bottom:20px">
      <ContactAssociations
        contactId={deal.id}
        parentKind="deal"
        kind="company"
        items={deal.account?.id ? [deal.account] : []}
      />
    </div>

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
      <DealForm
        data={data.editor}
        result={form}
        editing
        inline
        showNotes={false}
        onCancel={() => (editingProperties = false)}
        onSaved={async () => {
          await invalidateAll();
          editingProperties = false;
        }}
      />
    {:else}
      <PropertySummary
        target="Opportunity"
        record={deal}
        tags={deal.tags}
        entries={[
          ['Name', deal.name],
          ['Last Activity', exactTime(deal.last_activity_at)],
          ['Phone', deal.phone || '—'],
          ['Email', deal.email || '—'],
          ['Tags', deal.tags?.map((t) => t.name).join(', ') || '—'],
          ['Amount', deal.amount != null ? money(deal.amount, deal.currency) : '—'],
          ['Language', deal.language || '—'],
          ['Stage', stageOptions.find((s) => s.value === deal.stage)?.label || '—'],
          ['Close date', deal.closed_on ? longDate(deal.closed_on) : '—'],
          ['Deal owner', deal.owner || '—'],
          ['Priority', deal.priority_label || '—'],
          ['Source', deal.lead_source_label || '—'],
          ['Address', deal.address_line || '—'],
          ['City', deal.city || '—'],
          ['State', deal.state || '—'],
          ['Zip Code', deal.postcode || '—'],
          ['Country', deal.country_label || deal.country || '—']
        ]}
      />
    {/if}
    <dl class="v2-kv">
      <dt>Stage since</dt>
      <dd>{longDate(deal.stage_changed_at)}</dd>
    </dl>

    <!--
      An "Attached" panel listing this account's invoices and tickets used to
      sit here. Both are real models, but neither is on the opportunity
      response. Filling it means two more cross-module requests per page load
      for a rail nobody asked for. Add it back deliberately if it earns them.
    -->
    <DeleteRecord kind="deal" id={deal.id} inFlow />
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
    font-size: 15px;
    font-weight: 600;
  }

  .deal-overview {
    margin: 14px 22px 0;
    padding: 18px;
    display: flex;
    flex-wrap: wrap;
    align-items: flex-start;
    gap: 18px 30px;
    background: var(--v2-card);
    border-radius: 12px;
  }
  .deal-overview > div {
    min-width: 110px;
  }
  .deal-overview strong {
    display: block;
    font-size: 14px;
    font-weight: 600;
    overflow-wrap: anywhere;
  }
  .overview-label,
  .deal-value > span {
    display: block;
    font-size: 11px;
    color: var(--v2-slate);
    margin-bottom: 6px;
  }
  .deal-value strong {
    font-size: 26px;
    font-weight: 650;
    letter-spacing: -0.5px;
  }
  .stage-age {
    margin: 0;
    flex-basis: 100%;
    font-size: 12px;
    color: var(--v2-slate);
  }
  .deal-journal {
    padding: 20px;
    margin-bottom: 14px;
  }
  .deal-history {
    max-height: 420px;
    overflow-y: auto;
  }
  .deal-secondary {
    margin-bottom: 14px;
  }
  .deal-secondary > summary {
    padding: 14px 16px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
  }
  .deal-secondary > summary span {
    margin-left: 8px;
    font-size: 12px;
    color: var(--v2-slate);
    font-weight: 400;
  }
  .secondary-content {
    padding: 0 16px 16px;
  }
  .line-items-scroll {
    overflow-x: auto;
  }

  .deal-layout {
    display: flex;
    flex: 1;
    min-height: 0;
    overflow: auto;
  }
  .deal-layout > .v2-main {
    min-width: 300px;
  }
  .deal-properties {
    display: block !important;
    width: 320px;
    flex-shrink: 0;
    padding: 20px;
    margin: 14px 22px 20px 0;
    background: var(--v2-card);
    border: 0;
    border-radius: 12px;
    min-height: 0;
    overflow-y: auto;
  }
  @media (max-width: 800px) {
    .deal-layout {
      display: block;
      overflow-y: auto;
    }
    .deal-layout > .v2-main {
      overflow: visible;
      min-width: 0;
    }
    .deal-layout :global(.v2-scroll) {
      overflow: visible;
    }
    .deal-properties {
      width: auto;
      margin: 0 15px 20px;
      overflow: visible;
    }
    .deal-overview {
      margin: 12px 15px 0;
      gap: 16px 24px;
    }
  }
</style>
