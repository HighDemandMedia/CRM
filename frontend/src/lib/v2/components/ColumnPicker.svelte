<script>
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();

  import { tick } from 'svelte';
  import { X } from '@lucide/svelte';
  /** @type {{fields: any[], selected: string[], onToggle: (key: string) => void, onShowAll?: () => void, onReset?: () => void}} */
  let { fields, selected, onToggle, onShowAll, onReset } = $props();
  let open = $state(false);
  let search = $state('');
  let root;
  let trigger;
  let searchInput = $state();
  const matches = $derived(
    fields.filter(([, label]) => label.toLowerCase().includes(search.trim().toLowerCase()))
  );
  async function toggle() {
    open = !open;
    search = '';
    if (open) {
      await tick();
      searchInput?.focus();
    }
  }
  function outside(event) {
    if (open && !root?.contains(event.target)) open = false;
  }
</script>

<div class="column-picker" bind:this={root}>
  <button class="v2-btn" type="button" bind:this={trigger} aria-expanded={open} onclick={toggle}
    >{ui('Edit columns')}</button
  >
  {#if open}
    <div class="dropdown" role="group" aria-label={ui('Visible columns')}>
      <div class="picker-heading">
        <strong>{ui('Columns')}</strong><button
          type="button"
          aria-label={ui('Close columns')}
          onclick={() => {
            open = false;
            trigger?.focus();
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
    </div>
  {/if}
</div>
<svelte:window
  onpointerdown={outside}
  onfocusin={outside}
  onkeydown={(event) => {
    if (open && event.key === 'Escape') {
      open = false;
      trigger?.focus();
    }
  }}
/>

<style>
  .column-picker {
    position: relative;
  }
  .dropdown {
    position: absolute;
    top: calc(100% + 6px);
    right: 0;
    z-index: 40;
    width: min(260px, calc(100vw - 32px));
    padding: 10px;
    border: 1px solid var(--v2-line);
    border-radius: var(--crm-radius-md);
    background: var(--v2-bg, white);
    box-shadow: var(--crm-shadow-lg);
  }
  .dropdown > input {
    width: 100%;
    min-width: 0;
  }
  .options {
    max-height: min(300px, 50vh);
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
  @media (max-width: 700px) {
    .dropdown {
      position: fixed;
      top: auto;
      bottom: 1rem;
      left: 1rem;
      right: 1rem;
      width: auto;
      max-height: calc(100dvh - 2rem);
    }
    .options {
      max-height: 50dvh;
    }
  }
</style>
