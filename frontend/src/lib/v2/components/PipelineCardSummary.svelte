<script>
  import { useI18n } from '$lib/i18n/context.js';
  const { exactTime, stageDuration, ui, money, count } = useI18n();

  import TagBadge from './TagBadge.svelte';
  import { resolve } from '$app/paths';
  import { asInternalPath } from '$lib/utils/paths.js';

  /** @type {{ name: string, href: string, tags?: {id?: string, name: string, color?: string}[], email?: string, phone?: string, values?: {amount: number|null, currency?: string}[], valueLabel?: string, lastActivity?: string|null, stageEntered?: string|null, now: number }} */
  let {
    name,
    href,
    email = '',
    phone = '',
    values = [],
    tags = [],
    valueLabel = 'Value',
    lastActivity = null,
    stageEntered = null,
    now
  } = $props();
  let valueText = $derived(
    values
      .filter((value) => value.amount !== null)
      .map((value) =>
        value.currency
          ? money(value.amount, value.currency)
          : ui('{amount} (currency not set)', { amount: count(value.amount) })
      )
      .join(' · ')
  );
  let stageAge = $derived(stageDuration(stageEntered, now));
  let lastActivityText = $derived.by(() => {
    if (!lastActivity || !Number.isFinite(Date.parse(lastActivity))) return '—';
    const days = Math.floor(Math.max(0, now - Date.parse(lastActivity)) / 86400000);
    return days === 0 ? ui('Today') : ui('{days}d ago', { days });
  });
</script>

<div class="compact-heading">
  <a class="compact-name" draggable="false" href={resolve(asInternalPath(href))} title={name}
    >{name || `Record · ${href.split('/').pop()?.slice(0, 8)}`}</a
  >
  {#if valueText}<span class="compact-value" title={`${ui(valueLabel)}: ${valueText}`}
      >{valueText}</span
    >{/if}
</div>
{#if email}<a class="compact-email" draggable="false" href={`mailto:${email}`} title={email}
    >{email}</a
  >{/if}
{#if phone}<a class="compact-phone" draggable="false" href={`tel:${phone}`} title={phone}>{phone}</a
  >{/if}
<div class="compact-activity">
  <span title={exactTime(lastActivity)}>{ui('Last activity')} <b>{lastActivityText}</b></span>
  {#if stageAge}<span
      class="compact-age"
      title={ui('Time in stage: {duration}', { duration: stageAge })}
      >{stageAge} {ui('in stage')}</span
    >{/if}
</div>

{#if tags.length}
  <div class="compact-tags" aria-label={ui('Tags')}>
    {#each tags as tag}<TagBadge {tag} />{/each}
  </div>
{/if}

<style>
  .compact-tags {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--crm-space-1);
    margin-top: var(--crm-space-2);
  }
  .compact-tags :global(.tag-badge) {
    font-size: var(--crm-text-xs);
    padding: 2px 6px;
  }

  .compact-heading {
    display: flex;
    align-items: baseline;
    gap: var(--crm-space-2);
    min-width: 0;
  }
  .compact-name {
    flex: 1;
    min-width: 0;
    font-size: var(--crm-text-sm);
    font-weight: 650;
    color: var(--v2-ink);
    line-height: 1.5;
    text-decoration: none;
  }
  .compact-name,
  .compact-value,
  .compact-email,
  .compact-phone {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .compact-value {
    flex: 0 1 auto;
    max-width: 48%;
    font-size: var(--crm-text-xs);
    font-weight: 600;
    color: var(--v2-ink);
    font-variant-numeric: tabular-nums;
  }
  .compact-email {
    display: block;
    margin-top: var(--crm-space-1);
    color: var(--crm-text-muted);
    font-size: var(--crm-text-xs);
    line-height: 1.5;
    text-decoration: underline;
    text-underline-offset: 2px;
  }
  .compact-phone {
    display: block;
    margin-top: 3px;
    color: var(--crm-text-muted);
    font-size: var(--crm-text-xs);
    line-height: 1.5;
    text-decoration: none;
  }
  .compact-name:hover,
  .compact-phone:hover {
    text-decoration: underline;
  }
  a:focus-visible {
    outline: 2px solid var(--crm-focus);
    outline-offset: 2px;
    border-radius: var(--crm-radius-sm);
  }
  .compact-activity {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: var(--crm-space-1) var(--crm-space-2);
    margin-top: 9px;
    color: var(--crm-text-muted);
    font-size: var(--crm-text-xs);
    line-height: 1.5;
  }
  .compact-activity b {
    font-weight: 500;
  }
  .compact-age {
    color: var(--crm-text-muted);
    margin-left: auto;
  }
</style>
