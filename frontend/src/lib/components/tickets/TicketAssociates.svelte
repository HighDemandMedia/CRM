<script>
  import { X, Search } from '@lucide/svelte';
  let { values = $bindable(), options } = $props();
  const id = $props.id();
  let search = $state(''),
    open = $state(false),
    active = $state(-1),
    root;
  const records = $derived([
    ...(options.contacts ?? []).map((record) => ({ ...record, kind: 'Contact' })),
    ...(options.accounts ?? []).map((record) => ({ ...record, kind: 'Company' })),
    ...(options.deals ?? []).map((record) => ({ ...record, kind: 'Deal' }))
  ]);
  function selected(record) {
    return record.kind === 'Contact'
      ? (values.contacts ?? []).includes(record.id)
      : (record.kind === 'Company' ? values.account : values.deal) === record.id;
  }
  const chosen = $derived([
    ...(values.contacts ?? []).map((id) => ({
      id,
      kind: 'Contact',
      name: records.find((r) => r.kind === 'Contact' && r.id === id)?.name ?? 'Associated contact'
    })),
    ...(values.account
      ? [
          {
            id: values.account,
            kind: 'Company',
            name:
              records.find((r) => r.kind === 'Company' && r.id === values.account)?.name ??
              'Associated company'
          }
        ]
      : []),
    ...(values.deal
      ? [
          {
            id: values.deal,
            kind: 'Deal',
            name:
              records.find((r) => r.kind === 'Deal' && r.id === values.deal)?.name ??
              'Associated deal'
          }
        ]
      : [])
  ]);
  const matches = $derived(
    search.trim()
      ? records
          .filter(
            (record) =>
              !selected(record) &&
              `${record.name} ${record.kind}`.toLowerCase().includes(search.trim().toLowerCase())
          )
          .slice(0, 30)
      : []
  );
  function choose(record) {
    if (record.kind === 'Contact') values.contacts = [...(values.contacts ?? []), record.id];
    else if (record.kind === 'Company') values.account = record.id;
    else values.deal = record.id;
    search = '';
    open = false;
    active = -1;
  }
  function remove(record) {
    if (record.kind === 'Contact')
      values.contacts = values.contacts.filter((id) => id !== record.id);
    else if (record.kind === 'Company') values.account = '';
    else values.deal = '';
  }
  function keyboard(event) {
    if (event.key === 'Escape') {
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
      if (open && active >= 0 && matches[active]) choose(matches[active]);
    }
  }
  function outside(event) {
    if (!root?.contains(event.target)) open = false;
  }
</script>

<svelte:window onpointerdown={outside} onfocusin={outside} />
<div class="associates" bind:this={root}>
  <label for={`${id}-search`}>Associates</label>
  <div class="search">
    <Search size={15} /><input
      id={`${id}-search`}
      class="v2-input"
      placeholder="Search contacts, companies or deals…"
      bind:value={search}
      role="combobox"
      aria-autocomplete="list"
      aria-expanded={open && !!search.trim()}
      aria-controls={`${id}-results`}
      aria-activedescendant={open && active >= 0 ? `${id}-result-${active}` : undefined}
      autocomplete="off"
      oninput={() => {
        open = true;
        active = -1;
      }}
      onfocus={() => (open = true)}
      onkeydown={keyboard}
    />
  </div>
  {#if open && search.trim()}<div
      class="results"
      id={`${id}-results`}
      role="listbox"
      aria-label="Matching associates"
    >
      {#each matches as record, index (`${record.kind}-${record.id}`)}<button
          type="button"
          role="option"
          aria-selected={active === index}
          id={`${id}-result-${index}`}
          class:active={active === index}
          onclick={() => choose(record)}
          ><span>{record.name}</span><small>{record.kind}</small></button
        >{:else}<div class="empty" role="presentation">No matches.</div>{/each}
    </div>{/if}
  <div class="chosen">
    {#each chosen as record (`${record.kind}-${record.id}`)}<div class="chip">
        <div><span>{record.name}</span><small>{record.kind}</small></div>
        <button
          type="button"
          aria-label={`Remove ${record.kind.toLowerCase()} ${record.name}`}
          onclick={() => remove(record)}><X size={14} /></button
        >
      </div>{/each}
  </div>
  <input type="hidden" name="account" value={values.account ?? ''} />
  <input type="hidden" name="deal" value={values.deal ?? ''} />
  {#each values.contacts ?? [] as contact}<input
      type="hidden"
      name="contacts"
      value={contact}
    />{/each}
</div>

<style>
  .associates {
    position: relative;
    min-width: 0;
  }
  label {
    display: block;
    font-size: var(--crm-text-xs);
    color: var(--v2-muted);
    margin-bottom: 6px;
  }
  .search {
    position: relative;
  }
  .search :global(svg) {
    position: absolute;
    left: 10px;
    top: 50%;
    transform: translateY(-50%);
    color: var(--v2-muted);
    pointer-events: none;
  }
  input.v2-input {
    width: 100%;
    min-width: 0;
    padding-left: var(--crm-space-8);
    color: var(--v2-ink);
  }
  .results {
    position: absolute;
    top: 64px;
    left: 0;
    right: 0;
    z-index: 20;
    max-height: 250px;
    overflow: auto;
    background: var(--v2-bg);
    border: 1px solid var(--v2-line);
    border-radius: var(--crm-radius-md);
    box-shadow: var(--crm-shadow-sm);
    padding: 5px;
  }
  .results button {
    width: 100%;
    border: 0;
    background: none;
    display: flex;
    justify-content: space-between;
    align-items: center;
    text-align: left;
    gap: 10px;
    padding: 10px;
    border-radius: var(--crm-radius-sm);
    cursor: pointer;
    color: var(--v2-ink);
    font: inherit;
    font-size: var(--crm-text-sm);
  }
  .results button:hover,
  .results button.active {
    background: var(--v2-paper);
  }
  small {
    font-size: var(--crm-text-xs);
    color: var(--v2-muted);
    font-weight: 400;
  }
  .empty {
    padding: var(--crm-space-3);
    font-size: var(--crm-text-xs);
    color: var(--v2-muted);
  }
  .chosen {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: var(--crm-space-2);
  }
  .chip {
    display: flex;
    align-items: center;
    gap: var(--crm-space-2);
    padding: 7px 9px;
    border: 1px solid var(--v2-line);
    border-radius: var(--crm-radius-md);
    background: var(--v2-paper);
    max-width: 100%;
  }
  .chip div {
    min-width: 0;
  }
  .chip span {
    display: block;
    font-size: var(--crm-text-xs);
    overflow-wrap: anywhere;
  }
  .chip small {
    display: block;
    margin-top: 2px;
  }
  .chip button {
    display: flex;
    border: 0;
    background: none;
    cursor: pointer;
    color: var(--v2-muted);
    padding: 3px;
    flex-shrink: 0;
  }
</style>
