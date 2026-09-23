<script>
  import { money, count } from '$lib/v2/format.js';
  /** @type {{ values?: {amount: string|number, currency?: string}[], label?: string, currency?: string }} */
  let { values = [], label = 'Total value', currency = 'USD' } = $props();
  let text = $derived(
    values.length
      ? values
          .map((value) =>
            value.currency
              ? `${money(Number(value.amount), value.currency)} ${value.currency}`
              : `${count(Number(value.amount))} (currency not set)`
          )
          .join(' · ')
      : `${money(0, currency)} ${currency}`
  );
</script>

<span class="pipeline-total" title={label} aria-label={`${label}: ${text}`}>{text}</span>

<style>
  .pipeline-total {
    font-variant-numeric: tabular-nums;
    font-weight: 600;
    font-size: 11px;
    color: #6c6174;
  }
</style>
