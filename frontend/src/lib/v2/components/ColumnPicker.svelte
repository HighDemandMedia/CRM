<script>
  import { tick } from 'svelte';
  /** @type {{fields: any[], selected: string[], onToggle: (key: string) => void}} */
  let { fields, selected, onToggle } = $props();
  let open = $state(false);
  let search = $state('');
  let root;
  let trigger;
  let searchInput = $state();
  const matches = $derived(fields.filter(([, label]) => label.toLowerCase().includes(search.trim().toLowerCase())));
  async function toggle() {
    open = !open;
    search = '';
    if (open) { await tick(); searchInput?.focus(); }
  }
  function outside(event) {
    if (open && !root?.contains(event.target)) open = false;
  }
</script>


<div class="column-picker" bind:this={root}>
  <button class="v2-btn" type="button" bind:this={trigger} aria-expanded={open} onclick={toggle}>Edit columns</button>
  {#if open}
    <div class="dropdown" role="group" aria-label="Visible columns">
      <input class="v2-input" type="search" placeholder="Search columns…" aria-label="Search columns"
        bind:this={searchInput} bind:value={search} oninput={(event) => event.stopPropagation()}
        onkeydown={(event) => { if (event.key === 'Enter') event.preventDefault(); }} />
      <div class="options">
        {#each matches as [key, label] (key)}
          <label><input type="checkbox" checked={selected.includes(key)}
            disabled={selected.length === 1 && selected.includes(key)}
            oninput={(event) => event.stopPropagation()}
            onchange={() => onToggle(key)} />{label}</label>
        {:else}<p>No matching columns.</p>{/each}
      </div>
    </div>
  {/if}
</div>
<svelte:window onpointerdown={outside} onfocusin={outside} onkeydown={(event) => { if (open && event.key === 'Escape') { open = false; trigger?.focus(); } }} />

<style>
  .column-picker { position: relative; }
  .dropdown { position: absolute; top: calc(100% + 6px); right: 0; z-index: 40; width: min(260px, calc(100vw - 32px)); padding: 10px; border: 1px solid var(--v2-line); border-radius: 10px; background: var(--v2-bg, white); box-shadow: 0 8px 24px #0002; }
  .dropdown > input { width: 100%; min-width: 0; }
  .options { max-height: min(300px, 50vh); overflow-y: auto; margin-top: 6px; }
  label { display: flex; align-items: center; gap: 9px; padding: 8px; border-radius: 5px; font-size: 13px; cursor: pointer; }
  label:hover { background: #f3f4f6; }
  label input { margin: 0; accent-color: var(--v2-accent, #2563eb); }
  p { padding: 8px; font-size: 13px; color: var(--v2-muted); }
</style>
