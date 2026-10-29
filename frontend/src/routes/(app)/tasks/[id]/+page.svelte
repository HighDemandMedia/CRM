<script>
  import RecordAction from '$lib/v2/components/RecordAction.svelte';
  import * as Dropdown from '$lib/components/ui/dropdown-menu/index.js';
  import { StickyNote, ChevronDown, Trash2 } from '@lucide/svelte';
  let recordTabs;
  let deleteForm = $state();
  import Notice from '$lib/components/Notice.svelte';
  import { recordValidation } from '$lib/components/creation/validation.js';
  import { canChooseOwner } from '$lib/v2/permissions.js';
  import { useI18n } from '$lib/i18n/context.js';
  const { ui, locale, longDate } = useI18n();

  import PropertySummary from '$lib/v2/components/PropertySummary.svelte';
  import StageRuleNotice from '$lib/components/pipelines/StageRuleNotice.svelte';
  import { page } from '$app/state';
  import { configuredLabel } from '$lib/v2/pipeline-config.js';
  import TaskReminder from '$lib/components/tasks/TaskReminder.svelte';
  import { asInternalPath } from '$lib/utils/paths.js';
  import { resolve } from '$app/paths';
  import { enhance } from '$app/forms';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import RecordTabs from '$lib/v2/components/RecordTabs.svelte';
  import Attachments from '$lib/v2/components/Attachments.svelte';
  import TaskAssignees from '$lib/components/tasks/TaskAssignees.svelte';
  import TaskParent from '$lib/components/tasks/TaskParent.svelte';
  import { daysSince } from '$lib/v2/format.js';
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
      ? new Date(value).toLocaleString(locale(), { dateStyle: 'medium', timeStyle: 'short' })
      : '—';
  function edit() {
    draft = {
      ...data.editor.form,
      contacts: [...data.editor.form.contacts],
      assigned_to: [...task.assigned_ids]
    };
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
  {#snippet crumb()}<a href={resolve('/tasks')}>{ui('Tasks')}</a><span
      >{configuredLabel(page.data.pipelineConfig, 'Task', task.status, task.status)}</span
    >{/snippet}
  {#snippet actions()}
    {#if editing}<button class="v2-btn v2-btn-primary" type="submit" form={formId} disabled={busy}
        >{busy ? ui('Saving…') : ui('Save')}</button
      ><button class="v2-btn" disabled={busy} onclick={() => (editing = false)}
        >{ui('Cancel')}</button
      >
    {:else}<RecordAction icon={Pencil} label={ui('Edit')} onclick={edit} />
      <RecordAction
        icon={StickyNote}
        label={ui('Add note')}
        onclick={() => recordTabs?.openNotes()}
      />
      <form method="POST" action="?/toggle" use:enhance>
        <input type="hidden" name="done" value={task.is_done ? 'false' : 'true'} /><RecordAction
          primary
          type="submit"
          icon={task.is_done ? RotateCcw : CircleCheck}
          label={ui(task.is_done ? 'Reopen' : 'Complete task')}
        />
      </form>
    {/if}
    {#if data.canDelete}<Dropdown.Root>
        <Dropdown.Trigger class="v2-btn">{ui('Actions')}<ChevronDown size={13} /></Dropdown.Trigger>
        <Dropdown.Content align="end"
          ><Dropdown.Item variant="destructive" onclick={() => deleteForm?.requestSubmit()}
            ><Trash2 size={14} />{ui('Delete')}</Dropdown.Item
          ></Dropdown.Content
        >
      </Dropdown.Root>{/if}
  {/snippet}
</PageHeader>
<StageRuleNotice issue={form?.stageRequirements} />
{#if form?.error && !form?.stageRequirements}<Notice message={ui(form.error)} />{/if}
<div class="task-profile">
  <main>
    <section class="panel description">
      {#if editing}<label
          >{ui('Task name')}<input
            class="v2-input"
            form={formId}
            name="title"
            required
            disabled={busy}
            bind:value={draft.title}
            maxlength="200"
          /></label
        >
        <label
          >{ui('Description')}<textarea
            class="v2-input"
            form={formId}
            name="description"
            disabled={busy}
            bind:value={draft.description}
            rows="5"></textarea></label
        >
      {:else}<h2>{ui('Description')}</h2>
        <p class="body">{task.description || 'No description.'}</p>{/if}
    </section>
    <section class="panel journal">
      <RecordTabs bind:this={recordTabs}>
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
              aria-label={ui('Add a note')}
              name="comment"
              rows="3"
              placeholder={ui('Write a note…')}
              bind:value={comment}></textarea>
            <button class="v2-btn" disabled={commentBusy || !comment.trim()}
              >{commentBusy ? ui('Saving…') : ui('Add note')}</button
            >
          </form>
          <div class="entries">
            {#each comments as entry (entry.id)}<article>
                <p class="body">{entry.body}</p>
                <small>{entry.by || '—'} · {exactDate(entry.at)}</small>
              </article>{:else}<p class="muted">{ui('No notes.')}</p>{/each}
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
              </article>{:else}<p class="muted">{ui('No activity yet.')}</p>{/each}
          </div>{/snippet}
      </RecordTabs>
    </section>
    <details class="panel attachments">
      <summary>{ui('Attachments')} <span>{files.length}</span></summary>
      <div><Attachments attachments={files} action="?/comment" /></div>
    </details>
  </main>
  <aside class="panel properties">
    <h2>{ui('Properties')}</h2>
    {#if editing}<form
        id={formId}
        method="POST"
        action="?/properties"
        use:recordValidation={form?.fieldErrors}
        use:enhance={save}
      >
        <input type="hidden" name="parent_kind_original" value={data.editor.form.parent_kind} />
        <input type="hidden" name="parent_id_original" value={data.editor.form.parent_id} />
        <fieldset disabled={busy}>
          <label
            >{ui('Status')}<select class="v2-input" name="status" bind:value={draft.status}
              >{#each ['New', 'In Progress', 'Completed'] as status (status)}<option
                  >{status}</option
                >{/each}</select
            ></label
          >
          <label
            >{ui('Priority')}<select class="v2-input" name="priority" bind:value={draft.priority}
              ><option value="">{ui('None')}</option
              >{#each ['Low', 'Medium', 'High'] as priority (priority)}<option>{priority}</option
                >{/each}</select
            ></label
          >
          <label
            >{ui('Due date')}<input
              class="v2-input"
              type="date"
              name="due_date"
              bind:value={draft.due_date}
            /></label
          >
          <TaskReminder bind:value={draft.reminder_days} />
          {#if canChooseOwner(page.data.permissions, 'tasks')}
            <TaskAssignees people={data.editor.owners} bind:selected={draft.assigned_to} />
          {/if}
          <TaskParent
            parents={data.editor.parents}
            bind:kind={draft.parent_kind}
            bind:selected={draft.parent_id}
            bind:contacts={draft.contacts}
          />
        </fieldset>
      </form>
    {:else}
      <PropertySummary
        target="Task"
        record={task}
        entries={[
          ['Name', task.title],
          ['Status', configuredLabel(page.data.pipelineConfig, 'Task', task.status, task.status)],
          ['Priority', task.priority],
          [
            'Due date',
            task.due_date ? longDate(task.due_date) + (late ? ' · Overdue' : '') : '—',
            'due_date'
          ],
          [
            'Reminder',
            task.reminder_days == null
              ? 'No reminder'
              : task.reminder_days === 0
                ? 'On due date'
                : `${task.reminder_days} days before`,
            'reminder_days'
          ],
          ['Assigned to', task.assigned_names.join(', ') || '—'],
          ['Last Activity', exactDate(task.last_activity_at)],
          ['Created', exactDate(task.created_at)]
        ]}
      />

      <section class="associations">
        <h2>{ui('Association')}</h2>
        {#if task.related}<a class="associated" href={resolve(asInternalPath(task.related.href))}
            ><small
              >{{ account: 'Company', deal: 'Deal', ticket: 'Ticket', lead: 'Lead' }[
                task.related.kind
              ] || task.related.kind}</small
            ><strong>{task.related.name}</strong></a
          >{/if}
        {#each data.contacts as contact (contact.id)}<a
            class="associated"
            href={resolve(`/contacts/${contact.id}`)}
            ><small>{ui('Contact')}</small><strong>{contact.name}</strong>{#if contact.email}<small
                >{contact.email}</small
              >{/if}</a
          >{/each}
        {#if !task.related && !data.contacts.length}<p class="muted">
            {ui('No association.')}
          </p>{/if}
      </section>
    {/if}

    {#if data.canDelete}<form
        bind:this={deleteForm}
        hidden
        method="POST"
        action="?/delete"
        use:enhance
      ></form>{/if}
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
    padding: var(--crm-space-4) var(--crm-space-6) var(--crm-space-5);
  }
  main {
    min-width: 0;
    overflow-y: auto;
    min-height: 0;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }
  .panel {
    min-width: 0;
    background: var(--v2-card);
    border-radius: var(--crm-radius-lg);
    padding: var(--crm-space-5);
  }
  h2 {
    font-size: var(--crm-text-sm);
    font-weight: 650;
    margin: 0 0 var(--crm-space-3);
  }
  .body {
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    margin: 0;
    font-size: var(--crm-text-sm);
    line-height: 1.6;
  }
  .description > .body {
    max-height: 240px;
    overflow: auto;
  }
  label {
    display: grid;
    gap: 7px;
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
    margin-bottom: var(--crm-space-4);
  }
  .v2-input {
    width: 100%;
  }
  .journal form .v2-btn {
    margin-top: var(--crm-space-2);
  }
  .entries {
    max-height: 340px;
    overflow: auto;
    margin-top: var(--crm-space-4);
  }
  .entries article {
    padding: var(--crm-space-3) 0;
    border-bottom: 1px solid var(--v2-line-soft);
  }
  small {
    display: block;
    margin-top: 6px;
    font-size: var(--crm-text-xs);
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
    margin-top: var(--crm-space-6);
  }
  .associated {
    display: block;
    background: var(--v2-paper);
    border-radius: var(--crm-radius-md);
    padding: 10px;
    color: var(--v2-ink);
    text-decoration: none;
    margin-top: 6px;
    overflow-wrap: anywhere;
    font-size: var(--crm-text-sm);
  }
  .associated small {
    margin: 0 0 var(--crm-space-1);
  }
  .attachments {
    padding: 0;
  }
  .attachments summary {
    padding: 15px var(--crm-space-5);
    cursor: pointer;
    font-size: var(--crm-text-sm);
    font-weight: 600;
  }
  .attachments summary span {
    color: var(--v2-slate);
    margin-left: var(--crm-space-2);
    font-size: var(--crm-text-xs);
  }
  .attachments > div {
    padding: 0 var(--crm-space-5) var(--crm-space-5);
  }
  .muted {
    color: var(--v2-slate);
    font-size: var(--crm-text-xs);
  }
  @container crm-workspace (max-width: 48rem) {
    .task-profile {
      grid-template-columns: 1fr;
      grid-template-rows: max-content max-content;
      overflow: auto;
      padding: var(--crm-space-3);
    }
    main,
    .properties {
      overflow: visible;
    }
  }
</style>
