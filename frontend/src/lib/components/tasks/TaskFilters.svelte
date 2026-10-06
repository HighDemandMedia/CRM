<script>
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();

  import { List, Columns3 } from '@lucide/svelte';
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { onDestroy } from 'svelte';
  let { url, people } = $props();
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
    return `${resolve('/tasks')}?${params}`;
  }
</script>

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
  <input type="hidden" name="view" value={url.searchParams.get('view') ?? 'list'} />
  <input
    class="v2-input search"
    name="q"
    aria-label={ui('Search tasks')}
    placeholder={ui('Search tasks…')}
    value={url.searchParams.get('q') ?? ''}
  />
  <select
    class="v2-input"
    name="assigned_to"
    aria-label={ui('Owner')}
    value={url.searchParams.get('assigned_to') ?? ''}
    ><option value="">{ui('All owners')}</option>{#each people as person}<option value={person.id}
        >{person.name}</option
      >{/each}</select
  >
  <select
    class="v2-input"
    name="status"
    aria-label={ui('Status')}
    value={url.searchParams.get('status') ?? ''}
    ><option value="">{ui('All statuses')}</option
    >{#each ['New', 'In Progress', 'Completed'] as status}<option>{status}</option>{/each}</select
  >
  <select
    class="v2-input"
    name="priority"
    aria-label={ui('Priority')}
    value={url.searchParams.get('priority') ?? ''}
    ><option value="">{ui('All priorities')}</option
    >{#each ['Low', 'Medium', 'High'] as priority}<option>{priority}</option>{/each}</select
  >
  <details>
    <summary>{ui('Filters')}</summary>
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
  <nav class="views" aria-label={ui('Task view')}>
    <a
      href={viewHref('list')}
      aria-label={ui('List view')}
      title={ui('List')}
      aria-current={url.searchParams.get('view') !== 'pipeline' ? 'page' : undefined}
      ><List size={17} /></a
    ><a
      href={viewHref('pipeline')}
      aria-label={ui('Pipeline view')}
      title={ui('Pipeline')}
      aria-current={url.searchParams.get('view') === 'pipeline' ? 'page' : undefined}
      ><Columns3 size={17} /></a
    >
  </nav>
</form>

<style>
  .views {
    display: flex;
    margin-left: auto;
    gap: 3px;
  }
  .views a {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border-radius: var(--crm-radius-sm);
    color: var(--v2-slate);
  }
  .views a[aria-current='page'] {
    background: var(--v2-ink);
    color: white;
  }

  .task-filters {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: var(--crm-space-2);
    padding: 14px var(--crm-space-6);
  }
  .v2-input {
    width: auto;
    max-width: 100%;
    font-size: var(--crm-text-xs);
  }
  .search {
    flex: 1;
    min-width: 180px;
  }
  .completed {
    font-size: var(--crm-text-xs);
    display: flex;
    align-items: center;
    gap: 6px;
  }
  details {
    position: relative;
    font-size: var(--crm-text-xs);
  }
  summary {
    cursor: pointer;
    padding: 9px var(--crm-space-3);
    border: 1px solid var(--v2-line);
    border-radius: var(--crm-radius-md);
  }
  .extra {
    position: absolute;
    right: 0;
    top: 100%;
    z-index: 10;
    background: var(--v2-card);
    border: 1px solid var(--v2-line);
    border-radius: var(--crm-radius-md);
    padding: 14px;
    display: grid;
    gap: var(--crm-space-3);
    box-shadow: var(--crm-shadow-sm);
  }
  .extra label {
    display: grid;
    gap: 6px;
  }
</style>
