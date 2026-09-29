<script>
  import PropertySummary from '$lib/v2/components/PropertySummary.svelte';
  import StageRuleNotice from "$lib/components/pipelines/StageRuleNotice.svelte";
  import { page } from "$app/state";
  import { configuredStages, configuredLabel } from "$lib/v2/pipeline-config.js";
  const statusOptions = $derived(configuredStages(page.data.pipelineConfig, "Task", ["New", "In Progress", "Completed"].map(value => ({value,label:value}))));
  import TaskReminder from '$lib/components/tasks/TaskReminder.svelte';
  import { asInternalPath } from '$lib/utils/paths.js';
  import { resolve } from '$app/paths';
  import { enhance } from '$app/forms';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import RecordTabs from '$lib/v2/components/RecordTabs.svelte';
  import Attachments from '$lib/v2/components/Attachments.svelte';
  import TaskAssignees from '$lib/components/tasks/TaskAssignees.svelte';
  import TaskParent from '$lib/components/tasks/TaskParent.svelte';
  import Pill from '$lib/v2/components/Pill.svelte';
  import { longDate, daysSince } from '$lib/v2/format.js';
  import { TASK_PRIORITY_TONE, TASK_STATUS_TONE } from '$lib/v2/enums.js';
  import { CircleCheck, RotateCcw, Pencil } from '@lucide/svelte';
  let { data, form } = $props();
  let task = $derived(data.task);
  let editing = $state(false),
    busy = $state(false),
    commentBusy = $state(false),
    comment = $state('');
  let draft = $state(/** @type {any} */ ({}));
  const formId = $props.id();
  let comments = $derived(data.activity.filter((entry) => entry.type === 'comment'));
  let history = $derived(data.activity.filter((entry) => entry.type !== 'comment'));
  let files = $derived(
    data.activity
      .filter((entry) => entry.type === 'file' && entry.href)
      .map((entry) => ({
        id: entry.attachmentId,
        canDelete: entry.canDelete,
        name: entry.body,
        href: /** @type {`/api/attachments/${string}/download`} */ (entry.href)
      }))
  );
  let late = $derived(!task.is_done && task.due_date && (daysSince(task.due_date) ?? 0) > 0);
  const exactDate = (value) =>
    value
      ? new Date(value).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
      : '—';
  function edit() {
    draft = { ...data.editor.form, assigned_to: [...task.assigned_ids] };
    editing = true;
  }
  function save() {
    busy = true;
    return async ({ result, update }) => {
      try {
        await update({ reset: false });
        if (result.type === 'success') editing = false;
      } finally {
        busy = false;
      }
    };
  }
</script>

<PageHeader title={task.title || `Task · ${task.id.slice(0, 8)}`} record>
  {#snippet crumb()}<a href={resolve('/tasks')}>Tasks</a><span>{configuredLabel(page.data.pipelineConfig, 'Task', task.status, task.status)}</span>{/snippet}
  {#snippet actions()}
    {#if editing}<button class="v2-btn v2-btn-primary" type="submit" form={formId} disabled={busy}
        >{busy ? 'Saving…' : 'Save'}</button
      ><button class="v2-btn" disabled={busy} onclick={() => (editing = false)}>Cancel</button>
    {:else}<button class="v2-btn" onclick={edit}><Pencil size={14} />Edit</button>
      <form method="POST" action="?/toggle" use:enhance>
        <input type="hidden" name="done" value={task.is_done ? 'false' : 'true'} /><button
          class="v2-btn v2-btn-primary"
          type="submit"
          >{#if task.is_done}<RotateCcw size={15} />Reopen{:else}<CircleCheck size={15} />Complete
            task{/if}</button
        >
      </form>
    {/if}
  {/snippet}
</PageHeader>
<StageRuleNotice issue={form?.stageRequirements}/>
{#if form?.error && !form?.stageRequirements}<p class="v2-error error" role="alert">{form.error}</p>{/if}
<div class="task-profile">
  <main>
    <section class="panel description">
      {#if editing}<label
          >Task name<input
            class="v2-input"
            form={formId}
            name="title" required
            disabled={busy}
            bind:value={draft.title}
            maxlength="200"
          /></label
        >
        <label
          >Description<textarea
            class="v2-input"
            form={formId}
            name="description"
            disabled={busy}
            bind:value={draft.description}
            rows="5"></textarea></label
        >
      {:else}<h2>Description</h2>
        <p class="body">{task.description || 'No description.'}</p>{/if}
    </section>
    <section class="panel journal">
      <RecordTabs>
        {#snippet notes()}
          <form
            method="POST"
            action="?/comment"
            use:enhance={() => {
              commentBusy = true;
              return async ({ result, update }) => {
                try {
                  await update({ reset: false });
                  if (result.type === 'success') comment = '';
                } finally {
                  commentBusy = false;
                }
              };
            }}
          >
            <textarea
              class="v2-input"
              aria-label="Add a note"
              name="comment"
              rows="3"
              placeholder="Write a note…"
              bind:value={comment}></textarea>
            <button class="v2-btn" disabled={commentBusy || !comment.trim()}
              >{commentBusy ? 'Saving…' : 'Add note'}</button
            >
          </form>
          <div class="entries">
            {#each comments as entry (entry.id)}<article>
                <p class="body">{entry.body}</p>
                <small>{entry.by || '—'} · {exactDate(entry.at)}</small>
              </article>{:else}<p class="muted">No notes.</p>{/each}
          </div>
        {/snippet}
        {#snippet activity()}<div class="entries">
            {#each history as entry (entry.id)}<article>
                {#if entry.href}<a
                    href={resolve(asInternalPath(entry.href))}
                    target="_blank"
                    rel="noopener noreferrer">{entry.body}</a
                  >{:else}<p class="body">{entry.body}</p>{/if}<small
                  >{entry.by ? `${entry.by} · ` : ''}{exactDate(entry.at)}</small
                >
              </article>{:else}<p class="muted">No activity yet.</p>{/each}
          </div>{/snippet}
      </RecordTabs>
    </section>
    <details class="panel attachments">
      <summary>Attachments <span>{files.length}</span></summary>
      <div><Attachments attachments={files} action="?/comment" /></div>
    </details>
  </main>
  <aside class="panel properties">
    <h2>Properties</h2>
    {#if editing}<form id={formId} method="POST" action="?/properties" use:enhance={save}>
        <input type="hidden" name="parent_kind_original" value={data.editor.form.parent_kind} />
        <input type="hidden" name="parent_id_original" value={data.editor.form.parent_id} />
        <fieldset disabled={busy}>
          <label
            >Status<select class="v2-input" name="status" bind:value={draft.status}
              >{#each ['New', 'In Progress', 'Completed'] as status}<option>{status}</option
                >{/each}</select
            ></label
          >
          <label
            >Priority<select class="v2-input" name="priority" bind:value={draft.priority}
              ><option value="">None</option>{#each ['Low', 'Medium', 'High'] as priority}<option>{priority}</option
                >{/each}</select
            ></label
          >
          <label
            >Due date<input
              class="v2-input"
              type="date"
              name="due_date"
              bind:value={draft.due_date}
            /></label
          >
          <TaskReminder bind:value={draft.reminder_days} />
          <TaskAssignees people={data.editor.owners} bind:selected={draft.assigned_to} />
          <TaskParent
            parents={data.editor.parents}
            bind:kind={draft.parent_kind}
            bind:selected={draft.parent_id}
          />
        </fieldset>
      </form>
    {:else}
      <PropertySummary target="Task" record={task} entries={[
        ['Name',task.title], ['Status', configuredLabel(page.data.pipelineConfig, 'Task', task.status, task.status)], ['Priority', task.priority],
        ['Due date', task.due_date ? longDate(task.due_date) + (late ? ' · Overdue' : '') : '—', 'due_date'],
        ['Reminder',task.reminder_days == null ? 'No reminder' : task.reminder_days === 0 ? 'On due date' : `${task.reminder_days} days before`, 'reminder_days'],
        ['Assigned to',task.assigned_names.join(', ') || '—'],
        ['Last Activity',exactDate(task.last_activity_at)], ['Created',exactDate(task.created_at)]
      ]}/>

      <section class="associations">
        <h2>Association</h2>
        {#if task.related}<a class="associated" href={resolve(asInternalPath(task.related.href))}
            ><small
              >{{ account: 'Company', deal: 'Deal', ticket: 'Ticket', lead: 'Lead' }[
                task.related.kind
              ] || task.related.kind}</small
            ><strong>{task.related.name}</strong></a
          >{:else}<p class="muted">No association.</p>{/if}
      </section>
      {#if data.contacts.length}<section class="associations">
          <h2>Contacts</h2>
          {#each data.contacts as contact}<a
              class="associated"
              href={resolve(`/contacts/${contact.id}`)}
              ><strong>{contact.name}</strong>{#if contact.email}<small>{contact.email}</small
                >{/if}</a
            >{/each}
        </section>{/if}
    {/if}

    {#if data.canDelete}<form class="delete" method="POST" action="?/delete" use:enhance>
        <button type="submit" class="v2-btn">Delete</button>
      </form>{/if}
  </aside>
</div>

<style>
  .task-profile {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 310px;
    gap: 18px;
    flex: 1;
    min-height: 0;
    overflow: hidden;
    padding: 16px 22px 20px;
  }
  main {
    overflow-y: auto;
    min-height: 0;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }
  .panel {
    background: var(--v2-card);
    border-radius: 12px;
    padding: 20px;
  }
  h2 {
    font-size: 14px;
    font-weight: 650;
    margin: 0 0 12px;
  }
  .body {
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    margin: 0;
    font-size: 14px;
    line-height: 1.6;
  }
  .description > .body {
    max-height: 240px;
    overflow: auto;
  }
  label {
    display: grid;
    gap: 7px;
    font-size: 12px;
    color: var(--v2-slate);
    margin-bottom: 16px;
  }
  .v2-input {
    width: 100%;
  }
  .journal form .v2-btn {
    margin-top: 8px;
  }
  .entries {
    max-height: 340px;
    overflow: auto;
    margin-top: 16px;
  }
  .entries article {
    padding: 12px 0;
    border-bottom: 1px solid var(--v2-line-soft);
  }
  small {
    display: block;
    margin-top: 6px;
    font-size: 11px;
    color: var(--v2-slate);
  }
  .properties {
    min-height: 0;
    overflow-y: auto;
  }
  fieldset {
    border: 0;
    padding: 0;
    margin: 0;
    min-width: 0;
  }
  .associations {
    margin-top: 22px;
  }
  .associated {
    display: block;
    background: var(--v2-paper);
    border-radius: 7px;
    padding: 10px;
    color: var(--v2-ink);
    text-decoration: none;
    margin-top: 6px;
    overflow-wrap: anywhere;
    font-size: 13px;
  }
  .associated small {
    margin: 0 0 4px;
  }
  .delete {
    display: flex;
    justify-content: flex-end;
    margin-top: 24px;
  }
  .delete button {
    color: var(--v2-rust);
  }
  .attachments {
    padding: 0;
  }
  .attachments summary {
    padding: 15px 20px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 600;
  }
  .attachments summary span {
    color: var(--v2-slate);
    margin-left: 8px;
    font-size: 12px;
  }
  .attachments > div {
    padding: 0 20px 20px;
  }
  .muted {
    color: var(--v2-slate);
    font-size: 12px;
  }
  .error {
    margin: 0;
    padding: 10px 22px;
  }
  @media (max-width: 800px) {
    .task-profile {
      grid-template-columns: 1fr;
      overflow: auto;
      padding: 12px;
    }
    main,
    .properties {
      overflow: visible;
    }
  }
</style>
