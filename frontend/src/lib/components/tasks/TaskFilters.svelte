<script>
  import '$lib/v2/styles/module-layout.css';
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();

  import { List, Columns3 } from '@lucide/svelte';
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { onDestroy } from 'svelte';
  let { url, people, columnTools } = $props();
  let timer;
  onDestroy(() => clearTimeout(timer));
  function apply(form) {
    clearTimeout(timer);
    const params = new URLSearchParams();
    for (const [key, value] of new FormData(form))
      if (String(value).trim()) params.set(key, String(value).trim());
    if (!params.has('all')) params.set('all', '0');
    void goto(`${resolve('/tasks')}?${params}`, {
      keepFocus: true,
      noScroll: true,
      replaceState: true
    });
  }
  function viewHref(view) {
    const params = new URLSearchParams(url.searchParams);
    params.set('view', view);
    params.delete('offset');
    return `${resolve('/tasks')}?${params}`;
  }
</script>

<div class="task-toolbar object-toolbar">
  <form
    class="task-filters"
    method="GET"
    onsubmit={(e) => {
      e.preventDefault();
      apply(e.currentTarget);
    }}
    oninput={(e) => {
      const form = e.currentTarget;
      clearTimeout(timer);
      timer = setTimeout(() => apply(form), 300);
    }}
  >
    <input type="hidden" name="page_size" value={url.searchParams.get('page_size') ?? '25'} />
    <input type="hidden" name="view" value={url.searchParams.get('view') ?? 'list'} />
    <label class="crm-module-field search-field"
      >{ui('Search')}<input
        type="search"
        class="v2-input search"
        name="q"
        aria-label={ui('Search tasks')}
        placeholder={ui('Search tasks…')}
        value={url.searchParams.get('q') ?? ''}
      /></label
    >
    <label class="crm-module-field"
      >{ui('Owner')}
      <select
        class="v2-input"
        name="assigned_to"
        aria-label={ui('Owner')}
        value={url.searchParams.get('assigned_to') ?? ''}
        ><option value="">{ui('All owners')}</option>{#each people as person}<option
            value={person.id}>{person.name}</option
          >{/each}</select
      ></label
    >
    <label class="crm-module-field"
      >{ui('Status')}
      <select
        class="v2-input"
        name="status"
        aria-label={ui('Status')}
        value={url.searchParams.get('status') ?? ''}
        ><option value="">{ui('All statuses')}</option
        >{#each ['New', 'In Progress', 'Completed'] as status}<option>{status}</option
          >{/each}</select
      ></label
    >
    <label class="crm-module-field"
      >{ui('Priority')}
      <select
        class="v2-input"
        name="priority"
        aria-label={ui('Priority')}
        value={url.searchParams.get('priority') ?? ''}
        ><option value="">{ui('All priorities')}</option
        >{#each ['Low', 'Medium', 'High'] as priority}<option>{priority}</option>{/each}</select
      ></label
    >
    <details>
      <summary class="v2-btn">{ui('Filters')}</summary>
      <div class="extra">
        <label
          >{ui('Due from')}<input
            class="v2-input"
            type="date"
            name="due_date__gte"
            value={url.searchParams.get('due_date__gte') ?? ''}
          /></label
        >
        <label
          >{ui('Due through')}<input
            class="v2-input"
            type="date"
            name="due_date__lte"
            value={url.searchParams.get('due_date__lte') ?? ''}
          /></label
        >
      </div>
    </details>
    <label class="completed"
      ><input
        type="checkbox"
        name="all"
        value="1"
        checked={url.searchParams.get('all') !== '0'}
      />{ui('Show completed')}</label
    >
  </form>
  <div class="crm-module-actions">
    <nav class="views crm-view-switch" aria-label={ui('Task view')}>
      <a
        class="v2-btn v2-btn-icon"
        class:v2-btn-primary={url.searchParams.get('view') !== 'pipeline'}
        href={viewHref('list')}
        aria-label={ui('List view')}
        title={ui('List')}
        aria-current={url.searchParams.get('view') !== 'pipeline' ? 'page' : undefined}
        ><List size={17} /></a
      ><a
        class="v2-btn v2-btn-icon"
        class:v2-btn-primary={url.searchParams.get('view') === 'pipeline'}
        href={viewHref('pipeline')}
        aria-label={ui('Pipeline view')}
        title={ui('Pipeline')}
        aria-current={url.searchParams.get('view') === 'pipeline' ? 'page' : undefined}
        ><Columns3 size={17} /></a
      >
    </nav>
    {#if columnTools}{@render columnTools()}{/if}
  </div>
</div>

<style>
  .task-filters {
    display: flex;
    align-items: end;
    flex-wrap: wrap;
    gap: var(--crm-space-2);
    min-width: 0;
  }
  .crm-module-field {
    flex: 1 1 8rem;
  }
  .search-field {
    flex-basis: 12rem;
  }
  .v2-input {
    width: 100%;
    min-width: 0;
  }
  .task-toolbar {
    align-items: end;
  }
  .completed {
    font-size: var(--crm-text-xs);
    display: flex;
    align-items: center;
    gap: var(--crm-space-2);
    min-height: var(--crm-control-height, 2.5rem);
  }
  details {
    position: relative;
    font-size: var(--crm-text-xs);
  }
  .extra {
    position: absolute;
    left: 0;
    top: 100%;
    z-index: 10;
    background: var(--v2-card);
    border: 1px solid var(--v2-line);
    border-radius: var(--crm-radius-md);
    padding: var(--crm-space-4);
    width: min(18rem, calc(100vw - 2rem));
    display: grid;
    gap: var(--crm-space-3);
    box-shadow: var(--crm-shadow-sm);
  }
  .extra label {
    display: grid;
    gap: 6px;
  }
  @media (min-width: 701px) {
    .task-filters {
      display: contents;
    }
    .crm-module-field {
      flex: 0 1 10rem;
    }
    .search-field {
      flex-basis: 12rem;
    }
  }
  @media (max-width: 700px) {
    .task-filters {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      width: 100%;
    }
    details {
      grid-column: 1;
    }
  }
</style>
