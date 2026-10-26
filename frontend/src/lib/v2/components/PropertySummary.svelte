<script>
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();

  import TagBadge from '$lib/v2/components/TagBadge.svelte';
  import { page } from '$app/state';
  import InlineProperty from './InlineProperty.svelte';
  import { editableProperty, propertyRawValue } from '$lib/v2/inline-property.js';
  import { Copy } from '@lucide/svelte';
  import { orderedEntries, customDisplay } from '$lib/v2/property-order.js';
  /** @type {{entries:Array<any[]>,tags?:any[],target?:string,record?:any,schema?:any}} */
  let { entries, tags, target = '', record = null, schema = null } = $props();
  const config = $derived(page.data.propertyLayout?.[target]);
  const rows = $derived(
    orderedEntries(
      record?.id ? [...entries, ['Record ID', record.id, 'id']] : entries,
      target,
      config,
      record?.custom_fields
    )
  );
  let copyStatus = $state('');
  async function copyRecordId() {
    try {
      await navigator.clipboard.writeText(String(record.id));
      copyStatus = 'Full ID copied';
    } catch {
      copyStatus = 'Could not copy. Select the full ID to copy it.';
    }
  }
</script>

<dl>
  {#each rows as row (`${record?.id}:${row.key}`)}
    {@const editable =
      record &&
      editableProperty(row, target, schema, page.data.permissions, page.data.pipelineConfig)}
    <div>
      <dt>
        {row.definition ? row.label : ui(row.label)}{#if row.definition?.is_required}<span>
            *</span
          >{/if}
      </dt>
      <dd>
        {#if editable}
          <InlineProperty
            field={editable}
            value={propertyRawValue(record, editable)}
            {target}
            recordId={record.id}
          >
            {#if row.definition}{customDisplay(row.value, row.definition)}
            {:else if row.label === 'Tags' && tags}<span class="tags"
                >{#each tags as tag (tag.id)}<TagBadge {tag} />{:else}—{/each}</span
              >
            {:else if row.key === 'stage' && row.value}<span class="stage-value">{row.value}</span>
            {:else}{row.value === '' ? '—' : (row.value ?? '—')}{/if}
          </InlineProperty>
          {#if row.key === 'pages'}<span class="page-links"
              >{#each record.pages || [] as item (item.url)}<a
                  href={item.url}
                  target="_blank"
                  rel="external noopener noreferrer">{item.name || item.url}</a
                >{/each}</span
            >{/if}
        {:else if row.key === 'id' && row.value}
          <span class="record-id">
            <details>
              <summary title={String(row.value)}
                >{String(row.value).length > 16
                  ? `${String(row.value).slice(0, 8)}…${String(row.value).slice(-4)}`
                  : row.value}</summary
              ><span class="full-id">{row.value}</span>
            </details>
            <button
              type="button"
              class="copy-id"
              aria-label={ui('Copy full record ID')}
              title={ui('Copy full record ID')}
              onclick={copyRecordId}><Copy size={13} /></button
            >
          </span>
          {#if copyStatus}<span class="copy-status" role="status">{ui(copyStatus)}</span>{/if}
        {:else if row.definition}{customDisplay(row.value, row.definition)}
        {:else if row.label === 'Stage' && row.value && row.value !== '—'}<span class="stage-value"
            >{row.value}</span
          >
        {:else if row.label === 'Tags' && tags}<span class="tags"
            >{#each tags as tag (tag.id)}<TagBadge {tag} />{:else}—{/each}</span
          >
        {:else}{row.value === '' ? '—' : (row.value ?? '—')}{/if}
      </dd>
    </div>{/each}
</dl>

<style>
  .page-links {
    display: grid;
    gap: 4px;
    margin-top: 6px;
  }
  .record-id {
    display: flex;
    align-items: flex-start;
    gap: 6px;
    font-size: var(--crm-text-xs);
  }
  .record-id summary {
    cursor: pointer;
    list-style: none;
    font-variant-numeric: tabular-nums;
  }
  .record-id summary::-webkit-details-marker {
    display: none;
  }
  .full-id {
    display: block;
    margin-top: 6px;
    user-select: all;
    color: var(--v2-slate);
  }
  .copy-id {
    display: inline-flex;
    padding: 2px;
    background: transparent;
    border: 0;
    color: var(--v2-slate);
    cursor: pointer;
  }
  .copy-status {
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
  }
  dl {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 12rem), 1fr));
    gap: var(--crm-space-3);
    margin: var(--crm-space-3) 0 0;
  }
  dl > div {
    min-width: 0;
  }
  dt {
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
    margin-bottom: 6px;
  }
  dd {
    margin: 0;
    font-size: var(--crm-text-sm);
    line-height: 1.5;
    overflow-wrap: anywhere;
    white-space: normal;
  }
  .stage-value {
    display: inline-block;
    padding: 3px 9px;
    border-radius: var(--crm-radius-sm);
    background: var(--crm-info-bg);
    color: var(--crm-info);
    font-size: var(--crm-text-xs);
  }
  .tags {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
  }
</style>
