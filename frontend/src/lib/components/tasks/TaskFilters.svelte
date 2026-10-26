<script>
  import { asInternalPath } from '$lib/utils/paths.js';

  import { SvelteURLSearchParams } from 'svelte/reactivity';

  import { ViewToggle } from '$lib/components/ui/view-toggle';
  import SelectFilter from '$lib/components/ui/filter/SelectFilter.svelte';
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();

  import { CalendarDays } from '@lucide/svelte';
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { onDestroy } from 'svelte';
  import { page } from '$app/state';
  import { canFilterOwners } from '$lib/v2/permissions.js';
  let { url, people, columnTools } = $props();
  let timer;
  onDestroy(() => clearTimeout(timer));
  function apply(form) {
    clearTimeout(timer);
    const params = new SvelteURLSearchParams();
    for (const [key, value] of new FormData(form))
      if (String(value).trim()) params.set(key, String(value).trim());
    if (!params.has('all')) params.set('all', '0');
    void goto(resolve(asInternalPath(`/tasks?${params}`)), {
      keepFocus: true,
      noScroll: true,
      replaceState: true
    });
  }
  function viewHref(view) {
    const params = new SvelteURLSearchParams(url.searchParams);
    params.set('view', view);
    params.delete('offset');
    return `/tasks?${params}`;
  }
</script>

<div class="task-toolbar object-filters">
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
      ><span class="v2-sr-only">{ui('Search')}</span><input
        type="search"
        class="v2-input search"
        name="q"
        aria-label={ui('Search tasks')}
        placeholder={ui('Search tasks…')}
        value={url.searchParams.get('q') ?? ''}
      /></label
    >
    {#if canFilterOwners(page.data.permissions, 'tasks')}
      <div class="crm-module-field">
        <SelectFilter
          searchable
          name="assigned_to"
          label={ui('Owner')}
          allLabel={ui('All owners')}
          value={url.searchParams.get('assigned_to') ?? ''}
          options={people.map((person) => ({ value: person.id, label: person.name }))}
        />
      </div>
    {/if}
    <div class="crm-module-field">
      <SelectFilter
        name="status"
        label={ui('Status')}
        allLabel={ui('All statuses')}
        value={url.searchParams.get('status') ?? ''}
        options={['New', 'In Progress', 'Completed'].map((value) => ({ value, label: ui(value) }))}
      />
    </div>
    <div class="crm-module-field">
      <SelectFilter
        name="priority"
        label={ui('Priority')}
        allLabel={ui('All priorities')}
        value={url.searchParams.get('priority') ?? ''}
        options={['Low', 'Medium', 'High'].map((value) => ({ value, label: ui(value) }))}
      />
    </div>
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
  <div class="object-views">
    <ViewToggle
      view={url.searchParams.get('view') ?? 'list'}
      onchange={(view) =>
        goto(resolve(asInternalPath(viewHref(view))), { keepFocus: true, noScroll: true })}
    />
    <a
      class="v2-btn v2-btn-icon"
      href={resolve('/tasks/calendar')}
      aria-label={ui('Task calendar')}
      title={ui('Calendar')}><CalendarDays size={17} /></a
    >
    {#if columnTools}{@render columnTools()}{/if}
  </div>
</div>

<style>
  .task-filters {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: var(--crm-space-2);
    min-width: 0;
  }
  .crm-module-field {
    display: block;
    min-width: 0;
    flex: 0 1 10rem;
  }
  .search-field {
    flex: 1 1 12rem;
  }
  .v2-input {
    width: 100%;
    min-width: 0;
  }
  .task-toolbar {
    align-items: center;
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
      flex: 1 1 12rem;
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
