<script>
  import { tick } from 'svelte';
  import { ChevronDown } from '@lucide/svelte';
  import * as Popover from '$lib/components/ui/popover/index.js';
  import ChoiceList from '$lib/v2/components/ChoiceList.svelte';
  /** @type {{id?:string,name?:string,value?:string,options:{value:string,label:string,keywords?:string}[],label:string,placeholder?:string,required?:boolean,disabled?:boolean,compactLabel?:string,onchange?:(value:string)=>void,autocomplete?:import('svelte/elements').HTMLSelectAttributes['autocomplete']}} */
  let {
    id,
    name,
    value = $bindable(''),
    options,
    label,
    placeholder = '',
    required = false,
    disabled = false,
    compactLabel,
    onchange,
    autocomplete
  } = $props();
  let open = $state(false),
    query = $state('');
  let nativeSelect = $state(),
    trigger = $state();
  const choices = $derived(placeholder ? [{ value: '', label: placeholder }, ...options] : options);
  const display = $derived(
    compactLabel || choices.find((option) => option.value === value)?.label || value || placeholder
  );
  async function choose(next) {
    if (disabled || nativeSelect?.matches(':disabled')) return;
    value = next;
    open = false;
    await tick();
    nativeSelect?.dispatchEvent(new Event('input', { bubbles: true }));
    nativeSelect?.dispatchEvent(new Event('change', { bubbles: true }));
  }
</script>

<div class="searchable-select" class:compact={!!compactLabel} data-property-control>
  <!-- Keep native form submission, required validation and browser autofill. -->
  <select
    class="native-select"
    bind:this={nativeSelect}
    {name}
    bind:value
    {required}
    {disabled}
    {autocomplete}
    tabindex="-1"
    aria-hidden="true"
    onfocus={() => trigger?.focus()}
    oninvalid={(event) => {
      event.preventDefault();
      trigger?.focus();
    }}
    onchange={(event) => {
      value = event.currentTarget.value;
      onchange?.(value);
    }}
  >
    {#each choices as option (option.value)}<option value={option.value}>{option.label}</option
      >{/each}
  </select>
  <Popover.Root bind:open onOpenChange={() => (query = '')}>
    <Popover.Trigger asChild class="">
      {#snippet child({ props })}<button
          {...props}
          bind:this={trigger}
          {id}
          type="button"
          {disabled}
          data-select-trigger
          class="v2-input select-trigger"
          role="combobox"
          aria-label={`${label}: ${display}`}
          aria-required={required || undefined}
        >
          <span>{display}</span><ChevronDown size={15} aria-hidden="true" />
        </button>{/snippet}
    </Popover.Trigger>
    <Popover.Content
      portalProps={{ to: trigger?.closest('dialog') || undefined }}
      align="start"
      collisionPadding={8}
      class="form-select-popover"
      aria-label={label}
    >
      <ChoiceList options={choices} {value} {label} {disabled} bind:query onchange={choose} />
    </Popover.Content>
  </Popover.Root>
</div>

<style>
  .searchable-select {
    position: relative;
    width: 100%;
    min-width: 0;
  }
  .native-select {
    position: absolute;
    width: 1px;
    height: 1px;
    opacity: 0;
    pointer-events: none;
  }
  .select-trigger {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    width: 100%;
    min-width: 0;
    text-align: start;
    cursor: pointer;
  }
  .select-trigger span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .select-trigger :global(svg) {
    flex: none;
  }
  .select-trigger[aria-invalid='true'] {
    border-color: var(--crm-primary);
  }
  .compact .select-trigger {
    padding: 0 8px;
    height: 100%;
    min-height: 40px;
    border: 0;
    background: transparent;
    box-shadow: none;
    font-size: 13px;
  }
  :global(.form-select-popover) {
    width: min(20rem, calc(100vw - 2rem));
    max-height: var(--bits-popover-content-available-height);
    overflow: auto;
    padding: 0;
    background: var(--v2-card);
    color: var(--v2-ink);
  }
</style>
