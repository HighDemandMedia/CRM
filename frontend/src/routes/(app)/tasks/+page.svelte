<script>
  import { showStageRequirements } from "$lib/components/pipelines/feedback.js";
  import { configuredStages, configuredLabel } from "$lib/v2/pipeline-config.js";
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
  import TaskFilters from '$lib/components/tasks/TaskFilters.svelte';
  import '$lib/v2/styles/list-view.css';
  import Pill from '$lib/v2/components/Pill.svelte';
  import Avatar from '$lib/v2/components/Avatar.svelte';
  import EmptyState from '$lib/v2/components/EmptyState.svelte';
  import { count, relativeDays, daysSince } from '$lib/v2/format.js';
  import { TASK_PRIORITY_TONE, TASK_STATUS_TONE } from '$lib/v2/enums.js';
  import { invalidateAll } from '$app/navigation';
  import '$lib/v2/styles/pipeline.css';
  import { enhance, deserialize } from '$app/forms';
  import { CircleCheck, Circle, Plus } from '@lucide/svelte';

  /** @type {{ data: any, form: any }} */
  let { data, form } = $props();

  const statuses = $derived(configuredStages(page.data.pipelineConfig, 'Task', ['New', 'In Progress', 'Completed'].map(value => ({ value, label: value }))).map(s => s.value));
  const statusName = value => configuredLabel(page.data.pipelineConfig, 'Task', value, value);
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
      if (result.type !== 'success' && showStageRequirements(result, 'Task', id, {status})) return;
      if (result.type !== 'success') throw new Error(result.type === 'failure' ? String(result.data?.error || 'Could not move the task.') : 'Could not move the task. Please try again.');
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

<PageHeader title="Tasks">
  {#snippet sub()}
    <span class="v2-num">{count(totals.open)}</span> open ·
    <span class="v2-num" style="color:var(--v2-rust)">{count(totals.overdue)}</span> overdue
  {/snippet}
  {#snippet actions()}
    <a class="v2-btn v2-btn-primary" href={resolve('/tasks/new')}><Plus />New task</a>
  {/snippet}
</PageHeader>

<SectionTabs set="tasks" />
<div class="task-totals">
  <span>{count(totals.due_this_week)} due this week</span><span
    >{count(totals.no_due_date)} without due date</span
  >
</div>
<TaskFilters url={page.url} people={data.people} />

{#if form?.error}
  <p class="v2-pad v2-form-error" role="alert">{form.error}</p>
{/if}

{#if moveError}<p class="v2-pad v2-form-error" role="alert">{moveError}</p>{/if}
<div class="v2-scroll" class:task-list={!pipeline} class:pipeline-scroll={pipeline}>
  {#if pipeline}
    <div class="hdm-board" aria-label="Task pipeline">
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
                draggable={!moving}
                ondragstart={(event) => {
                  dragged = task.id;
                  event.dataTransfer?.setData('text/plain', task.id);
                }}
                ondragend={() => {
                  dragged = '';
                  target = '';
                }}
              >
                <a class="pipeline-name" href={resolve(`/tasks/${task.id}`)}>{task.title || `Task · ${task.id.slice(0, 8)}`}</a>
                <dl>
                  <div>
                    <dt>Owner</dt>
                    <dd>{task.assigned_names.join(', ') || '—'}</dd>
                  </div>
                  <div>
                    <dt>Priority</dt>
                    <dd>{task.priority}</dd>
                  </div>
                  <div>
                    <dt>Due</dt>
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
                  >{#each statuses as choice}<option value={choice}>{statusName(choice)}</option>{/each}</select
                >
              </article>
            {:else}<p class="pipeline-empty">No tasks</p>{/each}
          </div>
        </section>
      {/each}
    </div>
  {:else if tasks.length === 0}
    <EmptyState
      title={data.showAll ? 'No tasks yet' : 'Nothing on your list'}
      body={data.showAll ? 'Create a task to get started.' : 'No open tasks match this view.'}
    >
      {#snippet icon()}<CircleCheck size={21} />{/snippet}
      {#snippet actions()}
        <a class="v2-btn v2-btn-primary" href={resolve('/tasks/new')}>New task</a>
        {#if !data.showAll}
          <a class="v2-btn" href={resolve('/tasks?all=1')}>Show completed</a>
        {/if}
      {/snippet}
    </EmptyState>
  {:else}
    <div class="v2-table-wrap hdm-list">
      <table class="v2-table">
        <thead>
          <tr>
            <th style="width:38px"><span class="v2-sr-only">Done</span></th>
            <th>Task</th>
            <th>Association</th>
            <th>Priority</th>
            <th>Status</th>
            <th>Owner</th>
            <th class="v2-r">Due</th>
            <th>Last Activity</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {#each tasks as t (t.id)}
            {@const late = overdueDays(t)}
            <tr style={t.is_done ? 'opacity:.5' : ''}>
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
              <td data-m="title" style="white-space:normal;max-width:420px">
                <a
                  href={resolve(`/tasks/${t.id}`)}
                  class="v2-table-primary"
                  style={t.is_done ? 'text-decoration:line-through' : ''}>{t.title || `Task · ${t.id.slice(0, 8)}`}</a
                >
                {#if t.description}
                  <span class="v2-table-secondary v2-task-note">{t.description}</span>
                {/if}
              </td>
              <td>
                {#if t.related}
                  <a href={resolve(t.related.href)} style="color:inherit">{t.related.name}</a>
                  <span class="v2-table-secondary v2-task-kind">{t.related.kind}</span>
                {:else}
                  <span class="v2-muted">—</span>
                {/if}
              </td>
              <td><Pill tone={TASK_PRIORITY_TONE[t.priority]}>{t.priority}</Pill></td>
              <td data-m="tag">
                <Pill tone={TASK_STATUS_TONE[t.status]}>{statusName(t.status)}</Pill>
              </td>
              <td data-m="hide">
                {#if t.assigned_names.length}
                  <span>{t.assigned_names.join(', ')}</span>
                {:else}
                  <span class="v2-muted">nobody</span>
                {/if}
              </td>
              <td
                class="v2-r"
                class:v2-muted={!late}
                style={late ? 'color:var(--v2-rust);font-weight:600' : ''}
              >
                {#if !t.due_date}
                  <span class="v2-muted">no due date</span>
                {:else if late}
                  {late}d late
                {:else}
                  {relativeDays(t.due_date)}
                {/if}
              </td>
              <td title={t.last_activity_at ? new Date(t.last_activity_at).toLocaleString() : undefined}>{t.last_activity_at ? relativeDays(t.last_activity_at) : '—'}</td>
              <td class="list-row-actions"><a aria-label={`Edit ${t.title}`} href={resolve(`/tasks/${t.id}/edit`)}>Edit</a></td>
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
    border-radius: 5px;
    background: transparent;
    font-size: 11px;
    color: var(--v2-slate);
  }
  .task-parent {
    display: block;
    margin-top: 8px;
    color: var(--v2-slate);
    font-size: 12px;
  }
  .pipeline-column.drop-target {
    outline: 2px solid #6c86b5;
    outline-offset: -2px;
  }

  .task-totals {
    display: flex;
    gap: 20px;
    padding: 12px 22px 0;
    color: var(--v2-slate);
    font-size: 12px;
  }
  .task-list {
    padding: 0 22px 20px;
  }
  :global(.task-list .hdm-list) {
    overflow: auto;
  }
  :global(.task-list .v2-table) {
    min-width: 850px;
  }
  :global(.v2-root a.v2-btn-primary) {
    color: white;
  }
  .v2-task-note,
  .v2-task-kind {
    display: block;
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
    /* A note long enough to explain itself is long enough to bury the next
       three tasks. Two lines here, the rest on the task itself. */
    .v2-task-note {
      display: -webkit-box;
      -webkit-line-clamp: 2;
      line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    /* Hidden here rather than with data-m="hide", which would tie at equal
       specificity with the rule above and resolve on stylesheet order. */
    .v2-task-kind {
      display: none;
    }
  }
</style>
