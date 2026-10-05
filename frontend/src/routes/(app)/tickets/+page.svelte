<script>
  import { can } from '$lib/v2/permissions.js';
  import { showStageRequirements } from '$lib/components/pipelines/feedback.js';
  import { configuredStages, configuredLabel } from '$lib/v2/pipeline-config.js';
  import '$lib/v2/styles/pipeline.css';
  import '$lib/v2/styles/list-view.css';
  import { pipelineTone } from '$lib/v2/pipeline-view.js';
  import { onMount } from 'svelte';
  import { page } from '$app/state';
  import { goto, invalidateAll } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { deserialize } from '$app/forms';
  import { List, Columns3, Plus, Download } from '@lucide/svelte';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import { listColumns, columnValue } from '$lib/v2/list-columns.js';
  import { columnSelection } from '$lib/v2/column-selection.svelte.js';
  import ColumnPicker from '$lib/v2/components/ColumnPicker.svelte';
  import AdvancedQueue from '$lib/components/tickets/AdvancedQueue.svelte';
  import {
    statuses as defaultStatuses,
    priorities,
    categories,
    dueDateLabel,
    statusLabel,
    priorityLabel
  } from '$lib/components/tickets/options.js';
  const statuses = $derived(
    configuredStages(
      page.data.pipelineConfig,
      'Case',
      defaultStatuses.map(([value, label]) => ({ value, label }))
    ).map((s) => [s.value, s.label])
  );
  let { data, form } = $props();
  let advanced = $state(false),
    search = $state(''),
    timer,
    dragging = $state(''),
    target = $state(''),
    error = $state(''),
    moving = $state(false),
    resolving = $state(null),
    resolution = $state('');
  const legacyFields = [
    ['ticket_code', 'ID'],
    ['name', 'Title'],
    ['status', 'Status'],
    ['priority', 'Priority'],
    ['assignee', 'Assigned to'],
    ['association', 'Associated with'],
    ['category', 'Category'],
    ['source', 'Source'],
    ['due_at', 'Due date'],
    ['last_activity', 'Last activity']
  ];
  const catalog = $derived(listColumns('Case', page.data.propertyLayout?.Case, legacyFields));
  const fields = $derived(catalog.map((c) => [c.key, c.label]));
  const selection = columnSelection(
    () => catalog,
    () => `${page.data.accountId}.${page.data.accountUser?.email}.Case`
  );
  const columns = $derived(selection.selected);
  const view = $derived(page.url.searchParams.get('view') ?? 'list');
  const offset = $derived(Number(page.url.searchParams.get('offset') ?? 0));
  let sort = $state(''),
    asc = $state(true);
  const date = (value) =>
    value
      ? new Date(value).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
      : '—';
  function value(t, key) {
    if (key === 'status')
      return configuredLabel(page.data.pipelineConfig, 'Case', t.status, statusLabel(t.status));
    if (key === 'priority') return priorityLabel(t.priority);
    if (key === 'association')
      return [t.account?.name, ...t.contacts.map((c) => c.name)].filter(Boolean).join(', ');
    if (key === 'due_at') return dueDateLabel(t[key]);
    if (key === 'last_activity') return date(t[key]);
    return columnValue(t, key, catalog);
  }
  const rows = $derived(
    [...data.tickets].sort((a, b) =>
      sort
        ? String(value(a, sort)).localeCompare(String(value(b, sort)), undefined, {
            numeric: true
          }) * (asc ? 1 : -1)
        : 0
    )
  );
  const stages = $derived(statuses);
  onMount(() => {
    search = data.search;
    return () => clearTimeout(timer);
  });
  function toggle(key) {
    selection.toggle(key);
  }
  function filter(key, value) {
    const url = new URL(page.url);
    if (value) url.searchParams.set(key, value);
    else url.searchParams.delete(key);
    if (key !== 'offset') url.searchParams.delete('offset');
    goto(url, { keepFocus: true, noScroll: true });
  }
  async function move(id, status) {
    if (moving) return;
    if (status === 'Resolved' && !resolving) {
      resolving = id;
      return;
    }
    moving = true;
    error = '';
    const body = new FormData();
    body.set('id', id);
    body.set('status', status);
    if (status === 'Resolved') body.set('resolution_note', resolution);
    try {
      const result = deserialize(await (await fetch('?/move', { method: 'POST', body })).text());
      if (result.type !== 'success') {
        if (
          showStageRequirements(result, 'Case', id, {
            status,
            ...(status === 'Closed' ? { closed_on: new Date().toISOString().slice(0, 10) } : {}),
            ...(status === 'Resolved' ? { resolution_note: resolution } : {})
          })
        ) {
          resolving = null;
          return;
        }
        error =
          result.type === 'failure'
            ? String(result.data?.error ?? 'Could not move ticket.')
            : 'Could not move ticket.';
      } else {
        resolving = null;
        resolution = '';
        await invalidateAll();
      }
    } catch {
      error = 'Could not move ticket. Try again.';
    } finally {
      moving = false;
      dragging = '';
      target = '';
    }
  }
  function drop(e, status) {
    e.preventDefault();
    const id = e.dataTransfer?.getData('text/plain');
    if (id && rows.some((t) => t.id === id && t.status !== status)) move(id, status);
    target = '';
  }
  function modal(node) {
    node.showModal();
    return {
      destroy() {
        node.close();
      }
    };
  }
  async function exportCSV() {
    const response = await fetch(resolve('/tickets/export-check'));
    if (!response.ok) {
      error = 'Your permission set does not allow exporting tickets.';
      return;
    }
    const safe = (v) => {
      let s = String(v ?? '');
      if (/^[=+@\-\t\r]/.test(s)) s = "'" + s;
      return '"' + s.replaceAll('"', '""') + '"';
    };
    const text = [
      columns.map((k) => fields.find(([id]) => id === k)?.[1]),
      ...rows.map((t) => columns.map((k) => value(t, k)))
    ]
      .map((row) => row.map(safe).join(','))
      .join('\r\n');
    const url = URL.createObjectURL(
      new Blob(['\ufeff' + text], { type: 'text/csv;charset=utf-8;' })
    );
    const a = document.createElement('a');
    a.href = url;
    a.download = 'tickets.csv';
    a.click();
    URL.revokeObjectURL(url);
  }
</script>

{#if advanced}<button class="v2-btn" onclick={() => (advanced = false)}>Back to tickets</button
  ><AdvancedQueue {data} />{:else}
  <PageHeader title="Tickets"
    >{#snippet sub()}{data.totals.count}
      {data.totals.count === 1
        ? 'ticket'
        : 'tickets'}{/snippet}{#snippet actions()}{#if can(page.data.permissions, 'tickets', 'export')}<button
          class="v2-btn"
          onclick={exportCSV}><Download size={14} />Export CSV</button
        >{/if}{#if can(page.data.permissions, 'tickets', 'create')}<a
          class="v2-btn v2-btn-primary"
          href={resolve('/tickets/new')}><Plus size={14} />New ticket</a
        >{/if}{/snippet}</PageHeader
  >
  <div class="workspace">
    <div class="filters">
      <input
        class="v2-input search"
        aria-label="Search tickets"
        placeholder="Search tickets…"
        bind:value={search}
        oninput={() => {
          clearTimeout(timer);
          timer = setTimeout(() => filter('search', search), 300);
        }}
      />
      <select
        class="v2-input"
        aria-label="Assigned to"
        value={page.url.searchParams.get('assigned_to') ?? ''}
        onchange={(e) => filter('assigned_to', e.currentTarget.value)}
        ><option value="">Assigned to</option>{#each data.people as person}<option value={person.id}
            >{person.name}</option
          >{/each}</select
      >
      <select
        class="v2-input"
        aria-label="Status"
        value={data.status}
        onchange={(e) => filter('status', e.currentTarget.value)}
        ><option value="">All statuses</option>{#each statuses as [value, label]}<option {value}
            >{label}</option
          >{/each}</select
      >
      <select
        class="v2-input"
        aria-label="Priority"
        value={page.url.searchParams.get('priority') ?? ''}
        onchange={(e) => filter('priority', e.currentTarget.value)}
        ><option value="">Priority</option>{#each priorities as [value, label]}<option {value}
            >{label}</option
          >{/each}</select
      >
      <select
        class="v2-input"
        aria-label="Category"
        value={page.url.searchParams.get('category') ?? ''}
        onchange={(e) => filter('category', e.currentTarget.value)}
        ><option value="">Category</option>{#each categories as value}<option>{value}</option
          >{/each}</select
      >
      <label class="overdue-filter"
        ><input
          type="checkbox"
          checked={page.url.searchParams.get('overdue') === 'true'}
          onchange={(e) => filter('overdue', e.currentTarget.checked ? 'true' : '')}
        />Overdue</label
      >
      <div class="views">
        <button
          class="v2-btn"
          aria-label="List view"
          aria-pressed={view === 'list'}
          onclick={() => filter('view', 'list')}><List size={16} /></button
        ><button
          class="v2-btn"
          aria-label="Pipeline view"
          aria-pressed={view === 'pipeline'}
          onclick={() => filter('view', 'pipeline')}><Columns3 size={16} /></button
        >{#if view === 'list'}<ColumnPicker
            {fields}
            selected={columns}
            onToggle={toggle}
            onShowAll={selection.showAll}
            onReset={selection.reset}
          />{/if}
      </div>
    </div>
    {#if error}<p class="v2-error" role="alert">{error}</p>{/if}
    {#if view === 'pipeline'}<div class="pipeline hdm-board" aria-label="Tickets by status">
        {#each stages as [status, label]}<section
            class="pipeline-column"
            data-tone={pipelineTone(label)}
            class:target={target === status}
            ondragover={(e) => {
              if (!dragging || moving) return;
              e.preventDefault();
              target = status;
            }}
            ondrop={(e) => drop(e, status)}
            ondragleave={(e) => {
              if (!e.currentTarget.contains(/** @type {Node | null} */ (e.relatedTarget)))
                target = '';
            }}
            aria-label={label}
          >
            <header class="pipeline-header">
              <h2>{label}</h2>
              <span>{rows.filter((t) => t.status === status).length}</span>
            </header>
            <div class="pipeline-cards">
              {#each rows.filter((t) => t.status === status) as ticket}<article
                  class="pipeline-card"
                  draggable={!moving && can(page.data.permissions, 'tickets', 'stage')}
                  ondragstart={(e) => {
                    dragging = ticket.id;
                    e.dataTransfer?.setData('text/plain', ticket.id);
                  }}
                  ondragend={() => {
                    dragging = '';
                    target = '';
                  }}
                  role="group"
                  aria-label={ticket.name}
                  class:dragging={dragging === ticket.id}
                >
                  <div class="ticket-meta">
                    <small>{ticket.ticket_code}</small><span
                      class="priority-badge"
                      data-priority={ticket.priority}>{priorityLabel(ticket.priority)}</span
                    >
                  </div>
                  <a class="pipeline-name" draggable="false" href={resolve(`/tickets/${ticket.id}`)}
                    >{ticket.name || `Ticket · ${ticket.id.slice(0, 8)}`}</a
                  >
                  <p>{ticket.assignee ?? 'Unassigned'}</p>
                  <p>{ticket.category}</p>
                  {#if ticket.due_at}<p
                      class:overdue={ticket.is_open && new Date(ticket.due_at) < new Date()}
                    >
                      {dueDateLabel(ticket.due_at)}
                    </p>{/if}<select
                    class="ticket-stage-control"
                    aria-label={`Move ${ticket.name}`}
                    value={ticket.status}
                    disabled={moving}
                    onchange={(e) => move(ticket.id, e.currentTarget.value)}
                    >{#each stages as [value, label]}<option {value}>{label}</option>{/each}</select
                  >
                </article>{:else}<p class="pipeline-empty">No tickets</p>{/each}
            </div>
          </section>{/each}
      </div>
    {:else}<!-- svelte-ignore a11y_no_noninteractive_tabindex (Keyboard users need to focus this overflow region to scroll the table.) -->
      <div
        class="table-scroll hdm-list"
        role="region"
        aria-label="Tickets; scroll horizontally to see all columns"
        tabindex="0"
      >
        <table>
          <thead
            ><tr
              >{#each columns as key}<th
                  scope="col"
                  data-field={key}
                  aria-sort={sort === key ? (asc ? 'ascending' : 'descending') : 'none'}
                  ><button
                    onclick={() => {
                      if (sort === key) asc = !asc;
                      else {
                        sort = key;
                        asc = true;
                      }
                    }}
                    >{fields.find(([id]) => id === key)?.[1]}{sort === key
                      ? asc
                        ? ' ↑'
                        : ' ↓'
                      : ''}</button
                  ></th
                >{/each}<th scope="col">Actions</th></tr
            ></thead
          ><tbody
            >{#each rows as ticket}<tr
                >{#each columns as key}<td
                    data-field={key}
                    title={String(value(ticket, key))}
                    class:overdue={key === 'due_at' &&
                      ticket.is_open &&
                      ticket.due_at &&
                      new Date(ticket.due_at) < new Date()}
                    >{#if key === 'name' || key === 'ticket_code'}<a
                        href={resolve(`/tickets/${ticket.id}`)}
                        >{value(ticket, key) ||
                          ticket.ticket_code ||
                          `Ticket · ${ticket.id.slice(0, 8)}`}</a
                      >{:else if key === 'status'}<span
                        class="status list-badge"
                        data-tone={pipelineTone(ticket.status)}>{value(ticket, key)}</span
                      >{:else if key === 'priority'}<span
                        class="list-badge"
                        data-priority={ticket.priority}>{value(ticket, key)}</span
                      >{:else}{value(ticket, key)}{/if}</td
                  >{/each}<td class="list-row-actions"
                  >{#if can(page.data.permissions, 'tickets', 'edit')}<a
                      aria-label={`Edit ${ticket.name}`}
                      href={resolve(`/tickets/${ticket.id}/edit`)}>Edit</a
                    >{/if}</td
                ></tr
              >{:else}<tr><td colspan={columns.length + 1}>No tickets found.</td></tr>{/each}</tbody
          >
        </table>
      </div>{/if}
    {#if offset > 0 || offset + rows.length < data.totals.count}<div class="pages">
        <button
          class="v2-btn"
          disabled={offset === 0}
          onclick={() => filter('offset', String(Math.max(0, offset - 100)))}>Previous</button
        ><button
          class="v2-btn"
          disabled={offset + rows.length >= data.totals.count}
          onclick={() => filter('offset', String(offset + rows.length))}>Next</button
        >
      </div>{/if}
  </div>
  {#if resolving}<dialog
      use:modal
      onclose={() => (resolving = null)}
      aria-labelledby="resolve-title"
    >
      <h2 id="resolve-title">Resolve ticket</h2>
      <label
        >Resolution note<textarea class="v2-input" rows="4" bind:value={resolution}
        ></textarea></label
      >{#if error}<p class="v2-error" role="alert">{error}</p>{/if}
      <div class="pages">
        <button class="v2-btn" onclick={() => (resolving = null)}>Cancel</button><button
          class="v2-btn v2-btn-primary"
          disabled={moving || !resolution.trim()}
          onclick={() => move(resolving, 'Resolved')}>Resolve</button
        >
      </div>
    </dialog>{/if}
{/if}

<style>
  .workspace {
    padding: var(--crm-space-4) var(--crm-space-6);
    min-height: 0;
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: var(--crm-space-4);
  }
  .filters {
    display: flex;
    align-items: center;
    gap: var(--crm-space-2);
    flex-wrap: wrap;
  }
  .filters select {
    max-width: 180px;
  }
  .search {
    min-width: 180px;
    flex: 1;
  }
  .views {
    display: flex;
    gap: var(--crm-space-1);
    margin-left: auto;
  }
  .overdue-filter {
    font-size: var(--crm-text-xs);
    display: flex;
    gap: 5px;
    align-items: center;
  }
  .table-scroll {
    overflow: auto;
    flex: 1;
    border-radius: var(--crm-radius-md);
    background: var(--v2-bg);
  }
  table {
    border-collapse: collapse;
    min-width: 100%;
    width: max-content;
  }
  th,
  td {
    padding: 14px var(--crm-space-4);
    text-align: left;
    border-bottom: 1px solid var(--v2-line);
    white-space: nowrap;
    font-size: var(--crm-text-sm);
  }
  th {
    position: sticky;
    top: 0;
    background: var(--v2-bg);
  }
  th button {
    border: 0;
    background: none;
    color: var(--v2-muted);
    font: inherit;
    cursor: pointer;
  }
  a {
    color: inherit;
    text-decoration: none;
    font-weight: 600;
  }
  a.v2-btn-primary {
    color: var(--crm-primary-text);
  }
  a:hover {
    text-decoration: underline;
  }
  .status {
    padding: var(--crm-space-1) var(--crm-space-2);
    background: var(--v2-paper);
    border-radius: var(--crm-radius-sm);
  }
  .pipeline {
    display: flex;
    gap: var(--crm-space-3);
    overflow: auto;
    flex: 1;
  }
  .pipeline > section {
    flex: 0 0 260px;
    background: var(--v2-paper);
    border: 2px solid transparent;
    border-radius: var(--crm-radius-md);
    padding: var(--crm-space-3);
    overflow: auto;
  }
  .pipeline .target {
    border-color: var(--crm-info);
  }
  h2 {
    font-size: var(--crm-text-sm);
    margin: 0 0 var(--crm-space-4);
    display: flex;
    justify-content: space-between;
  }
  small {
    color: var(--v2-muted);
  }
  article {
    background: var(--v2-bg);
    border-radius: var(--crm-radius-md);
    padding: 14px;
    margin: 10px 0;
    cursor: grab;
  }
  .dragging {
    opacity: 0.5;
  }
  article a,
  article small {
    display: block;
  }
  article small {
    font-size: var(--crm-text-xs);
    margin-bottom: 7px;
  }
  article a {
    font-size: var(--crm-text-sm);
  }
  article p {
    font-size: var(--crm-text-xs);
    margin: var(--crm-space-2) 0;
    color: var(--v2-muted);
  }
  article select {
    width: 100%;
    border: 0;
    background: var(--v2-paper);
    font-size: var(--crm-text-xs);
    padding: 6px;
    border-radius: var(--crm-radius-sm);
  }
  .overdue,
  article p.overdue {
    color: var(--v2-rust);
  }
  .pages {
    display: flex;
    justify-content: flex-end;
    gap: var(--crm-space-2);
  }
  dialog::backdrop {
    background: var(--crm-overlay);
  }
  dialog {
    border: 0;
    background: var(--v2-bg);
    padding: var(--crm-space-6);
    width: min(440px, 100%);
    border-radius: var(--crm-radius-lg);
  }
  dialog textarea {
    width: 100%;
    margin: 10px 0;
  }
  @media (max-width: 700px) {
    .workspace {
      padding: var(--crm-space-3);
    }
    .search {
      flex-basis: 100%;
    }
  }
</style>
