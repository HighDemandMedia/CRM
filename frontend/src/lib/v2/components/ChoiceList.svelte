<script>
  import { tick } from 'svelte';
  import { matchesChoice } from '$lib/v2/choice-search.js';
  import { Check, Search } from '@lucide/svelte';
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();
  /** @type {{options?:any[],value?:string|string[],multiple?:boolean,label:string,query?:string,onchange?:(value:any)=>void,onsearch?:(query:string)=>void,loading?:boolean,error?:string,searchable?:boolean,disabled?:boolean,renderOption?:import('svelte').Snippet<[any]>}} */
  let {
    options = [],
    value = $bindable(''),
    multiple = false,
    label,
    query = $bindable(''),
    onchange = () => {},
    onsearch = () => {},
    loading = false,
    error = '',
    searchable = true,
    disabled = false,
    renderOption
  } = $props();
  const id = $props.id();
  let searchInput = $state(),
    list = $state();
  let active = $state(-1);
  const filtered = $derived(options.filter((option) => matchesChoice(option, query)));
  const selected = (option) =>
    multiple
      ? Array.isArray(value) && value.map(String).includes(String(option.value))
      : String(value ?? '') === String(option.value);
  async function choose(option) {
    if (disabled) return;
    const key = String(option.value);
    value = multiple
      ? selected(option)
        ? (Array.isArray(value) ? value : []).filter((item) => String(item) !== key)
        : [...(Array.isArray(value) ? value : []), key]
      : key;
    onchange(value);
    if (multiple) {
      await tick();
      searchInput?.focus({ preventScroll: true });
    }
  }
  function navigate(event) {
    if (['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) {
      if (!filtered.length) return;
      event.preventDefault();
      event.stopPropagation();
      active =
        event.key === 'Home'
          ? 0
          : event.key === 'End'
            ? filtered.length - 1
            : Math.max(
                0,
                Math.min(filtered.length - 1, active + (event.key === 'ArrowDown' ? 1 : -1))
              );
      void tick().then(() =>
        list?.querySelector(`[data-index="${active}"]`)?.scrollIntoView({ block: 'nearest' })
      );
    } else if (event.key === 'Enter') {
      event.preventDefault();
      event.stopPropagation();
      if (filtered[active < 0 ? 0 : active]) void choose(filtered[active < 0 ? 0 : active]);
    }
  }
</script>

<div class="choice-picker">
  {#if searchable}<div class="choice-search">
      <Search size={15} aria-hidden="true" />
      <input
        bind:this={searchInput}
        type="search"
        {disabled}
        role="combobox"
        aria-label={`${ui('Search options')}: ${label}`}
        aria-expanded="true"
        aria-controls={`${id}-options`}
        aria-autocomplete="list"
        aria-activedescendant={active >= 0 && filtered[active]
          ? `${id}-option-${active}`
          : undefined}
        placeholder={ui('Search…')}
        bind:value={query}
        oninput={(event) => {
          event.stopPropagation();
          active = -1;
          onsearch(query);
        }}
        onkeydown={navigate}
        autocomplete="off"
      />
    </div>{/if}
  <div
    bind:this={list}
    id={`${id}-options`}
    class="choice-options"
    role="listbox"
    aria-label={label}
    aria-multiselectable={multiple || undefined}
    aria-busy={loading}
  >
    {#each filtered as option, index (option.value)}
      <button
        type="button"
        role="option"
        {disabled}
        id={`${id}-option-${index}`}
        data-index={index}
        aria-selected={selected(option)}
        tabindex={searchable ? -1 : 0}
        class:active={index === active}
        class:selected={selected(option)}
        onpointerdown={(event) => event.preventDefault()}
        onclick={() => choose(option)}
      >
        <span class="mark" class:multiple aria-hidden="true"
          >{#if selected(option)}<Check size={13} />{/if}</span
        >
        <span class="option-label"
          >{#if renderOption}{@render renderOption(option)}{:else}{option.label}{/if}</span
        >
      </button>
    {/each}
  </div>
  {#if error}<p role="alert">{ui(error)}</p>{:else if loading}<p role="status">
      {ui('Loading options…')}
    </p>{:else if !filtered.length}<p role="status">{ui('No results found.')}</p>{/if}
</div>

<style>
  .choice-picker {
    min-width: 0;
    border: 1px solid var(--v2-line);
    border-radius: var(--crm-radius-sm);
    background: var(--v2-card);
    color: var(--v2-ink);
    overflow: hidden;
  }
  .choice-search {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 10px;
    border-bottom: 1px solid var(--v2-line);
    color: var(--v2-slate);
  }
  .choice-search input {
    width: 100%;
    min-width: 0;
    border: 0;
    outline: 0;
    background: transparent;
    color: var(--v2-ink);
    font: inherit;
    font-size: var(--crm-text-sm);
    min-height: 28px;
  }
  .choice-search input:focus-visible {
    outline: none;
    box-shadow: none;
  }
  .choice-search:focus-within {
    box-shadow: inset 0 -2px var(--crm-focus);
  }
  .choice-options {
    max-height: min(11.5rem, 32dvh);
    overflow-y: auto;
    overscroll-behavior: contain;
    padding: 4px;
  }
  .choice-options button {
    width: 100%;
    min-height: 34px;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 8px;
    border: 0;
    border-radius: var(--crm-radius-sm);
    background: transparent;
    color: inherit;
    font: inherit;
    font-size: var(--crm-text-sm);
    text-align: left;
    cursor: pointer;
  }
  .choice-options button:hover,
  .choice-options button.active,
  .choice-options button.selected {
    background: var(--crm-surface-selected);
  }
  .choice-options button:focus-visible {
    outline: 2px solid var(--crm-focus);
    outline-offset: -2px;
  }
  .mark {
    width: 16px;
    height: 16px;
    flex: none;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1px solid transparent;
    color: var(--crm-primary, #c82322);
  }
  .mark.multiple {
    border-color: var(--crm-control-border);
    border-radius: 3px;
  }
  .selected .mark.multiple {
    border-color: var(--crm-primary, #c82322);
  }
  .option-label {
    min-width: 0;
    overflow-wrap: anywhere;
  }
  p {
    padding: 8px 12px;
    margin: 0;
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
  }
  @media (pointer: coarse) {
    .choice-options button {
      min-height: 44px;
    }
  }
</style>
