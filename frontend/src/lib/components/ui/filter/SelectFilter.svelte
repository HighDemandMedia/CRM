<script>
  import { tick } from 'svelte';
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();
  import { ChevronDown, Check, X } from '@lucide/svelte';
  import { cn } from '$lib/utils.js';
  import * as Popover from '$lib/components/ui/popover/index.js';

  /**
   * @typedef {{
   *   value: string,
   *   label: string,
   *   icon?: any,
   * }} Option
   */

  /**
   * @type {{
   *   options: Option[],
   *   searchable?: boolean,
   *   name?: string,
   *   value?: string | string[],
   *   multiple?: boolean,
   *   placeholder?: string,
   *   label?: string,
   *   allLabel?: string,
   *   class?: string,
   *   onchange?: (value: string | string[]) => void,
   * }}
   */
  let {
    options = [],
    searchable = false,
    name = '',
    value = $bindable(''),
    multiple = false,
    placeholder = 'Select...',
    label: _label = '',
    allLabel = 'All',
    class: className,
    onchange
  } = $props();

  let open = $state(false);
  let query = $state('');
  let nativeValue = $state();
  const filtered = $derived(
    options.filter((option) => option.label.toLowerCase().includes(query.trim().toLowerCase()))
  );
  async function chooseSearchValue(next) {
    value = next;
    open = false;
    query = '';
    onchange?.(next);
    await tick();
    if (name) nativeValue?.dispatchEvent(new Event('input', { bubbles: true }));
  }

  const selectedValues = $derived(
    multiple ? (Array.isArray(value) ? value : value ? [value] : []) : []
  );

  const displayText = $derived.by(() => {
    if (multiple) {
      if (selectedValues.length === 0) return placeholder;
      if (selectedValues.length === 1) {
        const opt = options.find((o) => o.value === selectedValues[0]);
        return opt?.label || selectedValues[0];
      }
      return `${selectedValues.length} selected`;
    } else {
      if (!value || value === 'ALL') return allLabel;
      const opt = options.find((o) => o.value === value);
      return opt?.label || value;
    }
  });

  /**
   * @param {string} optValue
   */
  function handleSelect(optValue) {
    if (multiple) {
      const newValues = selectedValues.includes(optValue)
        ? selectedValues.filter((v) => v !== optValue)
        : [...selectedValues, optValue];
      value = newValues;
      onchange?.(newValues);
    } else {
      value = optValue;
      onchange?.(optValue);
      open = false;
    }
  }

  function handleClear() {
    if (multiple) {
      value = [];
      onchange?.([]);
    } else {
      value = 'ALL';
      onchange?.('ALL');
    }
  }

  const hasValue = $derived(multiple ? selectedValues.length > 0 : value && value !== 'ALL');
</script>

{#if searchable}
  {#if name}<input
      type="hidden"
      {name}
      value={value === 'ALL' ? '' : value}
      bind:this={nativeValue}
    />{/if}
  <Popover.Root bind:open>
    <Popover.Trigger asChild class="">
      {#snippet child({ props })}<button
          {...props}
          type="button"
          class="v2-btn searchable-filter"
          aria-label={_label || placeholder}
          ><span>{displayText}</span><ChevronDown size={16} /></button
        >{/snippet}
    </Popover.Trigger>
    <Popover.Content
      align="start"
      collisionPadding={8}
      class="filter-select-popover"
      aria-label={_label || placeholder}
    >
      <input
        class="v2-input"
        type="search"
        aria-label={ui('Search options')}
        placeholder={ui('Search…')}
        bind:value={query}
        oninput={(event) => event.stopPropagation()}
        onkeydown={(event) => {
          if (event.key === 'Enter') event.preventDefault();
        }}
      />
      <div class="search-options">
        <button
          type="button"
          aria-pressed={!value || value === 'ALL'}
          onclick={() => chooseSearchValue('')}>{allLabel}</button
        >
        {#each filtered as option (option.value)}<button
            type="button"
            aria-pressed={value === option.value}
            onclick={() => chooseSearchValue(option.value)}
            >{option.label}{#if value === option.value}<Check size={15} />{/if}</button
          >{:else}<p>{ui('No results found.')}</p>{/each}
      </div>
    </Popover.Content>
  </Popover.Root>
{:else}
  <Popover.Root bind:open>
    <Popover.Trigger asChild class="">
      {#snippet child({ props })}
        <button
          type="button"
          {...props}
          class={cn(
            'inline-flex h-7 items-center gap-1.5 rounded-[var(--r-sm)] border px-2.5 text-[13px] leading-none font-medium transition-colors focus:ring-1 focus:ring-[color:var(--ring)] focus:outline-none',
            hasValue
              ? 'border-[color:var(--violet)]/40 bg-[color:var(--violet-soft)] text-[color:var(--violet-soft-text)]'
              : 'border-[color:var(--border-faint)] bg-[color:var(--bg-elevated)] text-[color:var(--text-muted)] hover:bg-[color:var(--bg-hover)]',
            className
          )}
        >
          <span class="truncate">{displayText}</span>
          {#if hasValue}
            <span
              role="button"
              tabindex="0"
              onclick={(e) => {
                e.stopPropagation();
                e.preventDefault();
                handleClear();
              }}
              onkeydown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.stopPropagation();
                  e.preventDefault();
                  handleClear();
                }
              }}
              class="-mr-1 ml-0.5 flex size-3.5 shrink-0 items-center justify-center rounded-sm hover:bg-[color:var(--violet)]/15"
              aria-label="Clear filter"
            >
              <X class="size-3" />
            </span>
          {:else}
            <ChevronDown class="size-3.5 shrink-0 opacity-60" />
          {/if}
        </button>
      {/snippet}
    </Popover.Trigger>

    <Popover.Content
      align="start"
      sideOffset={4}
      class="w-[220px] overflow-hidden rounded-[var(--r-md)] border border-[color:var(--border)] bg-[color:var(--bg-card)] p-1 shadow-lg shadow-black/5"
    >
      <!-- All option -->
      {#if !multiple}
        <button
          type="button"
          class={cn(
            'select-option group',
            'relative flex w-full cursor-pointer items-center gap-2.5',
            'rounded-lg px-2.5 py-2 text-sm',
            'transition-all duration-150',
            'outline-none',
            !value || value === 'ALL'
              ? 'bg-primary/10 text-primary dark:bg-primary/20'
              : 'text-foreground/80 hover:bg-muted/80 hover:text-foreground'
          )}
          onclick={() => handleSelect('ALL')}
        >
          <div
            class={cn(
              'flex h-4 w-4 items-center justify-center rounded-full',
              'border transition-all duration-150',
              !value || value === 'ALL'
                ? 'border-primary bg-primary text-primary-foreground scale-100'
                : 'border-border group-hover:border-primary/50 scale-90 bg-transparent group-hover:scale-100'
            )}
          >
            {#if !value || value === 'ALL'}
              <Check class="h-2.5 w-2.5" />
            {/if}
          </div>
          <span class="font-medium">{allLabel}</span>
        </button>
        <div class="bg-border/50 my-1 h-px dark:bg-white/[0.06]"></div>
      {/if}

      <!-- Options -->
      <div class="max-h-[240px] overflow-y-auto">
        {#each options as option, i (option.value)}
          {@const isSelected = multiple
            ? selectedValues.includes(option.value)
            : value === option.value}
          <button
            type="button"
            class={cn(
              'select-option group',
              'relative flex w-full cursor-pointer items-center gap-2.5',
              'rounded-lg px-2.5 py-2 text-sm',
              'transition-all duration-150',
              'outline-none',
              isSelected
                ? 'bg-primary/10 text-primary dark:bg-primary/20'
                : 'text-foreground/80 hover:bg-muted/80 hover:text-foreground',
              'animate-in fade-in-0 slide-in-from-left-1'
            )}
            style="animation-delay: {i * 20}ms"
            onclick={() => handleSelect(option.value)}
          >
            <div
              class={cn(
                'flex h-4 w-4 shrink-0 items-center justify-center rounded-full',
                'border transition-all duration-150',
                isSelected
                  ? 'border-primary bg-primary text-primary-foreground scale-100'
                  : 'border-border/60 group-hover:border-primary/50 scale-90 bg-transparent group-hover:scale-100'
              )}
            >
              {#if isSelected}
                <Check class="h-2.5 w-2.5" />
              {/if}
            </div>
            <span class={cn('truncate', isSelected && 'font-medium')}>
              {option.label}
            </span>
          </button>
        {/each}
      </div>
    </Popover.Content>
  </Popover.Root>
{/if}

<style>
  .searchable-filter {
    width: 100%;
    justify-content: space-between;
    gap: var(--crm-space-4);
    min-width: 0;
  }
  .searchable-filter span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  :global(.filter-select-popover) {
    width: min(18rem, calc(100vw - 2rem));
    max-height: var(--bits-popover-content-available-height);
    overflow: auto;
    padding: var(--crm-space-2);
    background: var(--crm-surface);
    color: var(--crm-text);
  }
  .search-options {
    max-height: min(16rem, 40dvh);
    overflow-y: auto;
    margin-top: var(--crm-space-2);
  }
  .search-options button {
    display: flex;
    align-items: center;
    justify-content: space-between;
    text-align: left;
    width: 100%;
    min-height: var(--crm-target-size);
    padding: var(--crm-space-2);
    border: 0;
    border-radius: var(--crm-radius-sm);
    background: transparent;
    color: inherit;
    font-size: var(--crm-text-sm);
    overflow-wrap: anywhere;
  }
  .search-options button:hover,
  .search-options button[aria-pressed='true'] {
    background: var(--crm-surface-selected);
  }
  .search-options button:focus-visible {
    outline: 2px solid var(--crm-focus);
    outline-offset: -2px;
  }
  .search-options p {
    font-size: var(--crm-text-sm);
    padding: var(--crm-space-2);
  }
</style>
