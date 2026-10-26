<script>
  import { useI18n } from '$lib/i18n/context.js';
  import * as Popover from '$lib/components/ui/popover/index.js';
  const { ui } = useI18n();

  import { onMount } from 'svelte';
  import { X, SlidersHorizontal, PanelLeft, PanelLeftClose } from '@lucide/svelte';
  /** @type {{fields: any[], selected: string[], onToggle: (key: string) => void, onShowAll?: () => void, onReset?: () => void, actionsVisible?: boolean, onActionsChange?: (visible: boolean) => void}} */
  let {
    fields,
    selected,
    onToggle,
    onShowAll,
    onReset,
    actionsVisible = true,
    onActionsChange
  } = $props();
  let compact = $state(false);
  onMount(() => {
    try {
      compact = localStorage.getItem('crm-list-density') === 'compact';
    } catch {
      /* Storage may be disabled. */
    }
    document.documentElement.dataset.crmDensity = compact ? 'compact' : 'comfortable';
  });
  function setDensity(event) {
    event.stopPropagation();
    compact = event.currentTarget.checked;
    document.documentElement.dataset.crmDensity = compact ? 'compact' : 'comfortable';
    try {
      localStorage.setItem('crm-list-density', compact ? 'compact' : 'comfortable');
    } catch {
      /* The current view still works without persistence. */
    }
  }
  let open = $state(false);
  let search = $state('');
  let searchInput = $state();
  const matches = $derived(
    fields.filter(([, label]) => label.toLowerCase().includes(search.trim().toLowerCase()))
  );
</script>

{#if onActionsChange}
  <button
    type="button"
    class="v2-btn v2-btn-icon column-picker-trigger"
    aria-label={actionsVisible ? ui('Hide actions column') : ui('Show actions column')}
    title={actionsVisible ? ui('Hide actions column') : ui('Show actions column')}
    aria-expanded={actionsVisible}
    onclick={() => onActionsChange(!actionsVisible)}
  >
    {#if actionsVisible}<PanelLeft size={16} />{:else}<PanelLeftClose size={16} />{/if}
  </button>
{/if}

<Popover.Root bind:open onOpenChange={() => (search = '')}>
  <Popover.Trigger asChild class="">
    {#snippet child({ props })}
      <button
        {...props}
        type="button"
        class="v2-btn v2-btn-icon column-picker-trigger column-picker-settings"
        aria-label={ui('Edit columns')}
        title={ui('Edit columns')}><SlidersHorizontal size={16} /></button
      >
    {/snippet}
  </Popover.Trigger>
  <Popover.Content
    class="column-picker-popover"
    align="end"
    collisionPadding={12}
    aria-label={ui('Visible columns')}
    onOpenAutoFocus={(event) => {
      event.preventDefault();
      searchInput?.focus();
    }}
  >
    <div class="picker-heading">
      <strong>{ui('Columns')}</strong><button
        type="button"
        aria-label={ui('Close columns')}
        onclick={() => {
          open = false;
        }}><X size={16} /></button
      >
    </div>
    <input
      class="v2-input"
      type="search"
      placeholder={ui('Search columns…')}
      aria-label={ui('Search columns')}
      bind:this={searchInput}
      bind:value={search}
      oninput={(event) => event.stopPropagation()}
      onkeydown={(event) => {
        if (event.key === 'Enter') event.preventDefault();
      }}
    />
    <div class="picker-actions">
      <span aria-live="polite">{selected.length} {ui('of')} {fields.length}</span>
      {#if onShowAll}<button type="button" onclick={onShowAll}>{ui('Show all')}</button>{/if}
      {#if onReset}<button type="button" onclick={onReset}>{ui('Reset')}</button>{/if}
    </div>
    <label class="density-option"
      ><input
        type="checkbox"
        checked={compact}
        oninput={(event) => event.stopPropagation()}
        onchange={setDensity}
      />{ui('Compact rows')}</label
    >
    <div class="options">
      {#each matches as [key, label] (key)}
        <label
          ><input
            type="checkbox"
            checked={selected.includes(key)}
            disabled={selected.length === 1 && selected.includes(key)}
            oninput={(event) => event.stopPropagation()}
            onchange={() => onToggle(key)}
          />{label}</label
        >
      {:else}<p>{ui('No matching columns.')}</p>{/each}
    </div>
  </Popover.Content>
</Popover.Root>

<style>
  .column-picker-trigger {
    width: 30px;
    height: 30px;
    min-height: 30px;
    padding: 0;
    border-color: transparent;
    background: transparent;
  }
  :global(.column-picker-popover) {
    width: min(280px, calc(100vw - 24px));
    max-height: min(34rem, var(--bits-popover-content-available-height));
    overflow: auto;
    padding: 10px;
    background: var(--crm-surface);
    color: var(--crm-text);
    border: 1px solid var(--crm-border);
    box-shadow: var(--crm-shadow-lg);
  }
  .density-option {
    border-bottom: 1px solid var(--crm-border);
  }
  .v2-input {
    width: 100%;
    min-width: 0;
  }
  .options {
    max-height: min(18rem, 40dvh);
    overflow-y: auto;
    margin-top: 6px;
  }
  label {
    display: flex;
    align-items: center;
    gap: 9px;
    min-height: 2.75rem;
    padding: var(--crm-space-2);
    border-radius: var(--crm-radius-sm);
    font-size: var(--crm-text-sm);
    cursor: pointer;
  }
  label:hover {
    background: var(--crm-surface-secondary);
  }
  label input {
    margin: 0;
    accent-color: var(--v2-accent, var(--crm-info));
  }
  p {
    padding: var(--crm-space-2);
    font-size: var(--crm-text-sm);
    color: var(--v2-muted);
  }
  .picker-heading {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: var(--crm-text-sm);
  }
  .picker-heading button {
    display: grid;
    place-items: center;
    min-width: 2.75rem;
    min-height: 2.75rem;
  }
  .picker-actions {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-top: 0.5rem;
    font-size: var(--crm-text-xs);
  }
  .picker-actions span {
    margin-right: auto;
    color: var(--v2-muted);
  }
  .picker-actions button {
    min-height: 2.75rem;
    padding: 0.375rem;
    text-decoration: underline;
  }
  @media (max-width: 700px), (pointer: coarse) {
    .actions-visibility {
      margin-block: 6px 10px;
      background: var(--crm-surface-subtle);
      font-weight: 600;
    }
    .density-option {
      display: none;
    }
  }
</style>
