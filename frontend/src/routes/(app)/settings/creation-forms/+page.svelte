<script>
  import { untrack } from 'svelte';
  import { enhance } from '$app/forms';
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { useI18n } from '$lib/i18n/context.js';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import { insertColumn } from '$lib/v2/column-order.js';
  import { X, Plus, GripVertical } from '@lucide/svelte';
  const { ui } = useI18n();
  let { data, form } = $props();
  let selected = $state(
      untrack(() => data.selected.map((field) => ({ key: field.key, required: field.required })))
    ),
    revision = $state(untrack(() => data.revision)),
    search = $state(''),
    busy = $state(false),
    dragging = $state(''),
    dropGap = $state(null),
    overAvailable = $state(false),
    announcement = $state('');
  $effect(() => {
    revision = data.revision;
    selected = data.selected.map((field) => ({ key: field.key, required: field.required }));
  });
  const available = $derived(
    data.fields.filter(
      (field) =>
        !selected.some((row) => row.key === field.key) &&
        field.label.toLowerCase().includes(search.trim().toLowerCase())
    )
  );
  const fieldFor = (key) => data.fields.find((field) => field.key === key);
  function finishDrag() {
    dragging = '';
    dropGap = null;
    overAvailable = false;
  }
  function startDrag(event, key) {
    if (!data.can_edit || busy) return;
    dragging = key;
    if (event.dataTransfer) {
      event.dataTransfer.effectAllowed = 'move';
      event.dataTransfer.setData('text/plain', key);
    }
  }
  function insert(key, gap) {
    if (!data.can_edit || busy || !fieldFor(key)) return;
    const existing = selected.find((row) => row.key === key);
    if (existing) {
      const rows = new Map(selected.map((row) => [row.key, row]));
      selected = insertColumn(
        selected.map((row) => row.key),
        key,
        gap
      ).map((key) => rows.get(key));
    } else {
      const next = [...selected];
      next.splice(gap, 0, { key, required: false });
      selected = next;
    }
    announcement = `${fieldFor(key).label}: ${selected.findIndex((row) => row.key === key) + 1} / ${selected.length}`;
  }
  function remove(key) {
    if (!data.can_edit || busy || fieldFor(key)?.locked) return;
    selected = selected.filter((row) => row.key !== key);
    announcement = `${fieldFor(key).label}: ${ui('Available properties')}`;
  }
  function position(event) {
    const rows = [...event.currentTarget.querySelectorAll('li[data-field]')];
    const index = rows.findIndex((row) => {
      const rect = row.getBoundingClientRect();
      return event.clientY < rect.top + rect.height / 2;
    });
    return index < 0 ? selected.length : index;
  }
  function overFields(event) {
    if (!dragging || !data.can_edit || busy) return;
    event.preventDefault();
    overAvailable = false;
    dropGap = position(event);
    if (event.dataTransfer) event.dataTransfer.dropEffect = 'move';
  }
  function overProperties(event) {
    dropGap = null;
    if (
      !dragging ||
      !data.can_edit ||
      busy ||
      fieldFor(dragging)?.locked ||
      !selected.some((row) => row.key === dragging)
    )
      return;
    event.preventDefault();
    overAvailable = true;
    if (event.dataTransfer) event.dataTransfer.dropEffect = 'move';
  }
  function leaveZone(event) {
    if (
      !(event.relatedTarget instanceof Node) ||
      !event.currentTarget.contains(event.relatedTarget)
    ) {
      dropGap = null;
      overAvailable = false;
    }
  }
</script>

<PageHeader title={ui('Creation forms')}
  >{#snippet sub()}{ui(
      'Choose the fields your team completes when creating a record.'
    )}{/snippet}</PageHeader
>
<div class="v2-scroll v2-pad editor">
  <label class="object-select"
    >{ui('Object')}
    <select
      class="v2-input"
      value={data.target_model}
      disabled={busy}
      onchange={(event) =>
        goto(resolve(`/settings/creation-forms?object=${event.currentTarget.value}`))}
    >
      {#each data.objects as object (object.value)}<option value={object.value}
          >{ui(object.label)}</option
        >{/each}
    </select>
  </label>
  {#if form?.error}<p class="v2-error" role="alert">{ui(form.error)}</p>{/if}
  {#if form?.saved}<p role="status">
      {ui('Creation form saved. New records use this configuration.')}
    </p>{/if}
  {#if !data.can_edit}<p>{ui('Read only')}</p>{/if}
  <div class="panels">
    <section
      class="panel"
      class:drop-available={overAvailable}
      aria-label={ui('Available properties')}
      ondragover={overProperties}
      ondragleave={leaveZone}
      ondrop={(event) => {
        if (!overAvailable) return;
        event.preventDefault();
        remove(dragging);
        search = '';
        finishDrag();
      }}
    >
      <h2>{ui('Available properties')}</h2>
      <input
        class="v2-input"
        type="search"
        aria-label={ui('Search properties')}
        placeholder={ui('Search properties')}
        bind:value={search}
      />
      <div class="available">
        {#each available as field (field.key)}
          <button
            type="button"
            class="property-option"
            draggable={data.can_edit && !busy}
            ondragstart={(event) => startDrag(event, field.key)}
            ondragend={finishDrag}
            disabled={!data.can_edit || busy}
            onclick={() => insert(field.key, selected.length)}
          >
            <span>{field.custom ? field.label : ui(field.label)}</span><Plus size={16} />
          </button>
        {:else}<p>{ui('No matching properties.')}</p>{/each}
      </div>
    </section>
    <form
      method="POST"
      action="?/save"
      class="panel"
      use:enhance={() => {
        busy = true;
        return async ({ update }) => {
          try {
            await update({ reset: false });
          } finally {
            busy = false;
          }
        };
      }}
    >
      <input type="hidden" name="target_model" value={data.target_model} />
      <input type="hidden" name="revision" value={revision} />
      <input type="hidden" name="selected" value={JSON.stringify(selected)} />
      <h2>{ui('Fields in creation order')}</h2>
      <p class="hint">{ui('Required fields must be completed for new records.')}</p>
      <p class="sr-only" aria-live="polite">{announcement}</p>
      <ol
        aria-label={ui('Fields in creation order')}
        ondragover={overFields}
        ondragleave={leaveZone}
        ondrop={(event) => {
          if (!dragging || !data.can_edit || busy) return;
          event.preventDefault();
          insert(dragging, position(event));
          finishDrag();
        }}
      >
        {#each selected as row, index (row.key)}
          {@const field = fieldFor(row.key)}
          {#if field}
            <li
              data-field={row.key}
              draggable={data.can_edit && !busy}
              class:dragging={dragging === row.key}
              class:drop-before={dropGap === index}
              class:drop-after={dropGap === selected.length && index === selected.length - 1}
              ondragstart={(event) => startDrag(event, row.key)}
              ondragend={finishDrag}
            >
              <button
                type="button"
                class="drag-handle v2-btn v2-btn-icon"
                disabled={!data.can_edit || busy}
                aria-label={ui('Reorder field') + ': ' + field.label}
                title={ui('Drag to reorder, or use the up and down arrow keys')}
                onkeydown={(event) => {
                  if (!['ArrowUp', 'ArrowDown'].includes(event.key)) return;
                  event.preventDefault();
                  insert(row.key, index + (event.key === 'ArrowUp' ? -1 : 2));
                }}><GripVertical size={15} aria-hidden="true" /></button
              >
              <span class="property-name">{field.custom ? field.label : ui(field.label)}</span>
              <label class="required"
                ><input
                  type="checkbox"
                  bind:checked={row.required}
                  disabled={field.locked || !data.can_edit || busy}
                />{ui('Required')}</label
              >
              <div class="row-actions">
                <button
                  type="button"
                  class="v2-btn v2-btn-icon"
                  aria-label={ui('Remove field') + ': ' + field.label}
                  disabled={field.locked || !data.can_edit || busy}
                  onclick={() => remove(row.key)}><X size={15} /></button
                >
              </div>
            </li>
          {/if}
        {/each}
      </ol>
      {#if data.can_edit}<button class="v2-btn v2-btn-primary" disabled={busy}
          >{busy ? ui('Saving…') : ui('Save changes')}</button
        >{/if}
    </form>
  </div>
</div>

<style>
  .editor {
    width: 100%;
  }
  .object-select {
    display: grid;
    gap: var(--crm-space-2);
    max-width: 22rem;
    margin-bottom: var(--crm-space-5);
  }
  .panels {
    display: grid;
    grid-template-columns: minmax(14rem, 1fr) minmax(26rem, 2fr);
    gap: var(--crm-space-5);
    align-items: start;
  }
  .panel {
    background: var(--crm-surface);
    border: 1px solid var(--crm-border);
    border-radius: var(--crm-radius-lg);
    padding: var(--crm-space-5);
    min-width: 0;
  }
  h2 {
    font-size: var(--crm-text-base);
    margin: 0 0 var(--crm-space-3);
  }
  .hint,
  .available p {
    color: var(--crm-text-muted);
    font-size: var(--crm-text-sm);
  }
  .available {
    max-height: 34rem;
    overflow: auto;
    margin-top: var(--crm-space-3);
  }
  .property-option {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--crm-space-2);
    width: 100%;
    min-height: 2.75rem;
    background: transparent;
    color: inherit;
    border: 0;
    border-bottom: 1px solid var(--crm-border);
    text-align: left;
    cursor: pointer;
  }
  .property-option:hover {
    background: var(--crm-surface-secondary);
  }
  ol {
    list-style: none;
    padding: 0;
    margin: var(--crm-space-4) 0;
  }
  li {
    position: relative;
    display: flex;
    align-items: center;
    gap: var(--crm-space-2);
    flex-wrap: wrap;
    padding: var(--crm-space-2) 0;
    border-bottom: 1px solid var(--crm-border);
  }
  .property-name {
    flex: 1;
    min-width: 7rem;
    overflow-wrap: anywhere;
    font-size: var(--crm-text-sm);
  }
  .required,
  .row-actions {
    display: flex;
    align-items: center;
    gap: var(--crm-space-1);
    font-size: var(--crm-text-xs);
  }
  .drag-handle {
    cursor: grab;
    border-color: transparent;
    background: transparent;
  }
  .drag-handle:active {
    cursor: grabbing;
  }
  .drop-before::before,
  .drop-after::after {
    content: '';
    position: absolute;
    left: 0;
    right: 0;
    height: 3px;
    background: var(--crm-primary);
    border-radius: var(--crm-radius-sm);
    pointer-events: none;
  }
  .drop-before::before {
    top: -2px;
  }
  .drop-after::after {
    bottom: -2px;
  }
  .drop-available {
    outline: 2px solid var(--crm-primary);
    outline-offset: 2px;
    background: color-mix(in srgb, var(--crm-primary) 7%, var(--crm-surface));
  }
  .dragging {
    opacity: 0.5;
  }
  @media (max-width: 1000px) {
    .panels {
      grid-template-columns: 1fr;
    }
    .available {
      max-height: 15rem;
    }
  }
</style>
