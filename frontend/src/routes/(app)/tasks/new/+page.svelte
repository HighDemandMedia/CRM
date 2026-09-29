<script>
  import RecordSection from '$lib/components/creation/RecordSection.svelte';
  import { recordValidation } from '$lib/components/creation/validation.js';
  import { page } from '$app/state';
  import { configuredStages } from '$lib/v2/pipeline-config.js';
  const statusOptions = $derived(
    configuredStages(
      page.data.pipelineConfig,
      'Task',
      ['New', 'In Progress', 'Completed'].map((value) => ({ value, label: value }))
    )
  );
  import TaskReminder from '$lib/components/tasks/TaskReminder.svelte';
  import { creationEnhance } from '$lib/components/creation/enhance.js';
  const enhance = creationEnhance();
  import TaskAssignees from '$lib/components/tasks/TaskAssignees.svelte';
  import TaskParent from '$lib/components/tasks/TaskParent.svelte';
  import { resolve } from '$app/paths';
  /**
   * A new task.
   *
   * "Attached to" is one question, not four. The model allows exactly one
   * parent and now enforces it on every path, so a form with four separate
   * pickers would let somebody fill two and learn about the rule from a 400.
   * Pick the kind, then pick the record.
   */
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import { untrack } from 'svelte';
  import { ChevronRight } from '@lucide/svelte';

  /** @type {{ data: any, form: any }} */
  let { data, form } = $props();

  let assignees = $state(untrack(() => [...(form?.values?.assigned_to ?? [])]));
  let reminder = $state(untrack(() => String(form?.values?.reminder_days ?? '')));
  let values = $derived(form?.values ?? {});
  let kind = $state(untrack(() => form?.values?.parent_kind ?? ''));
  let selected = $state(untrack(() => form?.values?.[form?.values?.parent_kind] ?? ''));
</script>

<PageHeader title="New task" record center width="62ch">
  {#snippet crumb()}
    <a href={resolve('/tasks')}>Tasks</a>
    <ChevronRight size={12} />
    <span>New</span>
  {/snippet}
</PageHeader>

<div class="v2-scroll">
  <form
    use:recordValidation={form?.fieldErrors}
    method="POST"
    action="?/create"
    use:enhance
    class="v2-pad"
    style="padding-top:18px;padding-bottom:36px;max-width:62ch;margin-left:auto;margin-right:auto"
  >
    {#if form?.error}
      <p style="color:var(--v2-rust);font-size:12.5px;margin:0 0 14px" role="alert">{form.error}</p>
    {/if}

    <RecordSection title="Task details">
      <label class="v2-field">
        <span class="v2-label">Title *</span>
        <input
          class="v2-input"
          name="title"
          required
          maxlength="200"
          value={values.title ?? ''}
          placeholder="Task title"
        />
      </label>
      <TaskParent parents={data.parents} bind:kind bind:selected />
    </RecordSection>
    <RecordSection title="Assignment & schedule">
      <TaskAssignees people={data.owners} bind:selected={assignees} />
      <div style="display:flex;gap:12px;flex-wrap:wrap">
        <label class="v2-field" style="flex:1;min-width:150px">
          <span class="v2-label">Priority</span>
          <select class="v2-input" name="priority" value={values.priority ?? 'Medium'}
            ><option value="">None</option>
            <option value="Low">Low</option>
            <option value="Medium">Medium</option>
            <option value="High">High</option>
          </select>
        </label>
        <label class="v2-field" style="flex:1;min-width:150px">
          <span class="v2-label">Status</span>
          <select class="v2-input" name="status" value={values.status ?? 'New'}>
            {#each statusOptions as option}<option value={option.value}>{option.label}</option
              >{/each}
          </select>
        </label>
        <label class="v2-field" style="flex:1;min-width:150px">
          <span class="v2-label">Due</span>
          <input class="v2-input" type="date" name="due_date" value={values.due_date ?? ''} />
        </label>
      </div>
      <TaskReminder bind:value={reminder} />
    </RecordSection>
    <RecordSection title="Additional details" collapsible>
      <label class="v2-field">
        <span class="v2-label">Description</span>
        <textarea class="v2-input" name="description" rows="4" placeholder="Add details…"
          >{values.description ?? ''}</textarea
        >
      </label>
    </RecordSection>

    <div style="display:flex;gap:9px;margin-top:6px">
      <button class="v2-btn v2-btn-primary" type="submit">Create task</button>
      <a class="v2-btn" href={resolve('/tasks')}>Cancel</a>
    </div>
  </form>
</div>

<style>
  form.v2-pad {
    width: 100%;
    background: var(--v2-card);
    border-radius: 12px;
    margin-top: 16px;
  }
</style>
