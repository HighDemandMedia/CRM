<script>
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();

  import { resolve } from '$app/paths';
  import { goto } from '$app/navigation';
  import {
    Search,
    Columns3,
    Building2,
    Users,
    Target,
    LifeBuoy,
    Receipt,
    BookOpen,
    Plus,
    CalendarDays,
    CircleCheck,
    Sun,
    X
  } from '@lucide/svelte';

  /**
   * One search across every record type, opened with ⌘K.
   *
   * v1 had a search box per list, each scoped to that list, so finding a
   * ticket meant knowing it was a ticket first. This asks once.
   *
   * Empty query shows actions rather than an empty box. The fastest way to
   * start a new deal is ⌘K, "new", Enter, and that only works if the actions
   * are there before you type.
   *
   * @type {{ open: boolean, onclose: () => void }}
   */
  let { open = false, onclose } = $props();

  const ACTIONS = [
    {
      kind: 'Create',
      id: 'act-contact',
      title: 'New contact',
      meta: '',
      href: '/contacts/new',
      icon: Users
    },
    {
      kind: 'Create',
      id: 'act-company',
      title: 'New company',
      meta: '',
      href: '/accounts/new',
      icon: Building2
    },
    {
      kind: 'Create',
      id: 'act-deal',
      title: 'New deal',
      meta: '',
      href: '/pipeline/new',
      icon: Columns3
    },
    {
      kind: 'Create',
      id: 'act-task',
      title: 'New task',
      meta: '',
      href: '/tasks/new',
      icon: CircleCheck
    },
    {
      kind: 'Create',
      id: 'act-ticket',
      title: 'New ticket',
      meta: '',
      href: '/tickets/new',
      icon: LifeBuoy
    },
    {
      kind: 'Open',
      id: 'act-calendar',
      title: 'Calendar',
      meta: '',
      href: '/calendar',
      icon: CalendarDays
    },
    { kind: 'Open', id: 'act-today', title: 'Today', meta: '', href: '/', icon: Sun }
  ];

  const ICON = {
    Deals: Columns3,
    Accounts: Building2,
    Contacts: Users,
    Leads: Target,
    Tickets: LifeBuoy,
    Invoices: Receipt,
    'Knowledge base': BookOpen,
    Actions: Plus
  };

  let query = $state('');
  let hits = $state(/** @type {any[]} */ ([]));
  let cursor = $state(0);
  /** @type {HTMLInputElement | undefined} */
  let input = $state();

  let loading = $state(false),
    failure = $state('');
  let rows = $derived(
    query.trim()
      ? [
          ...ACTIONS.filter((action) =>
            `${ui(action.title)} ${ui(action.kind)} ${action.title}`
              .toLowerCase()
              .includes(query.trim().toLowerCase())
          ),
          ...hits
        ]
      : ACTIONS
  );

  /** Grouped for display, but `rows` stays flat so ↑/↓ crosses group borders. */
  let groups = $derived(
    rows.reduce((acc, r) => {
      const g = acc.find((x) => x.kind === r.kind);
      if (g) g.rows.push(r);
      else acc.push({ kind: r.kind, rows: [r] });
      return acc;
    }, /** @type {{kind: string, rows: any[]}[]} */ ([]))
  );

  $effect(() => {
    const q = query.trim();
    hits = [];
    cursor = 0;
    failure = '';
    if (!open || !q) {
      loading = false;
      return;
    }
    const controller = new AbortController();
    loading = true;
    const timer = setTimeout(async () => {
      try {
        const response = await fetch(`/api/search?q=${encodeURIComponent(q)}`, {
          signal: controller.signal
        });
        if (!response.ok) throw new Error();
        const result = await response.json();
        if (!controller.signal.aborted) hits = result.results || [];
      } catch {
        if (!controller.signal.aborted) failure = 'Could not search. Please try again.';
      } finally {
        if (!controller.signal.aborted) loading = false;
      }
    }, 250);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  });

  $effect(() => {
    if (open) input?.focus();
  });

  function onkeydown(e) {
    if (e.key === 'Escape') {
      e.preventDefault();
      onclose();
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      cursor = rows.length ? (cursor + 1) % rows.length : 0;
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      cursor = rows.length ? (cursor - 1 + rows.length) % rows.length : 0;
    } else if (e.key === 'Enter') {
      e.preventDefault();
      choose(rows[cursor]);
    }
  }

  function choose(row) {
    if (!row) return;
    onclose();
    query = '';
    goto(resolve(row.href));
  }
</script>

{#if open}
  <!--
    A backdrop click closes; that is a convenience, not the only way out, so
    the keyboard handler on the dialog carries Escape. Nothing here is
    reachable by mouse alone that is not also reachable by key alone.
  -->
  <div
    class="v2-scrim"
    role="presentation"
    onclick={(e) => {
      if (e.target === e.currentTarget) onclose();
    }}
  >
    <div
      class="v2-palette"
      role="dialog"
      aria-modal="true"
      aria-label={ui('Search')}
      tabindex="-1"
      {onkeydown}
    >
      <div class="v2-palette-input">
        <Search size={17} style="color:var(--v2-slate);flex:none" />
        <input
          bind:this={input}
          bind:value={query}
          type="text"
          placeholder={ui('Search records or actions…')}
          aria-label={ui('Search')}
          aria-autocomplete="list"
          autocomplete="off"
          spellcheck="false"
        />
        <button
          class="palette-close"
          type="button"
          aria-label={ui('Close search')}
          onclick={onclose}><X size={16} /></button
        >
      </div>

      <div class="v2-palette-list" role="listbox" aria-label={ui('Results')}>
        {#each groups as group (group.kind)}
          <div class="v2-palette-group v2-label">
            {ui(group.kind === 'Accounts' ? 'Companies' : group.kind)}
          </div>
          {#each group.rows as row (row.id)}
            {@const i = rows.indexOf(row)}
            {@const Icon = row.icon ?? ICON[row.kind] ?? Search}
            <button
              class="v2-palette-row"
              type="button"
              role="option"
              aria-selected={i === cursor}
              onmouseenter={() => (cursor = i)}
              onclick={() => choose(row)}
            >
              <Icon />
              <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap"
                >{row.id?.startsWith('act-') ? ui(row.title) : row.title}</span
              >
              {#if row.meta}<span class="v2-palette-meta">{row.meta}</span>{/if}
            </button>
          {/each}
        {:else}
          <p class="v2-sub" style="padding:22px 15px;text-align:center;margin:0">
            {loading ? ui('Searching…') : failure || `No results for “${query}”.`}
          </p>
        {/each}
      </div>
    </div>
  </div>
{/if}

<style>
  .palette-close {
    display: grid;
    place-items: center;
    width: 28px;
    height: 28px;
    flex-shrink: 0;
    border: 0;
    border-radius: var(--crm-radius-sm);
    background: transparent;
    color: var(--v2-slate);
    cursor: pointer;
  }
  .palette-close:hover {
    background: var(--v2-paper);
    color: var(--v2-ink);
  }
  .v2-palette-row {
    min-height: 42px;
  }
  .v2-palette-group {
    padding-top: var(--crm-space-3);
  }
</style>
