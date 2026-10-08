<script>
  import { useI18n } from '$lib/i18n/context.js';
  import { X } from '@lucide/svelte';
  const { ui } = useI18n();
  let { records, chosen, onselect, onremove, label = 'Associated Objects' } = $props();
  const id = $props.id();
  let query = $state('');
  let open = $state(false);
  let active = $state(-1);
  const showingResults = $derived(open && query.trim().length > 0);
  let root;
  const matches = $derived(
    records
      .filter(
        (item) =>
          !chosen.some((record) => record.type === item.type && record.id === item.id) &&
          `${item.name} ${item.email ?? ''} ${ui(item.label)}`
            .toLowerCase()
            .includes(query.trim().toLowerCase())
      )
      .slice(0, 20)
  );
  function choose(item) {
    onselect(item);
    query = '';
    open = false;
    active = -1;
  }
  function outside(event) {
    if (!root?.contains(event.target)) open = false;
  }
  function keyboard(event) {
    if (event.key === 'Escape') {
      event.preventDefault();
      event.stopPropagation();
      open = false;
      active = -1;
    } else if (['ArrowDown', 'ArrowUp'].includes(event.key)) {
      event.preventDefault();
      if (!query.trim()) return;
      open = true;
      active = matches.length
        ? (active + (event.key === 'ArrowDown' ? 1 : -1) + matches.length) % matches.length
        : -1;
    } else if (event.key === 'Enter') {
      event.preventDefault();
      if (showingResults && matches.length && (active >= 0 || matches.length === 1))
        choose(matches[Math.max(active, 0)]);
    }
  }
</script>

<svelte:window onpointerdown={outside} onfocusin={outside} />
<div class="parent-picker" bind:this={root}>
  <label for={`${id}-input`}>{ui(label)}</label>
  {#if chosen.length}
    <div class="chosen-records">
      {#each chosen as record (`${record.type}-${record.id}`)}
        <span class="chosen">
          <span>{record.name}</span>
          <button
            type="button"
            class="v2-btn v2-btn-icon"
            aria-label={`${ui('Remove association')}: ${record.name}`}
            onclick={() => onremove(record)}><X size={15} /></button
          >
        </span>
      {/each}
    </div>
  {/if}
  <input
    id={`${id}-input`}
    class="v2-input"
    placeholder={ui('Search associations…')}
    bind:value={query}
    autocomplete="off"
    role="combobox"
    aria-autocomplete="list"
    aria-expanded={showingResults}
    aria-controls={`${id}-results`}
    aria-activedescendant={showingResults && active >= 0 ? `${id}-option-${active}` : undefined}
    onclick={() => {
      open = true;
    }}
    onfocus={() => {
      open = true;
      active = -1;
    }}
    oninput={() => {
      open = true;
      active = -1;
    }}
    onkeydown={keyboard}
  />
  {#if showingResults}<div
      class="matches"
      id={`${id}-results`}
      role="listbox"
      aria-label={ui(label)}
    >
      {#each matches as item, index (`${item.type}-${item.id}`)}<button
          id={`${id}-option-${index}`}
          type="button"
          role="option"
          aria-selected={active === index}
          class:active={active === index}
          onclick={() => choose(item)}
          ><small>{ui(item.label)}</small><strong>{item.name}</strong>{#if item.email}<small
              >{item.email}</small
            >{/if}</button
        >
      {:else}<p role="status">{ui('No matches.')}</p>{/each}
    </div>{/if}
</div>

<style>
  .parent-picker {
    display: grid;
    gap: var(--crm-space-2);
    margin-bottom: var(--crm-space-5);
    font-size: var(--crm-text-xs);
    min-width: 0;
  }
  .chosen-records {
    display: flex;
    flex-wrap: wrap;
    gap: var(--crm-space-2);
  }
  .chosen {
    display: inline-flex;
    align-items: center;
    gap: var(--crm-space-1);
    max-width: 100%;
    padding-left: var(--crm-space-2);
    background: var(--crm-surface-secondary);
    border: 1px solid var(--crm-border);
    border-radius: var(--crm-radius-md);
  }
  .chosen > span {
    min-width: 0;
    overflow-wrap: anywhere;
  }
  small {
    display: block;
    color: var(--crm-text-muted);
    font-size: var(--crm-text-xs);
    margin-block: var(--crm-space-1);
  }
  strong {
    font-weight: 600;
  }
  .matches {
    max-height: 16rem;
    overflow: auto;
    border: 1px solid var(--crm-border);
    border-radius: var(--crm-radius-md);
    background: var(--crm-surface);
  }
  .matches button {
    display: block;
    padding: var(--crm-space-3);
    width: 100%;
    text-align: left;
    cursor: pointer;
    font: inherit;
    border: 0;
    background: transparent;
    color: var(--crm-text);
    overflow-wrap: anywhere;
  }
  .matches button:hover,
  .matches button.active {
    background: var(--crm-surface-selected);
  }
  .matches button:focus-visible {
    outline: 2px solid var(--crm-focus);
    outline-offset: -2px;
  }
  .matches p {
    padding: var(--crm-space-3);
    margin: 0;
  }
</style>
