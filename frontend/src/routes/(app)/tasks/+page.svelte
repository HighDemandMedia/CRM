<script>
  import { listViewPreference } from '$lib/v2/list-view-preference.svelte.js';
  import { useI18n } from '$lib/i18n/context.js';
  const { ui, locale, count, relativeDays } = useI18n();

  import { can } from '$lib/v2/permissions.js';
  import { showStageRequirements } from '$lib/components/pipelines/feedback.js';
  import { configuredStages, configuredLabel } from '$lib/v2/pipeline-config.js';
  import { resolve } from '$app/paths';
  /**
   * Tasks are the one list where the row itself is the work, so every row
   * carries the control that finishes it. v1 needed a click into a detail
   * page to tick a checkbox, which is why nobody ticked them.
   *
   * Now on the real API, and the tick is a PATCH. The mock left a note saying
   * this must never become "a tick that looks saved and is not", so the row
   * shows a pending state while the request is in flight and takes whatever
   * the server says, rather than assuming it worked.
   */
  import { page } from '$app/state';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import SectionTabs from '$lib/v2/components/SectionTabs.svelte';
  import { listColumns, columnValue } from '$lib/v2/list-columns.js';
  import { columnSelection } from '$lib/v2/column-selection.svelte.js';
  import ColumnPicker from '$lib/v2/components/ColumnPicker.svelte';
  import TaskFilters from '$lib/components/tasks/TaskFilters.svelte';
  import '$lib/v2/styles/list-view.css';
  import Pill from '$lib/v2/components/Pill.svelte';
  import EmptyState from '$lib/v2/components/EmptyState.svelte';
  import { daysSince } from '$lib/v2/format.js';
  import { TASK_PRIORITY_TONE, TASK_STATUS_TONE } from '$lib/v2/enums.js';
  import { invalidateAll } from '$app/navigation';
  import '$lib/v2/styles/pipeline.css';
  import { enhance, deserialize } from '$app/forms';
  import { CircleCheck, Circle, Plus } from '@lucide/svelte';

  /** @type {{ data: any, form: any }} */
  let { data, form } = $props();

  const catalog = $derived(listColumns('Task', page.data.propertyLayout?.Task));
  const fields = $derived(catalog.map((c) => [c.key, c.system ? ui(c.label) : c.label]));
  listViewPreference(
    () => `${page.data.accountId}.${page.data.accountUser?.email}.Task`,
    () => page.url
  );
  const selection = columnSelection(
    () => catalog,
    () => `${page.data.accountId}.${page.data.accountUser?.email}.Task`
  );
  const columns = $derived(selection.selected);

  const statuses = $derived(
    configuredStages(
      page.data.pipelineConfig,
      'Task',
      ['New', 'In Progress', 'Completed'].map((value) => ({ value, label: value }))
    ).map((s) => s.value)
  );
  const statusName = (value) => configuredLabel(page.data.pipelineConfig, 'Task', value, value);
  let pipeline = $derived(page.url.searchParams.get('view') === 'pipeline');
  let dragged = $state(''),
    target = $state(''),
    moving = $state(false),
    moveError = $state('');
  async function move(id, status) {
    dragged = '';
    target = '';
    if (moving || data.tasks.find((task) => task.id === id)?.status === status) return;
    moving = true;
    moveError = '';
    const body = new FormData();
    body.set('id', id);
    body.set('status', status);
    try {
      const response = await fetch('?/move', {
        method: 'POST',
        body,
        headers: { 'x-sveltekit-action': 'true' }
      });
      const result = deserialize(await response.text());
      if (result.type !== 'success' && showStageRequirements(result, 'Task', id, { status }))
        return;
      if (result.type !== 'success')
        throw new Error(
          result.type === 'failure'
            ? String(result.data?.error || 'Could not move the task.')
            : 'Could not move the task. Please try again.'
        );
      await invalidateAll();
    } catch (error) {
      moveError = error.message;
    } finally {
      moving = false;
    }
  }
  let totals = $derived(data.totals);
  let tasks = $derived(data.tasks);

  /** Rows with a save in flight, so the tick can show it is thinking. */
  let saving = $state(/** @type {Record<string, boolean>} */ ({}));

  /** Overdue is only meaningful for something still open. */
  const overdueDays = (/** @type {any} */ t) => {
    if (!t.due_date || t.is_done) return 0;
    const n = daysSince(t.due_date) ?? 0;
    return n > 0 ? n : 0;
  };
</script>

<PageHeader title={ui('Tasks')}>
  {#snippet sub()}
    <span class="v2-num">{count(totals.open)}</span>
    {ui('open ·')}
    <span class="v2-num" style="color:var(--v2-rust)">{count(totals.overdue)}</span>
    {ui('overdue')}
  {/snippet}
  {#snippet actions()}
    {#if can(page.data.permissions, 'tasks', 'create')}<a
        class="v2-btn v2-btn-primary"
        href={resolve('/tasks/new')}><Plus />{ui('New task')}</a
      >{/if}
  {/snippet}
</PageHeader>

<SectionTabs set="tasks" />
<div class="task-totals">
  <span>{count(totals.due_this_week)} {ui('due this week')}</span><span
    >{count(totals.no_due_date)} {ui('without due date')}</span
  >
</div>
<TaskFilters url={page.url} people={data.people} />
{#if !pipeline}<div class="list-column-tools">
    <ColumnPicker
      {fields}
      selected={columns}
      onToggle={(key) => selection.toggle(key)}
      onShowAll={selection.showAll}
      onReset={selection.reset}
    />
  </div>{/if}

{#if form?.error}
  <p class="v2-pad v2-form-error" role="alert">{ui(form.error)}</p>
{/if}

{#if moveError}<p class="v2-pad v2-form-error" role="alert">{moveError}</p>{/if}
<div class="v2-scroll" class:task-list={!pipeline} class:pipeline-scroll={pipeline}>
  {#if pipeline}
    <div class="hdm-board" aria-label={ui('Task pipeline')}>
      {#each statuses as status}
        <section
          class="pipeline-column"
          aria-label={`${status} tasks`}
          class:drop-target={target === status}
          data-tone={status === 'Completed'
            ? 'success'
            : status === 'In Progress'
              ? 'waiting'
              : 'open'}
          ondragover={(event) => {
            if (dragged && !moving) {
              event.preventDefault();
              target = status;
            }
          }}
          ondragleave={(event) => {
            if (!event.currentTarget.contains(/** @type {Node|null} */ (event.relatedTarget)))
              target = '';
          }}
          ondrop={(event) => {
            event.preventDefault();
            if (dragged) void move(dragged, status);
          }}
        >
          <header class="pipeline-header">
            <h2>{statusName(status)}</h2>
            <span>{tasks.filter((task) => task.status === status).length}</span>
          </header>
          <div class="pipeline-cards">
            {#each tasks.filter((task) => task.status === status) as task (task.id)}
              <article
                class="pipeline-card"
                draggable={!moving && can(page.data.permissions, 'tasks', 'stage')}
                ondragstart={(event) => {
                  dragged = task.id;
                  event.dataTransfer?.setData('text/plain', task.id);
                }}
                ondragend={() => {
                  dragged = '';
                  target = '';
                }}
              >
                <a class="pipeline-name" href={resolve(`/tasks/${task.id}`)}
                  >{task.title || `Task · ${task.id.slice(0, 8)}`}</a
                >
                <dl>
                  <div>
                    <dt>{ui('Owner')}</dt>
                    <dd>{task.assigned_names.join(', ') || '—'}</dd>
                  </div>
                  <div>
                    <dt>{ui('Priority')}</dt>
                    <dd>{task.priority}</dd>
                  </div>
                  <div>
                    <dt>{ui('Due')}</dt>
                    <dd>{task.due_date ? relativeDays(task.due_date) : '—'}</dd>
                  </div>
                </dl>
                {#if task.related}<a class="task-parent" href={resolve(task.related.href)}
                    >{task.related.name}</a
                  >{/if}
                <select
                  class="task-stage"
                  aria-label={`Stage for ${task.title}`}
                  value={task.status}
                  disabled={moving}
                  onchange={(event) => move(task.id, event.currentTarget.value)}
                  >{#each statuses as choice}<option value={choice}>{statusName(choice)}</option
                    >{/each}</select
                >
              </article>
            {:else}<p class="pipeline-empty">{ui('No tasks')}</p>{/each}
          </div>
        </section>
      {/each}
    </div>
  {:else if tasks.length === 0}
    <EmptyState
      title={data.showAll ? ui('No tasks yet') : ui('Nothing on your list')}
      body={data.showAll ? 'Create a task to get started.' : 'No open tasks match this view.'}
    >
      {#snippet icon()}<CircleCheck size={21} />{/snippet}
      {#snippet actions()}
        {#if can(page.data.permissions, 'tasks', 'create')}<a
            class="v2-btn v2-btn-primary"
            href={resolve('/tasks/new')}>{ui('New task')}</a
          >{/if}
        {#if !data.showAll}
          <a class="v2-btn" href={resolve('/tasks?all=1')}>{ui('Show completed')}</a>
        {/if}
      {/snippet}
    </EmptyState>
  {:else}
    <!-- svelte-ignore a11y_no_noninteractive_tabindex (Keyboard users need to focus this overflow region to scroll the table.) -->
    <div
      class="v2-table-wrap hdm-list"
      role="region"
      aria-label={ui('Tasks; scroll horizontally to see all columns')}
      tabindex="0"
    >
      <table class="v2-table">
        <thead>
          <tr>
            <th style="width:38px"><span class="v2-sr-only">{ui('Done')}</span></th>
            {#each columns as key (key)}<th scope="col">{fields.find(([id]) => id === key)?.[1]}</th
              >{/each}
            <th>{ui('Actions')}</th>
          </tr>
        </thead>
        <tbody>
          {#each tasks as t (t.id)}
            {@const late = overdueDays(t)}
            <tr>
              <!-- Not the identifier, so it must not take the title slot, but it
                   is the one control on this row, so it stays on the title line
                   at the left rather than dropping into the meta run. -->
              <td data-m="lead">
                <form
                  method="POST"
                  action="?/toggle"
                  use:enhance={() => {
                    saving[t.id] = true;
                    return async ({ update }) => {
                      await update({ reset: false });
                      saving[t.id] = false;
                    };
                  }}
                >
                  <input type="hidden" name="id" value={t.id} />
                  <input type="hidden" name="done" value={t.is_done ? 'false' : 'true'} />
                  <button
                    type="submit"
                    class="v2-tick"
                    disabled={saving[t.id]}
                    aria-label={t.is_done ? `Reopen ${t.title}` : `Mark ${t.title} done`}
                  >
                    {#if t.is_done}
                      <CircleCheck size={17} style="color:var(--v2-moss)" />
                    {:else}
                      <Circle size={17} />
                    {/if}
                  </button>
                </form>
              </td>
              {#each columns as key (key)}
                <td data-field={key}>
                  {#if key === 'title'}
                    <a
                      href={resolve(`/tasks/${t.id}`)}
                      class="v2-table-primary"
                      style={t.is_done ? 'text-decoration:line-through' : ''}
                      >{t.title || `Task · ${t.id.slice(0, 8)}`}</a
                    >
                  {:else if key === 'priority'}
                    <Pill tone={TASK_PRIORITY_TONE[t.priority]}>{t.priority}</Pill>
                  {:else if key === 'status'}
                    <Pill tone={TASK_STATUS_TONE[t.status]}>{statusName(t.status)}</Pill>
                  {:else if key === 'due_date'}
                    <span class:overdue={late > 0}
                      >{!t.due_date ? '—' : late ? `${late}d late` : relativeDays(t.due_date)}</span
                    >
                  {:else if ['account', 'opportunity', 'case'].includes(key) && t.related && t[key]?.id === t.related.id}
                    <a href={resolve(t.related.href)}>{t.related.name}</a>
                  {:else if key === 'last_activity_at' || key === 'created_at'}
                    <span title={t[key] ? new Date(t[key]).toLocaleString(locale()) : undefined}
                      >{t[key] ? relativeDays(t[key]) : '—'}</span
                    >
                  {:else}
                    {columnValue(t, key, catalog)}
                  {/if}
                </td>
              {/each}
              <td class="list-row-actions"
                >{#if can(page.data.permissions, 'tasks', 'edit')}<a
                    aria-label={`Edit ${t.title}`}
                    href={resolve(`/tasks/${t.id}/edit`)}>{ui('Edit')}</a
                  >{/if}</td
              >
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</div>

<style>
  .task-stage {
    width: 100%;
    margin-top: 10px;
    padding: 6px;
    border: 1px solid var(--v2-line);
    border-radius: var(--crm-radius-sm);
    background: transparent;
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
  }
  .task-parent {
    display: block;
    margin-top: var(--crm-space-2);
    color: var(--v2-slate);
    font-size: var(--crm-text-xs);
  }
  .pipeline-column.drop-target {
    outline: 2px solid var(--crm-info);
    outline-offset: -2px;
  }

  .task-totals {
    display: flex;
    gap: var(--crm-space-5);
    padding: var(--crm-space-3) var(--crm-space-6) 0;
    color: var(--v2-slate);
    font-size: var(--crm-text-xs);
  }
  .task-list {
    padding: 0 var(--crm-space-6) var(--crm-space-5);
  }
  :global(.task-list .hdm-list) {
    overflow: auto;
  }
  :global(.task-list .v2-table) {
    min-width: 850px;
  }
  :global(.task-list .v2-table td[data-field='title']) {
    min-width: 14rem;
    overflow-wrap: anywhere;
  }
  :global(.v2-root a.v2-btn-primary) {
    color: var(--crm-primary-text);
  }
  .overdue {
    color: var(--crm-danger);
    font-weight: 600;
  }
  .v2-tick {
    border: 0;
    background: none;
    padding: 0;
    display: grid;
    place-items: center;
    cursor: pointer;
    color: var(--v2-slate);
  }
  .v2-tick:hover {
    color: var(--v2-ink);
  }
  .v2-tick:disabled {
    cursor: progress;
    opacity: 0.45;
  }
  /* Checking a task off is the main reason this page gets opened on a phone,
     and the target was the 17px icon itself. Grown to 40px and pulled back by
     the overhang, so the target changes but the layout does not. */
  @media (max-width: 768px) {
    .v2-tick {
      min-width: 40px;
      min-height: 40px;
      margin: -9px 0 -9px -11px;
    }
  }
</style>
