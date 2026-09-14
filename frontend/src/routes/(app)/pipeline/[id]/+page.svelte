<script>
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
  import Pill from '$lib/v2/components/Pill.svelte';
  import Avatar from '$lib/v2/components/Avatar.svelte';
  import { money, longDate } from '$lib/v2/format.js';
  import { OPEN_STAGES, STAGE_LABEL, AGING_TONE, AGING_LABEL } from '$lib/v2/enums.js';
  import { Check, ChevronRight } from '@lucide/svelte';

  /** @type {{ data: any, form?:any }} */
  let { data, form } = $props();

  let { deal, activity, lineItems, contacts } = $derived(data);
  let stageIndex = $derived(OPEN_STAGES.indexOf(deal.stage));

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

<PageHeader title={deal.name} record>
  {#snippet crumb()}
    <a href={resolve('/pipeline')}>Deals</a>
    <ChevronRight size={12} />
    {#if deal.account.id}<a href={resolve(`/accounts/${deal.account.id}`)}>{deal.account.name}</a
      >{/if}
  {/snippet}
</PageHeader>

<div class="deal-layout">
  <div class="v2-main">
    <!-- Stage stepper. Closed stages are not on the path; they end it. -->
    <div
      class="v2-pad"
      style="padding-top:14px;display:flex;gap:6px;align-items:center;flex-wrap:wrap;flex:none"
    >
      {#each OPEN_STAGES as stage, i (stage)}
        {#if i > 0}<ChevronRight size={12} style="color:var(--v2-slate)" />{/if}
        <span
          class="v2-pill"
          style={i <= stageIndex
            ? 'color:var(--v2-ink);background:color-mix(in srgb, var(--v2-ink) 9%, transparent)'
            : 'color:var(--v2-slate);background:var(--v2-line-soft)'}
        >
          {#if i < stageIndex}<Check size={11} />{/if}
          {STAGE_LABEL[stage]}
        </span>
      {/each}
      <span style="margin-left:auto">
        <Pill tone={AGING_TONE[deal.aging_status]} dot>
          {`${AGING_LABEL[deal.aging_status]} · ${deal.days_in_current_stage} days in ${STAGE_LABEL[deal.stage]}`}
        </Pill>
      </span>
    </div>

    <div class="v2-scroll">
      <div class="v2-pad" style="padding-top:14px;padding-bottom:32px">
        <!--
          The "next action" card that used to sit here was a fixture string.
          Opportunity has no such field and nothing derives one, so there is
          nothing to render. A suggestion the system invented is worse than no
          suggestion, because people act on it.
        -->
        <section aria-label="Deal notes" style="margin-bottom:20px">
          <h2 class="v2-label" style="margin-bottom:10px">Notes</h2>
          {#key deal.id}<DealNotes notes={data.notes} />{/key}
        </section>
        <section class="v2-card deal-attachments">
          <h2>Attachments</h2>
          <Attachments attachments={data.attachments} />
        </section>
        <div class="v2-label" style="margin-bottom:12px">Activity</div>
        <Timeline events={activity} />

        {#if lineItems.length}
          <div class="v2-label" style="margin:22px 0 10px">Line items</div>
          <div class="v2-card" style="overflow:hidden">
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
                      {li.discount_amount > 0 ? `−${money(li.discount_amount, deal.currency)}` : ''}
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
              <span class="v2-num" style="font-weight:650">{money(deal.amount, deal.currency)}</span
              >
            </div>
          </div>
        {/if}
      </div>
    </div>
  </div>

  <aside class="v2-rail deal-properties" aria-label="Deal properties">
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
        entries={[
          ['Name', deal.name],
          ['Amount', deal.amount != null ? money(deal.amount, deal.currency) : '—'],
          ['Language', deal.language || '—'],
          ['Stage', STAGE_LABEL[deal.stage] || '—'],
          ['Close date', deal.closed_on ? longDate(deal.closed_on) : '—'],
          ['Deal owner', deal.owner || '—'],
          ['Priority', deal.priority_label || '—'],
          ['Source', deal.lead_source_label || '—'],
          ['Company', deal.account?.id ? deal.account.name : '—'],
          [
            'Contacts',
            contacts.map((c) => [c.first_name, c.last_name].filter(Boolean).join(' ')).join(', ') ||
              '—'
          ],
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

    <div class="v2-label v2-rail-head">Contact</div>
    {#each contacts as c (c.id)}
      <!-- A link now that `/contacts/<uuid>` resolves. These names were
           plain text because the contacts module was still fixtures. -->
      <a
        class="v2-rail-row"
        href={resolve(`/contacts/${c.id}`)}
        style="color:inherit;text-decoration:none"
      >
        <Avatar name="{c.first_name} {c.last_name}" size={27} />
        <div style="min-width:0">
          <div style="font-size:12.5px;font-weight:550">{c.first_name} {c.last_name}</div>
          <!-- `relationship` (Champion, Blocker) was a fixture field. Contact
               has `title` and `department`, so the line says those. -->
          <div class="v2-sub" style="font-size:11px">
            {[c.title, c.department].filter(Boolean).join(' · ') || 'No title recorded'}
          </div>
        </div>
      </a>
    {:else}
      <p class="v2-sub" style="font-size:12px">
        Nobody is linked to this deal yet. Add the person who signs it.
      </p>
    {/each}

    <!--
      An "Attached" panel listing this account's invoices and tickets used to
      sit here. Both are real models, but neither is on the opportunity
      response. Filling it means two more cross-module requests per page load
      for a rail nobody asked for. Add it back deliberately if it earns them.
    -->
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

  .deal-attachments {
    padding: 16px;
    margin-bottom: 20px;
  }
  .deal-attachments h2 {
    font-size: 14px;
    margin: 0 0 12px;
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
    width: 300px;
    min-height: 0;
    overflow-y: auto;
  }
</style>
