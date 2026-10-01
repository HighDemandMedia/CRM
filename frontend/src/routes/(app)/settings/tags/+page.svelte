<script>
  import { deserialize } from '$app/forms';
  import { invalidateAll } from '$app/navigation';
  import { toast } from 'svelte-sonner';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import TeamPanel from '$lib/components/team/TeamPanel.svelte';
  import TagBadge from '$lib/v2/components/TagBadge.svelte';
  import * as Dropdown from '$lib/components/ui/dropdown-menu/index.js';
  import { tagColors } from '$lib/v2/tag-colors.js';
  import {
    Plus,
    Search,
    ChevronDown,
    Pencil,
    Archive,
    RotateCcw,
    Merge,
    Check
  } from '@lucide/svelte';

  /** @type {{data:any, form:any}} */
  let { data, form } = $props();
  let query = $state(''),
    status = $state('active'),
    object = $state('');
  let sort = $state('name'),
    descending = $state(false),
    expanded = $state('');
  let panel = $state(''),
    selected = $state(/** @type {any} */ (null));
  let name = $state(''),
    color = $state('blue'),
    destination = $state('');
  let busy = $state(false),
    error = $state(''),
    confirmed = $state(false);
  const objectNames = {
    contacts: 'Contacts',
    accounts: 'Companies',
    opportunities: 'Deals',
    tasks: 'Tasks',
    cases: 'Tickets',
    leads: 'Leads',
    api_settings: 'API settings',
    solutions: 'Knowledge base',
    web_forms: 'Web forms'
  };
  const labelFor = (key) => objectNames[key] || key.replaceAll('_', ' ');
  const used = (tag) =>
    Object.values(tag.usage || {}).reduce((sum, value) => sum + Number(value || 0), 0);
  const usage = (tag) => Object.entries(tag.usage || {}).filter(([, value]) => Number(value) > 0);
  let objectOptions = $derived(
    Object.entries(objectNames).filter(
      ([key]) =>
        ['contacts', 'accounts', 'opportunities', 'tasks', 'cases'].includes(key) ||
        data.tags.some((t) => t.usage?.[key] > 0)
    )
  );
  let totals = $derived(data.totals);
  let filters = $derived([
    { key: 'active', label: 'Active', count: totals.active },
    { key: 'unused', label: 'Unused', count: totals.unused },
    { key: 'archived', label: 'Archived', count: totals.count - totals.active },
    { key: 'all', label: 'All', count: totals.count }
  ]);
  let tags = $derived(
    [...data.tags]
      .filter(
        (t) =>
          (status === 'all' ||
            (status === 'archived'
              ? !t.is_active
              : t.is_active && (status !== 'unused' || used(t) === 0))) &&
          (!object || t.usage?.[object] > 0) &&
          t.name.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase())
      )
      .sort(
        (a, b) =>
          (sort === 'usage'
            ? used(a) - used(b) || a.name.localeCompare(b.name)
            : a.name.localeCompare(b.name)) * (descending ? -1 : 1)
      )
  );
  let mergeTargets = $derived(data.tags.filter((t) => t.is_active && t.id !== selected?.id));
  let into = $derived(mergeTargets.find((t) => t.id === destination));
  function openEditor(tag = null) {
    selected = tag;
    name = tag?.name || '';
    color = tag?.color || 'blue';
    error = '';
    panel = tag ? 'edit' : 'create';
  }
  function openMerge(tag) {
    selected = tag;
    destination = '';
    confirmed = false;
    error = '';
    panel = 'merge';
  }
  function reorder(key) {
    if (sort === key) descending = !descending;
    else {
      sort = key;
      descending = key === 'usage';
    }
  }
  async function perform(action, values) {
    if (busy) return;
    busy = true;
    error = '';
    try {
      const body = new FormData();
      Object.entries(values).forEach(([key, value]) => body.set(key, String(value)));
      const response = await fetch(`?/${action}`, {
        method: 'POST',
        body,
        headers: { 'x-sveltekit-action': 'true' }
      });
      const result = /** @type {any} */ (deserialize(await response.text()));
      if (result.type !== 'success')
        throw new Error(
          result.type === 'failure'
            ? String(result.data?.[action]?.error || 'Could not save. Please try again.')
            : 'Could not save. Please try again.'
        );
      panel = '';
      toast.success(
        {
          create: 'Tag saved',
          edit: 'Tag updated',
          archive: 'Tag archived. Existing records keep it.',
          restore: 'Tag restored',
          merge: 'Tags merged'
        }[action]
      );
      if (action === 'create' || action === 'restore') {
        status = 'active';
        query = '';
        object = '';
      }
      await invalidateAll();
    } catch (cause) {
      error = cause.message || 'Could not save. Please try again.';
    } finally {
      busy = false;
    }
  }
  function submit(event) {
    event.preventDefault();
    if (panel === 'merge') {
      if (confirmed && destination) void perform('merge', { id: selected.id, into: destination });
    } else
      void perform(panel, { ...(selected ? { id: selected.id } : {}), name: name.trim(), color });
  }
</script>

<PageHeader title="Tags">
  {#snippet actions()}{#if data.can_edit}<button
        class="v2-btn v2-btn-primary"
        disabled={busy}
        onclick={() => openEditor()}><Plus size={16} />New tag</button
      >{/if}{/snippet}
</PageHeader>
<div class="tag-settings">
  <div class="status-filters" role="group" aria-label="Tag status">
    {#each filters as filter}<button
        type="button"
        class:chosen={status === filter.key}
        aria-pressed={status === filter.key}
        onclick={() => (status = filter.key)}>{filter.label}<span>{filter.count}</span></button
      >{/each}
  </div>
  <div class="toolbar">
    <label class="search"
      ><Search size={16} /><input
        aria-label="Search tags"
        type="search"
        placeholder="Search tags…"
        bind:value={query}
      /></label
    >
    <select class="v2-input object-filter" aria-label="Filter tags by object" bind:value={object}
      ><option value="">All objects</option>{#each objectOptions as [key, label]}<option value={key}
          >{label}</option
        >{/each}</select
    >
  </div>
  {#if error && !panel}<p class="v2-error" role="alert">{error}</p>{/if}
  <!-- svelte-ignore a11y_no_noninteractive_tabindex (Keyboard access to horizontal scrolling.) -->
  <div class="tag-table" role="region" aria-label="Tags list" tabindex="0">
    <table>
      <thead
        ><tr>
          <th
            scope="col"
            aria-sort={sort === 'name' ? (descending ? 'descending' : 'ascending') : 'none'}
            ><button onclick={() => reorder('name')}
              >Tag {sort === 'name' ? (descending ? '↓' : '↑') : ''}</button
            ></th
          >
          <th
            scope="col"
            aria-sort={sort === 'usage' ? (descending ? 'descending' : 'ascending') : 'none'}
            ><button onclick={() => reorder('usage')}
              >Used in records {sort === 'usage' ? (descending ? '↓' : '↑') : ''}</button
            ></th
          >
          <th scope="col">Status</th>{#if data.can_edit}<th scope="col" class="actions-heading"
              >Actions</th
            >{/if}
        </tr></thead
      >
      <tbody
        >{#each tags as tag (tag.id)}
          <tr>
            <td><TagBadge {tag} /></td>
            <td
              >{#if used(tag)}<button
                  class="usage-button"
                  aria-expanded={expanded === tag.id}
                  aria-controls={`usage-${tag.id}`}
                  onclick={() => (expanded = expanded === tag.id ? '' : tag.id)}
                  >{used(tag).toLocaleString()}
                  {used(tag) === 1 ? 'record' : 'records'}<ChevronDown size={13} /></button
                >{:else}<span class="muted">Unused</span>{/if}</td
            >
            <td
              ><span class="status" class:archived={!tag.is_active}
                >{tag.is_active ? 'Active' : 'Archived'}</span
              ></td
            >
            {#if data.can_edit}<td class="row-actions"
                ><Dropdown.Root>
                  <Dropdown.Trigger
                    class="v2-btn v2-btn-sm"
                    disabled={busy}
                    aria-label={`Actions for ${tag.name}`}
                    >Actions<ChevronDown size={13} /></Dropdown.Trigger
                  >
                  <Dropdown.Content align="end">
                    <Dropdown.Item onclick={() => openEditor(tag)}
                      ><Pencil size={14} />Edit name & color</Dropdown.Item
                    >
                    {#if tag.is_active}
                      <Dropdown.Item
                        disabled={data.tags.filter((t) => t.is_active).length < 2}
                        onclick={() => openMerge(tag)}><Merge size={14} />Merge</Dropdown.Item
                      >
                      <Dropdown.Separator />
                      <Dropdown.Item onclick={() => perform('archive', { id: tag.id })}
                        ><Archive size={14} />Archive</Dropdown.Item
                      >
                    {:else}<Dropdown.Item onclick={() => perform('restore', { id: tag.id })}
                        ><RotateCcw size={14} />Restore</Dropdown.Item
                      >{/if}
                  </Dropdown.Content>
                </Dropdown.Root></td
              >{/if}
          </tr>
          {#if expanded === tag.id}<tr id={`usage-${tag.id}`} class="usage-row"
              ><td colspan={data.can_edit ? 4 : 3}
                ><div class="usage-details">
                  {#each usage(tag) as [key, total]}<span
                      >{labelFor(key)} <strong>{Number(total).toLocaleString()}</strong></span
                    >{/each}
                </div></td
              ></tr
            >{/if}
        {:else}<tr
            ><td class="empty" colspan={data.can_edit ? 4 : 3}
              >{data.tags.length ? 'No tags match these filters.' : 'No tags yet.'}</td
            ></tr
          >{/each}</tbody
      >
    </table>
  </div>
</div>

{#if panel}<TeamPanel
    title={panel === 'create' ? 'New tag' : panel === 'edit' ? 'Edit tag' : 'Merge tags'}
    {busy}
    onclose={() => {
      panel = '';
      error = '';
    }}
  >
    <form class="panel-form" onsubmit={submit}>
      <div class="panel-body">
        {#if panel === 'merge'}
          <div class="merge-source"><span>Merge</span><TagBadge tag={selected} /></div>
          <label class="field"
            >Into<select class="v2-input" bind:value={destination} required disabled={busy}
              ><option value="">Select the tag to keep</option>{#each mergeTargets as target}<option
                  value={target.id}>{target.name}</option
                >{/each}</select
            ></label
          >
          {#if into}<p class="merge-info">
              Records tagged <strong>{selected.name}</strong> will use <strong>{into.name}</strong>.
              Existing assignments of that tag stay unchanged. <strong>{selected.name}</strong> will be
              archived. This merge cannot be undone.
            </p>
            <label class="confirm"
              ><input type="checkbox" required bind:checked={confirmed} disabled={busy} />Confirm
              merge into {into.name}</label
            >{/if}
        {:else}
          <label class="field"
            >Name<input
              class="v2-input"
              bind:value={name}
              required
              maxlength="50"
              disabled={busy}
              placeholder="e.g. VIP"
            /></label
          >
          <fieldset disabled={busy} class="color-field">
            <legend>Color</legend>
            <div class="colors">
              {#each Object.entries(tagColors) as [key, hex]}<label
                  class="swatch"
                  class:selected={color === key}
                  style:--swatch={hex}
                  title={key}
                  ><input
                    type="radio"
                    name="tag-color"
                    value={key}
                    bind:group={color}
                    aria-label={key}
                  />{#if color === key}<Check size={16} />{/if}</label
                >{/each}
            </div>
          </fieldset>
          <div class="tag-example"><TagBadge tag={{ name: name.trim() || 'Tag', color }} /></div>
        {/if}
        {#if error}<p class="v2-error" role="alert">{error}</p>{/if}
      </div>
      <footer class="panel-footer">
        <button
          class="v2-btn"
          type="button"
          disabled={busy}
          onclick={() => {
            panel = '';
            error = '';
          }}>Cancel</button
        ><button
          class="v2-btn v2-btn-primary"
          disabled={busy || (panel === 'merge' ? !confirmed || !destination : !name.trim())}
          >{busy
            ? 'Saving…'
            : panel === 'create'
              ? 'Create tag'
              : panel === 'edit'
                ? 'Save changes'
                : 'Merge tags'}</button
        >
      </footer>
    </form>
  </TeamPanel>{/if}

<style>
  .tag-settings {
    padding: 0 var(--v2-pad, 24px) 24px;
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }
  .status-filters {
    display: flex;
    gap: 16px;
    border-bottom: 1px solid var(--v2-line);
    flex-shrink: 0;
    overflow-x: auto;
  }
  .status-filters button {
    border: 0;
    border-bottom: 2px solid transparent;
    background: transparent;
    padding: 12px 2px;
    color: var(--v2-slate);
    display: flex;
    gap: 8px;
    align-items: center;
    cursor: pointer;
    font-size: 13px;
  }
  .status-filters button.chosen {
    border-bottom-color: var(--v2-ink);
    color: var(--v2-ink);
    font-weight: 600;
  }
  .status-filters span {
    font-size: 11px;
    padding: 2px 6px;
    border-radius: 5px;
    background: var(--v2-line-soft);
    font-variant-numeric: tabular-nums;
  }
  .toolbar {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    padding: 18px 0;
    flex-shrink: 0;
  }
  .search {
    display: flex;
    align-items: center;
    gap: 8px;
    border: 1px solid var(--v2-line);
    background: var(--v2-card);
    padding: 0 12px;
    border-radius: 7px;
    color: var(--v2-slate);
    width: min(320px, 100%);
  }
  .search input {
    border: 0;
    background: transparent;
    width: 100%;
    padding: 10px 0;
    min-width: 0;
    color: var(--v2-ink);
    font-size: 13px;
    outline: 0;
  }
  .search:focus-within {
    outline: 2px solid var(--v2-slate);
    outline-offset: 2px;
  }
  .object-filter {
    width: 180px;
    font-size: 13px;
  }
  .tag-table {
    overflow: auto;
    min-height: 0;
    border: 1px solid var(--v2-line);
    border-radius: 9px;
    background: var(--v2-card);
  }
  table {
    width: 100%;
    border-collapse: collapse;
    text-align: left;
    font-size: 13px;
    min-width: 470px;
  }
  th {
    color: var(--v2-slate);
    font-size: 12px;
    font-weight: 500;
    position: sticky;
    top: 0;
    background: var(--v2-card);
    z-index: 1;
  }
  th,
  td {
    padding: 12px 16px;
    border-bottom: 1px solid var(--v2-line-soft);
  }
  tr:last-child td {
    border-bottom: 0;
  }
  th button {
    border: 0;
    background: transparent;
    padding: 0;
    font: inherit;
    color: inherit;
    cursor: pointer;
  }
  tbody tr:hover {
    background: var(--v2-bg);
  }
  .muted {
    color: var(--v2-slate);
  }
  .usage-button {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    border: 0;
    background: transparent;
    color: var(--v2-ink);
    padding: 3px 0;
    cursor: pointer;
    font: inherit;
  }
  .status {
    font-size: 12px;
    color: var(--v2-ink);
  }
  .status.archived {
    color: var(--v2-slate);
  }
  .row-actions,
  .actions-heading {
    text-align: right;
    width: 120px;
  }
  .usage-details {
    display: flex;
    flex-wrap: wrap;
    gap: 12px 24px;
    color: var(--v2-slate);
    font-size: 12px;
  }
  .usage-details strong {
    margin-left: 6px;
    font-variant-numeric: tabular-nums;
    color: var(--v2-ink);
  }
  .usage-row {
    background: var(--v2-bg);
  }
  .empty {
    padding: 40px 16px;
    text-align: center;
    color: var(--v2-slate);
  }
  .color-field {
    border: 0;
    padding: 0;
    margin: 0;
  }
  .color-field legend {
    font-size: 13px;
    font-weight: 500;
    margin-bottom: 12px;
  }
  .colors {
    display: grid;
    grid-template-columns: repeat(9, 30px);
    gap: 12px;
  }
  .swatch {
    position: relative;
    height: 30px;
    border-radius: 50%;
    background: var(--swatch);
    display: flex;
    align-items: center;
    justify-content: center;
    color: #172033;
    cursor: pointer;
  }
  .swatch input {
    position: absolute;
    width: 100%;
    height: 100%;
    inset: 0;
    margin: 0;
    opacity: 0;
    cursor: pointer;
  }
  .swatch.selected {
    outline: 2px solid var(--v2-ink);
    outline-offset: 3px;
  }
  .swatch:focus-within {
    outline: 2px solid var(--v2-ink);
    outline-offset: 3px;
  }
  .tag-example {
    margin-top: 24px;
  }
  .merge-source {
    display: flex;
    gap: 12px;
    align-items: center;
    margin-bottom: 24px;
    font-size: 13px;
  }
  .merge-info {
    font-size: 13px;
    line-height: 1.7;
    color: var(--v2-slate);
  }
  .confirm {
    display: flex;
    gap: 8px;
    align-items: center;
    font-size: 13px;
    margin-top: 20px;
  }
  @media (max-width: 600px) {
    .tag-settings {
      padding: 0 16px 16px;
    }
    .colors {
      grid-template-columns: repeat(6, 30px);
    }
    .status-filters {
      gap: 12px;
    }
    .search {
      width: 100%;
    }
    .object-filter {
      width: 100%;
    }
  }
</style>
