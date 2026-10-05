<script>
  import { untrack, getContext } from 'svelte';
  import { deserialize } from '$app/forms';
  import TagBadge from './TagBadge.svelte';
  import { tagColors } from '$lib/v2/tag-colors.js';
  /** @type {{options?:any[],selected?:string[],original?:string[],canCreate?:boolean,creating?:boolean,onSearch?:(query:string)=>void,inputId?:string}} */
  let {
    options = [],
    selected = $bindable([]),
    original = [],
    creating = $bindable(false),
    canCreate = false,
    onSearch = () => {},
    inputId = undefined
  } = $props();
  const creation = getContext('creation-panel');
  let available = $state(untrack(() => [...options]));
  $effect(() => {
    const incoming = options;
    // Keep selected tag labels while later search results arrive.
    available = [
      ...new Map(
        [...untrack(() => available), ...incoming].map((tag) => [String(tag.id), tag])
      ).values()
    ];
  });
  const originalValue = untrack(() => JSON.stringify([...original].map(String).sort()));
  let search = $state(''),
    open = $state(false),
    error = $state(''),
    color = $state('blue');
  const matches = $derived(
    available.filter(
      (t) =>
        (t.is_active !== false || selected.includes(String(t.id))) &&
        !selected.includes(String(t.id)) &&
        t.name.toLowerCase().includes(search.trim().toLowerCase())
    )
  );
  const exact = $derived(
    available.find((t) => t.name.toLowerCase() === search.trim().toLowerCase())
  );
  const picked = $derived(available.filter((t) => selected.includes(String(t.id))));
  function choose(tag) {
    selected = [...new Set([...selected, String(tag.id)])];
    search = '';
    onSearch('');
    error = '';
    open = false;
  }
  async function create() {
    if (creating || !search.trim() || !canCreate) return;
    if (exact) {
      choose(exact);
      return;
    }
    creating = true;
    error = '';
    try {
      const body = new FormData();
      body.set('name', search.trim());
      body.set('color', color);
      const response = await fetch(
        creation ? new URL('?/createTag', creation.url) : '?/createTag',
        {
          method: 'POST',
          body,
          headers: { 'x-sveltekit-action': 'true' }
        }
      );
      const result = deserialize(await response.text());
      if (result.type !== 'success' || !result.data?.tag) {
        error =
          result.type === 'failure'
            ? String(result.data?.error || 'Could not create tag.')
            : 'Could not create tag.';
        return;
      }
      const tag = /** @type {{id:string,name:string,color:string}} */ (result.data.tag);
      available = [...available.filter((t) => t.id !== tag.id), tag];
      choose(tag);
    } catch {
      error = 'Could not confirm tag creation. Refresh before trying again.';
    } finally {
      creating = false;
    }
  }
</script>

<div
  data-stage-field="tags"
  class="picker"
  onfocusout={(e) => {
    if (!e.currentTarget.contains(/** @type {Node|null} */ (e.relatedTarget))) open = false;
  }}
>
  <input type="hidden" name="tags_present" value="1" />
  <input type="hidden" name="tags_original" value={originalValue} />
  {#each selected as id}<input type="hidden" name="tags" value={id} />{/each}
  <div class="input-shell">
    {#each picked as tag (tag.id)}<span class="chip"
        ><TagBadge {tag} /><button
          type="button"
          aria-label={`Remove ${tag.name}`}
          disabled={creating}
          onclick={() => (selected = selected.filter((id) => id !== String(tag.id)))}>×</button
        ></span
      >{/each}
    <input
      id={inputId}
      aria-label={canCreate ? 'Search or create tag' : 'Search tags'}
      placeholder={canCreate ? 'Search or create tag…' : 'Search tags…'}
      maxlength="50"
      autocomplete="off"
      bind:value={search}
      disabled={creating}
      onfocus={() => (open = true)}
      oninput={() => {
        open = true;
        error = '';
        onSearch(search);
      }}
      onkeydown={(e) => {
        if (e.key === 'Escape') {
          e.preventDefault();
          open = false;
        }
        if (e.key === 'Enter') {
          e.preventDefault();
          if (exact) choose(exact);
          else if (search.trim()) void create();
        }
      }}
    />
  </div>
  {#if open}<div class="menu">
      <div class="options">
        {#each matches as tag (tag.id)}<button
            type="button"
            class="option"
            disabled={creating}
            onclick={() => choose(tag)}><TagBadge {tag} /></button
          >{/each}
      </div>
      {#if search.trim() && !exact && canCreate}
        <div class="create">
          <div class="colors" role="group" aria-label="Tag color">
            {#each Object.entries(tagColors) as [name, hex]}<button
                type="button"
                class="swatch"
                style:background={hex}
                aria-label={name}
                title={name}
                aria-pressed={color === name}
                disabled={creating}
                onclick={() => (color = name)}>{color === name ? '✓' : ''}</button
              >{/each}
          </div>
          <button type="button" class="create-button" disabled={creating} onclick={create}
            >{creating ? 'Creating…' : '＋ Create'}
            <TagBadge tag={{ name: search.trim(), color }} /></button
          >
        </div>
      {:else if !matches.length}<p>No matching tags.</p>{/if}
      {#if error}<p role="alert" class="error">{error}</p>{/if}
    </div>{/if}
</div>

<style>
  .picker {
    position: relative;
    min-width: 0;
  }
  .input-shell {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 5px;
    border: 1px solid var(--crm-control-border);
    border-radius: var(--crm-radius-sm);
    padding: 7px;
    background: var(--v2-bg, white);
    min-height: 40px;
  }
  .input-shell:focus-within {
    border-color: var(--crm-focus);
    outline: 2px solid var(--crm-focus);
    outline-offset: 2px;
  }
  .input-shell input {
    flex: 1;
    min-width: 140px;
    width: 100%;
    border: 0;
    outline: 0;
    background: transparent;
    font: inherit;
    font-size: var(--crm-text-sm);
    padding: 3px;
    color: inherit;
  }
  .chip {
    display: inline-flex;
    align-items: center;
    gap: 2px;
    max-width: 100%;
  }
  .chip button {
    border: 0;
    background: transparent;
    color: var(--crm-text-muted);
    font-size: var(--crm-text-lg);
    cursor: pointer;
    padding: 0 3px;
  }
  .menu {
    border: 1px solid var(--v2-line);
    border-radius: var(--crm-radius-md);
    background: var(--v2-bg, white);
    margin-top: 5px;
    padding: var(--crm-space-2);
    box-shadow: var(--crm-shadow-sm);
  }
  .options {
    max-height: 180px;
    overflow: auto;
  }
  .option {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 6px;
    border: 0;
    background: transparent;
    cursor: pointer;
    text-align: left;
  }
  .option:hover {
    background: var(--v2-line-soft);
  }
  .colors {
    display: flex;
    flex-wrap: wrap;
    gap: var(--crm-space-2);
    padding: var(--crm-space-2) 2px;
  }
  .swatch {
    width: 22px;
    height: 22px;
    border: 2px solid transparent;
    border-radius: 50%;
    padding: 0;
    cursor: pointer;
    color: white;
    font-size: var(--crm-text-sm);
    text-shadow: 0 1px 2px #0009;
  }
  .swatch[aria-pressed='true'] {
    outline: 2px solid var(--crm-text);
    outline-offset: 2px;
  }
  .create-button {
    display: flex;
    align-items: center;
    gap: 6px;
    width: 100%;
    padding: var(--crm-space-2) var(--crm-space-1);
    background: transparent;
    border: 0;
    cursor: pointer;
    font: inherit;
    font-size: var(--crm-text-sm);
    color: var(--v2-ink);
  }
  p {
    font-size: var(--crm-text-xs);
    padding: var(--crm-space-1);
    margin: 0;
  }
  .error {
    color: var(--crm-danger);
  }
  button:focus-visible {
    outline: 2px solid var(--crm-info);
    outline-offset: 2px;
  }
</style>
