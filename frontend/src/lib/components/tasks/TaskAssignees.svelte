<script>
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();

  import { X, ChevronDown } from '@lucide/svelte';
  let {
    people,
    selected = $bindable([]),
    multiple = true,
    required = false,
    compact = false,
    label = 'Assigned to',
    fieldName = 'assigned_to',
    disabled = false
  } = $props();
  const id = $props.id();
  let query = $state(''),
    open = $state(false),
    active = $state(-1),
    root,
    input = $state();
  $effect(() => {
    input?.setCustomValidity(
      required && !selected.length ? 'Select a user from the suggestions.' : ''
    );
  });
  const matches = $derived(
    people
      .filter(
        (person) =>
          !selected.includes(person.id) &&
          `${person.name} ${person.email ?? ''}`.toLowerCase().includes(query.trim().toLowerCase())
      )
      .slice(0, 20)
  );
  function choose(person) {
    if (disabled) return;
    selected = multiple ? [...selected, person.id] : [person.id];
    query = '';
    active = -1;
    input?.focus();
    open = false;
  }
  function outside(event) {
    if (!root?.contains(event.target)) open = false;
  }
  function keyboard(event) {
    if (event.key === 'Escape' && open) {
      event.preventDefault();
      event.stopPropagation();
      open = false;
      active = -1;
    } else if (['ArrowDown', 'ArrowUp'].includes(event.key)) {
      event.preventDefault();
      open = true;
      active = matches.length
        ? (active + (event.key === 'ArrowDown' ? 1 : -1) + matches.length) % matches.length
        : -1;
    } else if (event.key === 'Enter') {
      event.preventDefault();
      if (open && matches.length && (active >= 0 || matches.length === 1))
        choose(matches[Math.max(0, active)]);
    }
  }
</script>

<svelte:window onpointerdown={outside} onfocusin={outside} />
<div data-stage-field={fieldName} class="assignees" class:compact bind:this={root}>
  <label for={`${id}-input`}>{label}{required ? ' *' : ''}</label>
  <div class="selection-field" class:disabled>
    {#if selected.length}<div class="selected">
        {#each selected as personId (personId)}
          {@const person = people.find((person) => person.id === personId)}
          <span
            >{person?.name ?? 'Assigned user'}<button
              type="button"
              {disabled}
              aria-label={`Remove ${person?.name ?? 'assigned user'}`}
              onclick={() => {
                selected = selected.filter((value) => value !== personId);
                active = -1;
              }}><X size={13} /></button
            ></span
          >
        {/each}
      </div>{/if}
    <div class="search">
      <input
        bind:this={input}
        id={`${id}-input`}
        {disabled}
        placeholder={selected.length
          ? multiple
            ? ui('Add a user…')
            : ui('Change user…')
          : multiple
            ? ui('Select users…')
            : ui('Select user…')}
        bind:value={query}
        autocomplete="off"
        required={required && !selected.length}
        role="combobox"
        aria-autocomplete="list"
        aria-expanded={open}
        aria-controls={`${id}-results`}
        aria-activedescendant={open && active >= 0 && matches[active]
          ? `${id}-option-${matches[active].id}`
          : undefined}
        onfocus={() => {
          if (!disabled) open = true;
        }}
        oninput={() => {
          open = true;
          active = -1;
        }}
        onkeydown={keyboard}
      />
      <button
        class="toggle"
        type="button"
        {disabled}
        tabindex="-1"
        aria-label={`Show ${label.toLowerCase()} options`}
        onclick={() => {
          const next = !open;
          input?.focus();
          open = next;
        }}><ChevronDown size={15} /></button
      >
    </div>
  </div>
  {#if open && !disabled}<div
      class="suggestions"
      id={`${id}-results`}
      role="listbox"
      aria-label={ui('Suggested users')}
    >
      {#each matches as person, index (person.id)}<button
          type="button"
          role="option"
          id={`${id}-option-${person.id}`}
          aria-selected={active === index}
          tabindex="-1"
          onpointerdown={(event) => event.preventDefault()}
          onclick={() => choose(person)}
          >{person.name}{#if person.email && people.filter((p) => p.name === person.name).length > 1}<small
              >{person.email}</small
            >{/if}</button
        >
      {:else}<p role="status">
          {query.trim() ? ui('No matching users.') : ui('No more users available.')}
        </p>{/each}
    </div>{/if}
  {#each selected as personId}<input type="hidden" name={fieldName} value={personId} />{/each}
</div>

<style>
  .assignees {
    position: relative;
    display: grid;
    gap: 7px;
    margin-bottom: 18px;
    font-size: var(--crm-text-sm);
  }
  .assignees.compact {
    margin-bottom: 0;
  }
  label {
    color: var(--v2-slate);
  }
  .selection-field {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
    border: 1px solid var(--v2-line);
    background: var(--v2-card);
    border-radius: var(--crm-radius-md);
    padding: 7px 9px;
    min-height: 42px;
  }
  .selection-field:focus-within {
    outline: 2px solid var(--v2-slate);
    outline-offset: 2px;
  }
  .selection-field.disabled {
    opacity: 0.6;
  }
  .selected {
    display: contents;
  }
  .selected > span {
    display: inline-flex;
    align-items: center;
    gap: var(--crm-space-1);
    max-width: 100%;
    background: var(--v2-hover);
    border-radius: var(--crm-radius-sm);
    padding: 3px 5px 3px var(--crm-space-2);
    font-size: var(--crm-text-xs);
    overflow-wrap: anywhere;
  }
  .selected button {
    background: none;
    border: 0;
    color: var(--v2-slate);
    display: grid;
    place-items: center;
    width: 22px;
    height: 22px;
    cursor: pointer;
  }
  .search {
    display: flex;
    align-items: center;
    gap: 6px;
    flex: 1;
    min-width: 120px;
    color: var(--v2-slate);
  }
  .search input {
    width: 100%;
    min-width: 0;
    background: none;
    border: 0;
    outline: none;
    padding: 3px;
    font: inherit;
    color: var(--v2-ink);
  }
  .search :global(svg) {
    flex-shrink: 0;
  }
  .toggle {
    display: grid;
    place-items: center;
    background: none;
    border: 0;
    padding: 3px;
    color: var(--v2-slate);
    cursor: pointer;
  }
  .suggestions {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    z-index: 30;
    max-height: 220px;
    overflow: auto;
    border: 1px solid var(--v2-line);
    border-radius: var(--crm-radius-md);
    background: var(--v2-card);
    box-shadow: var(--crm-shadow-sm);
    margin-top: var(--crm-space-1);
  }
  .suggestions button {
    display: block;
    width: 100%;
    text-align: left;
    padding: 11px var(--crm-space-3);
    background: none;
    border: 0;
    font: inherit;
    color: var(--v2-ink);
    cursor: pointer;
  }
  .suggestions button:hover,
  .suggestions button[aria-selected='true'] {
    background: var(--v2-hover);
  }
  .suggestions small {
    display: block;
    color: var(--v2-slate);
    font-size: var(--crm-text-xs);
    margin-top: 3px;
  }
  .suggestions p {
    padding: var(--crm-space-3);
    margin: 0;
    color: var(--v2-slate);
  }
</style>
