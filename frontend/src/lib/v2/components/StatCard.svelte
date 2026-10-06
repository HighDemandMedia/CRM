<script>
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();

  /**
   * A stat tile. The value is tabular mono so a changing figure never
   * reflows the tile it sits in.
   *
   * @type {{ label: string, value: string, tone?: 'ink'|'slate'|'clay'|'rust'|'moss', detail?: string, review?: boolean }}
   */
  let { label, value, tone = 'ink', detail = null, review = false } = $props();

  const VAR = {
    ink: 'var(--v2-ink)',
    slate: 'var(--v2-slate)',
    clay: 'var(--v2-clay)',
    rust: 'var(--v2-rust)',
    moss: 'var(--v2-moss)'
  };
</script>

<div class="v2-stat">
  <div class="v2-label">
    {label}{#if review}<span class="review-badge" title={ui('Pending review')}>{ui('Review')}</span
      >{/if}
  </div>
  <div class="v2-stat-value" style="color:{VAR[tone] ?? VAR.ink}">{value}</div>
  {#if detail}<div class="v2-sub" style="font-size:var(--crm-text-xs);margin-top:2px">
      {detail}
    </div>{/if}
</div>

<style>
  .review-badge {
    display: inline-block;
    margin-left: 6px;
    padding: 2px var(--crm-space-1);
    font-size: var(--crm-text-xs);
    line-height: 1.3;
    font-weight: 500;
    color: var(--crm-warning);
    background: var(--crm-warning-bg);
    border-radius: var(--crm-radius-sm);
    text-transform: none;
    letter-spacing: normal;
  }
</style>
