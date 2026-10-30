<script>
  import { Info } from '@lucide/svelte';
  import * as Tooltip from '$lib/components/ui/tooltip/index.js';
  import { useI18n } from '$lib/i18n/context.js';
  const { ui, locale, money } = useI18n();
  /** @type {{metric:{key:string,label:string,unit:string,value?:number|null,definition:string,amounts?:{currency:string,amount:string}[]}}} */
  let { metric } = $props();
  const number = (value) =>
    new Intl.NumberFormat(locale(), { maximumFractionDigits: 1 }).format(value);
</script>

<section class="crm-stat crm-panel">
  <div class="metric-label">
    <span>{ui(metric.label)}</span>
    <Tooltip.Provider delayDuration={150}
      ><Tooltip.Root>
        <Tooltip.Trigger aria-label={ui(metric.definition)} class="metric-help"
          ><Info size={14} /></Tooltip.Trigger
        >
        <Tooltip.Content side="bottom"
          ><span class="definition">{ui(metric.definition)}</span></Tooltip.Content
        >
      </Tooltip.Root></Tooltip.Provider
    >
  </div>
  {#if metric.unit === 'money'}
    <div class="amounts">
      {#each metric.amounts || [] as amount (amount.currency)}
        <strong>{money(amount.amount, amount.currency)} <span>{amount.currency}</span></strong>
      {:else}<strong>—</strong>{/each}
    </div>
  {:else}<strong
      >{metric.value == null
        ? '—'
        : `${number(metric.value)}${metric.unit === 'percent' ? '%' : metric.unit === 'hours' ? ' h' : ''}`}</strong
    >{/if}
</section>

<style>
  .metric-label {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    color: var(--crm-text-muted);
    font-size: var(--crm-text-xs);
  }
  .metric-label :global(.metric-help) {
    display: inline-flex;
    padding: 3px;
    border-radius: var(--crm-radius-full);
  }
  .metric-label :global(.metric-help:focus-visible) {
    outline: 2px solid var(--crm-focus);
  }
  .definition {
    display: block;
    max-width: 280px;
  }
  .amounts {
    display: grid;
    gap: 6px;
  }
  .amounts strong {
    font-size: var(--crm-text-xl);
  }
  .amounts strong span {
    font-size: var(--crm-text-xs);
    color: var(--crm-text-muted);
    font-weight: 400;
  }
</style>
