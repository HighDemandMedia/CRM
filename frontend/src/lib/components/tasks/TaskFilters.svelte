<script>
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
    aria-label="Search tasks"
    placeholder="Search tasks…"
    value={url.searchParams.get('q') ?? ''}
  />
  <select
    class="v2-input"
    name="assigned_to"
    aria-label="Owner"
    value={url.searchParams.get('assigned_to') ?? ''}
    ><option value="">All owners</option>{#each people as person}<option value={person.id}
        >{person.name}</option
      >{/each}</select
  >
  <select
    class="v2-input"
    name="status"
    aria-label="Status"
    value={url.searchParams.get('status') ?? ''}
    ><option value="">All statuses</option
    >{#each ['New', 'In Progress', 'Completed'] as status}<option>{status}</option>{/each}</select
  >
  <select
    class="v2-input"
    name="priority"
    aria-label="Priority"
    value={url.searchParams.get('priority') ?? ''}
    ><option value="">All priorities</option>{#each ['Low', 'Medium', 'High'] as priority}<option
        >{priority}</option
      >{/each}</select
  >
  <details>
    <summary>Filters</summary>
    <div class="extra">
      <label
        >Due from<input
          class="v2-input"
          type="date"
          name="due_date__gte"
          value={url.searchParams.get('due_date__gte') ?? ''}
        /></label
      >
      <label
        >Due through<input
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
    />Show completed</label
  >
  <nav class="views" aria-label="Task view">
    <a
      href={viewHref('list')}
      aria-label="List view"
      title="List"
      aria-current={url.searchParams.get('view') !== 'pipeline' ? 'page' : undefined}
      ><List size={17} /></a
    ><a
      href={viewHref('pipeline')}
      aria-label="Pipeline view"
      title="Pipeline"
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
    border-radius: 6px;
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
    gap: 8px;
    padding: 14px 22px;
  }
  .v2-input {
    width: auto;
    max-width: 100%;
    font-size: 12px;
  }
  .search {
    flex: 1;
    min-width: 180px;
  }
  .completed {
    font-size: 12px;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  details {
    position: relative;
    font-size: 12px;
  }
  summary {
    cursor: pointer;
    padding: 9px 12px;
    border: 1px solid var(--v2-line);
    border-radius: 7px;
  }
  .extra {
    position: absolute;
    right: 0;
    top: 100%;
    z-index: 10;
    background: var(--v2-card);
    border: 1px solid var(--v2-line);
    border-radius: 8px;
    padding: 14px;
    display: grid;
    gap: 12px;
    box-shadow: 0 5px 16px #0001;
  }
  .extra label {
    display: grid;
    gap: 6px;
  }
</style>
