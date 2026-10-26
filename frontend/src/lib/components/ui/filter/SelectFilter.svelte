<script>
  import { tick } from 'svelte';
  import { ChevronDown } from '@lucide/svelte';
  import { useI18n } from '$lib/i18n/context.js';
  import * as Popover from '$lib/components/ui/popover/index.js';
  import ChoiceList from '$lib/v2/components/ChoiceList.svelte';
  const { ui } = useI18n();
  /** @type {{options?:any[],searchable?:boolean,name?:string,value?:string|string[],multiple?:boolean,placeholder?:string,label?:string,allLabel?:string,class?:string,onchange?:(value:any)=>void}} */
  let {
    options = [],
    name = '',
    value = $bindable(''),
    multiple = false,
    placeholder = 'Select…',
    label = '',
    allLabel = 'All',
    class: className = '',
    onchange
  } = $props();
  let open = $state(false),
    query = $state(''),
    nativeValue = $state();
  const choices = $derived(options.map((option) => ({ ...option, value: String(option.value) })));
  const selected = $derived(Array.isArray(value) ? value : []);
  const displayText = $derived(
    multiple
      ? selected.length
        ? selected
            .map((key) => choices.find((option) => option.value === key)?.label || key)
            .join(', ')
        : ui(placeholder)
      : !value || value === 'ALL'
        ? allLabel
        : choices.find((option) => option.value === String(value))?.label || value
  );
  async function choose(next) {
    value = next;
    onchange?.(next);
    if (!multiple) open = false;
    await tick();
    nativeValue?.dispatchEvent(new Event('input', { bubbles: true }));
  }
</script>

{#if name}<input
    type="hidden"
    {name}
    value={Array.isArray(value) ? value.join(',') : value === 'ALL' ? '' : value}
    bind:this={nativeValue}
  />{/if}
<Popover.Root bind:open onOpenChange={() => (query = '')}>
  <Popover.Trigger asChild class="">
    {#snippet child({ props })}<button
        {...props}
        type="button"
        class={`v2-btn searchable-filter ${className}`}
        aria-label={label || placeholder}
        ><span>{displayText}</span><ChevronDown size={16} /></button
      >{/snippet}
  </Popover.Trigger>
  <Popover.Content
    align="start"
    collisionPadding={8}
    class="filter-select-popover"
    aria-label={label || placeholder}
  >
    <ChoiceList
      options={multiple ? choices : [{ value: '', label: allLabel }, ...choices]}
      value={value === 'ALL' ? '' : value}
      {multiple}
      label={label || placeholder}
      bind:query
      onchange={choose}
    />
  </Popover.Content>
</Popover.Root>

<style>
  .searchable-filter {
    width: 100%;
    justify-content: space-between;
    gap: 12px;
    min-width: 0;
  }
  .searchable-filter span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .searchable-filter :global(svg) {
    flex: none;
  }
  :global(.filter-select-popover) {
    width: min(18rem, calc(100vw - 2rem));
    max-height: var(--bits-popover-content-available-height);
    overflow: auto;
    padding: 0;
    background: var(--crm-surface);
    color: var(--crm-text);
  }
</style>
