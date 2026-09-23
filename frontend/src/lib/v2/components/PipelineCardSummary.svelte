<script>
  import TagBadge from './TagBadge.svelte';
  import { resolve } from '$app/paths';
  import { asInternalPath } from '$lib/utils/paths.js';
  import { exactTime, stageDuration } from '$lib/v2/contact-time.js';
  import { money, count } from '$lib/v2/format.js';

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
          : `${count(value.amount)} (currency not set)`
      )
      .join(' · ')
  );
  let stageAge = $derived(stageDuration(stageEntered, now));
  let lastActivityText = $derived.by(() => {
    if (!lastActivity || !Number.isFinite(Date.parse(lastActivity))) return '—';
    const days = Math.floor(Math.max(0, now - Date.parse(lastActivity)) / 86400000);
    return days === 0 ? 'Today' : `${days}d ago`;
  });
</script>

<div class="compact-heading">
  <a class="compact-name" draggable="false" href={resolve(asInternalPath(href))} title={name}
    >{name || `Record · ${href.split("/").pop()?.slice(0, 8)}`}</a
  >
  {#if valueText}<span class="compact-value" title={`${valueLabel}: ${valueText}`}>{valueText}</span
    >{/if}
</div>
{#if email}<a class="compact-email" draggable="false" href={`mailto:${email}`} title={email}
    >{email}</a
  >{/if}
{#if phone}<a class="compact-phone" draggable="false" href={`tel:${phone}`} title={phone}>{phone}</a
  >{/if}
<div class="compact-activity">
  <span title={exactTime(lastActivity)}>Last activity <b>{lastActivityText}</b></span>
  {#if stageAge}<span class="compact-age" title={`Time in stage: ${stageAge}`}
      >{stageAge} in stage</span
    >{/if}
</div>

{#if tags.length}
  <div class="compact-tags" aria-label="Tags">
    {#each tags as tag}<TagBadge {tag} />{/each}
  </div>
{/if}

<style>
  .compact-tags { display:flex; flex-wrap:wrap; align-items:center; gap:4px; margin-top:8px; }
  .compact-tags :global(.tag-badge) { font-size:10px; padding:2px 6px; }

  .compact-heading {
    display: flex;
    align-items: baseline;
    gap: 8px;
    min-width: 0;
  }
  .compact-name {
    flex: 1;
    min-width: 0;
    font-size: 13px;
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
    font-size: 12px;
    font-weight: 600;
    color: var(--v2-ink);
    font-variant-numeric: tabular-nums;
  }
  .compact-email {
    display: block;
    margin-top: 4px;
    color: #706779;
    font-size: 11px;
    line-height: 1.5;
    text-decoration: underline;
    text-underline-offset: 2px;
  }
  .compact-phone {
    display: block;
    margin-top: 3px;
    color: #625a69;
    font-size: 12px;
    line-height: 1.5;
    text-decoration: none;
  }
  .compact-name:hover,
  .compact-phone:hover {
    text-decoration: underline;
  }
  a:focus-visible {
    outline: 2px solid #81778c;
    outline-offset: 2px;
    border-radius: 2px;
  }
  .compact-activity {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 4px 8px;
    margin-top: 9px;
    color: #817889;
    font-size: 10px;
    line-height: 1.5;
  }
  .compact-activity b {
    font-weight: 500;
  }
  .compact-age {
    color: #76627f;
    margin-left: auto;
  }
</style>
