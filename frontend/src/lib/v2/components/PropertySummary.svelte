<script>
  import TagBadge from '$lib/v2/components/TagBadge.svelte';
  import { page } from '$app/state';
  import { invalidateAll } from '$app/navigation';
  import { Pencil, Copy } from '@lucide/svelte';
  import StageRequirementField from '$lib/components/pipelines/StageRequirementField.svelte';
  import { orderedEntries, customDisplay } from '$lib/v2/property-order.js';
  /** @type {{entries:Array<any[]>,tags?:any[],target?:string,record?:any}} */
  let { entries, tags, target = '', record = null } = $props();
  const config = $derived(page.data.propertyLayout?.[target]);
  const rows = $derived(
    orderedEntries(
      record?.id ? [...entries, ['Record ID', record.id, 'id']] : entries,
      target,
      config,
      record?.custom_fields
    )
  );
  let editing = $state(''),
    draft = $state(/** @type {any} */ ('')),
    busy = $state(false),
    error = $state('');
  let copyStatus = $state('');
  async function copyRecordId() {
    try {
      await navigator.clipboard.writeText(String(record.id));
      copyStatus = 'Full ID copied';
    } catch {
      copyStatus = 'Could not copy. Select the full ID to copy it.';
    }
  }
  function edit(row) {
    error = '';
    editing = row.key;
    draft =
      row.definition.field_type === 'checkbox'
        ? row.value == null
          ? ''
          : String(row.value)
        : row.definition.field_type === 'multi_select'
          ? [...(row.value || [])]
          : row.definition.field_type === 'datetime' && row.value
            ? new Date(
                new Date(row.value).getTime() - new Date(row.value).getTimezoneOffset() * 60000
              )
                .toISOString()
                .slice(0, 16)
            : row.definition.field_type === 'list'
              ? JSON.stringify(row.value || [])
              : (row.value ?? '');
  }
  async function save(event, row) {
    event.preventDefault();
    busy = true;
    error = '';
    try {
      let value = draft;
      if (row.definition.field_type === 'checkbox') value = draft === '' ? null : draft === 'true';
      if (row.definition.field_type === 'list') value = JSON.parse(draft || '[]');
      if (row.definition.field_type === 'datetime' && draft) value = new Date(draft).toISOString();
      const response = await fetch('/api/record-properties', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target, id: record.id, values: { [row.definition.key]: value } })
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error);
      await invalidateAll();
      editing = '';
    } catch (err) {
      error = err.message || 'Could not save the property.';
    } finally {
      busy = false;
    }
  }
</script>

<dl>
  {#each rows as row (row.key)}<div>
      <dt>
        {row.label}{#if row.definition?.is_required}<span> *</span>{/if}
        {#if row.definition && record && editing !== row.key}<button
            type="button"
            class="edit-property"
            aria-label={`Edit ${row.label}`}
            disabled={busy}
            onclick={() => edit(row)}><Pencil size={13} /></button
          >{/if}
      </dt>
      <dd>
        {#if editing === row.key}<form onsubmit={(event) => save(event, row)}>
            <StageRequirementField
              field={{ ...row.definition, label: row.label }}
              required={row.definition.is_required}
              bind:value={draft}
            />
            {#if error}<p class="v2-error" role="alert">{error}</p>{/if}
            <button class="v2-btn v2-btn-primary" disabled={busy}>Save</button>
            <button type="button" class="v2-btn" disabled={busy} onclick={() => (editing = '')}
              >Cancel</button
            >
          </form>
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
              aria-label="Copy full record ID"
              title="Copy full record ID"
              onclick={copyRecordId}><Copy size={13} /></button
            >
          </span>
          <span class="copy-status" role="status">{copyStatus}</span>
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
  .record-id {
    display: flex;
    align-items: flex-start;
    gap: 6px;
    font-size: 12px;
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
    font-size: 11px;
    color: var(--v2-slate);
  }
  .edit-property {
    border: 0;
    background: transparent;
    cursor: pointer;
    color: var(--v2-slate);
    float: right;
    padding: 0 4px;
  }
  dl {
    display: grid;
    gap: 19px;
    margin: 22px 0 0;
  }
  dt {
    font-size: 12px;
    color: var(--v2-slate);
    margin-bottom: 6px;
  }
  dd {
    margin: 0;
    font-size: 14px;
    line-height: 1.5;
    overflow-wrap: anywhere;
    white-space: pre-wrap;
  }
  .stage-value {
    display: inline-block;
    padding: 3px 9px;
    border-radius: 5px;
    background: #eff6ff;
    color: #1d4ed8;
    font-size: 12px;
  }
  .tags {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
  }
</style>
