<script>
  import { untrack } from 'svelte';
  import { RangeCalendar } from 'bits-ui';
  import { parseDate } from '@internationalized/date';
  import { ChevronLeft, ChevronRight } from '@lucide/svelte';
  import * as Dialog from '$lib/components/ui/dialog/index.js';
  import { useI18n } from '$lib/i18n/context.js';
  const { ui, locale } = useI18n();
  /** @type {{open:boolean,start:string,end:string,onapply:(start:string,end:string)=>void}} */
  let { open = $bindable(false), start, end, onapply } = $props();
  /** @type {{start:import('@internationalized/date').DateValue|undefined,end:import('@internationalized/date').DateValue|undefined}} */
  // The parent mounts a fresh dialog for each edit; keep its draft independent.
  let range = $state(untrack(() => ({ start: parseDate(start), end: parseDate(end) })));
  function dateLabel(value) {
    return value
      ? value.toDate('UTC').toLocaleDateString(locale(), {
          month: 'short',
          day: 'numeric',
          year: 'numeric',
          timeZone: 'UTC'
        })
      : '—';
  }
  function apply() {
    if (!range.start || !range.end) return;
    onapply(range.start.toString(), range.end.toString());
    open = false;
  }
</script>

<Dialog.Root bind:open>
  <Dialog.Content class="crm-range-dialog">
    <Dialog.Header
      ><Dialog.Title>{ui('Custom date range')}</Dialog.Title>
      <Dialog.Description class="sr-only">{ui('Select a start and end date.')}</Dialog.Description>
    </Dialog.Header>
    <RangeCalendar.Root
      bind:value={range}
      locale={locale()}
      numberOfMonths={2}
      weekdayFormat="short"
      fixedWeeks
      maxDays={3660}
      minValue={parseDate('1901-01-01')}
      maxValue={parseDate('9998-12-31')}
      calendarLabel={ui('Custom date range')}
    >
      {#snippet children({ months, weekdays })}
        <RangeCalendar.Header class="range-navigation">
          <RangeCalendar.PrevButton class="v2-btn v2-btn-icon" aria-label={ui('Previous month')}
            ><ChevronLeft size={16} /></RangeCalendar.PrevButton
          >
          <RangeCalendar.Heading />
          <RangeCalendar.NextButton class="v2-btn v2-btn-icon" aria-label={ui('Next month')}
            ><ChevronRight size={16} /></RangeCalendar.NextButton
          >
        </RangeCalendar.Header>
        <div class="months">
          {#each months as month (month.value.toString())}
            <div class="month">
              <h3>
                {month.value.toDate('UTC').toLocaleDateString(locale(), {
                  month: 'long',
                  year: 'numeric',
                  timeZone: 'UTC'
                })}
              </h3>
              <RangeCalendar.Grid class="range-grid">
                <RangeCalendar.GridHead
                  ><RangeCalendar.GridRow>
                    {#each weekdays as day, index (index)}<RangeCalendar.HeadCell
                        >{day}</RangeCalendar.HeadCell
                      >{/each}
                  </RangeCalendar.GridRow></RangeCalendar.GridHead
                >
                <RangeCalendar.GridBody>
                  {#each month.weeks as week, index (index)}<RangeCalendar.GridRow>
                      {#each week as date (date.toString())}<RangeCalendar.Cell
                          {date}
                          month={month.value}
                        >
                          <RangeCalendar.Day class="range-day">{date.day}</RangeCalendar.Day>
                        </RangeCalendar.Cell>{/each}
                    </RangeCalendar.GridRow>{/each}
                </RangeCalendar.GridBody>
              </RangeCalendar.Grid>
            </div>
          {/each}
        </div>
      {/snippet}
    </RangeCalendar.Root>
    <div class="range-footer crm-control-toolbar">
      <span aria-live="polite">{dateLabel(range.start)} – {dateLabel(range.end)}</span>
      <button class="v2-btn" onclick={() => (open = false)}>{ui('Cancel')}</button>
      <button class="v2-btn v2-btn-primary" disabled={!range.start || !range.end} onclick={apply}
        >{ui('Apply')}</button
      >
    </div>
  </Dialog.Content>
</Dialog.Root>

<style>
  :global(.crm-range-dialog) {
    width: 650px;
    max-width: 650px;
    background: var(--crm-surface);
    color: var(--crm-text);
  }
  :global(.crm-range-dialog .range-navigation) {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    font-size: var(--crm-text-sm);
  }
  .months {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 24px;
  }
  .month h3 {
    font-size: var(--crm-text-sm);
    font-weight: 600;
    margin: 14px 0 10px;
    text-align: center;
  }
  .month :global(.range-grid) {
    width: 100%;
    border-collapse: collapse;
    table-layout: fixed;
  }
  .month :global(th) {
    height: 32px;
    font-size: var(--crm-text-xs);
    font-weight: 400;
    color: var(--crm-text-muted);
  }
  .month :global(td) {
    padding: 2px 0;
    text-align: center;
  }
  .month :global(.range-day) {
    width: 100%;
    height: 34px;
    font-size: var(--crm-text-sm);
    border-radius: var(--crm-radius-sm);
  }
  .month :global(.range-day:hover),
  .month :global(.range-day[data-range-middle]),
  .month :global(.range-day[data-highlighted]) {
    background: var(--crm-surface-selected);
  }
  .month :global(.range-day[data-range-start]),
  .month :global(.range-day[data-range-end]) {
    background: var(--crm-primary);
    color: var(--crm-primary-text);
  }
  .month :global(.range-day[data-outside-month]) {
    visibility: hidden;
  }
  .month :global(.range-day[data-disabled]) {
    opacity: 0.35;
  }
  .month :global(.range-day:focus-visible) {
    outline: 2px solid var(--crm-focus);
    outline-offset: 1px;
  }
  .range-footer {
    display: flex;
    align-items: center;
    gap: 8px;
    border-top: 1px solid var(--crm-border-soft);
    padding-top: 16px;
  }
  .range-footer > span {
    margin-right: auto;
    font-size: var(--crm-text-sm);
  }
</style>
