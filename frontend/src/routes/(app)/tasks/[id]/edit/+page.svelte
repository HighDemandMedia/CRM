<script>
  import StageRuleNotice from "$lib/components/pipelines/StageRuleNotice.svelte";
  import { page } from "$app/state";
  import { configuredStages } from "$lib/v2/pipeline-config.js";
  const statusOptions = $derived(configuredStages(page.data.pipelineConfig, "Task", ["New", "In Progress", "Completed"].map(value => ({value,label:value}))));
  import TaskReminder from '$lib/components/tasks/TaskReminder.svelte';
  import TaskAssignees from '$lib/components/tasks/TaskAssignees.svelte';
  import TaskParent from '$lib/components/tasks/TaskParent.svelte';
  import { resolve } from '$app/paths';
  /**
   * Editing a task.
   *
   * Same single "attached to" question as the new-task form, plus the two
   * hidden originals that let the save tell a real change from a re-send.
   * See the action for why that distinction matters here.
   */
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import { creationEnhance } from '$lib/components/creation/enhance.js';
  const enhance = creationEnhance();
  import { untrack } from 'svelte';
  import { ChevronRight } from '@lucide/svelte';

  /** @type {{ data: any, form: any }} */
  let { data, form } = $props();

  let assignees = $state(untrack(() => [...(form?.values?.assigned_to ?? data.task.assigned_ids)]));
  let reminder = $state(
    untrack(() => String(form?.values?.reminder_days ?? data.form.reminder_days ?? ''))
  );
  let values = $derived(form?.values ?? data.form);
  let kind = $state(untrack(() => form?.values?.parent_kind ?? data.form.parent_kind ?? ''));
  let selected = $state(untrack(() => form?.values?.parent_id ?? data.form.parent_id ?? ''));
  let currentId = $derived(form?.values?.parent_id ?? data.form.parent_id ?? '');
</script>

<PageHeader title="Edit task" record center width="62ch">
  {#snippet crumb()}
    <a href={resolve('/tasks')}>Tasks</a>
    <ChevronRight size={12} />
    <a href={resolve(`/tasks/${data.task.id}`)}>{data.task.title}</a>
    <ChevronRight size={12} />
    <span>Edit</span>
  {/snippet}
</PageHeader>

<div class="v2-scroll">
  <form
    method="POST"
    action="?/save"
    use:enhance
    class="v2-pad"
    style="padding-top:18px;padding-bottom:36px;max-width:62ch;margin-left:auto;margin-right:auto"
  >
    <StageRuleNotice issue={form?.stageRequirements}/>
{#if form?.error && !form?.stageRequirements}
      <p style="color:var(--v2-rust);font-size:12.5px;margin:0 0 14px" role="alert">{form.error}</p>
    {/if}

    <input type="hidden" name="parent_kind_original" value={data.form.parent_kind} />
    <input type="hidden" name="parent_id_original" value={data.form.parent_id} />

    <label class="v2-field">
      <span class="v2-label">Task</span>
      <input class="v2-input" name="title" required maxlength="200" value={values.title ?? ''} />
    </label>

    <div style="display:flex;gap:12px;flex-wrap:wrap">
      <label class="v2-field" style="flex:1;min-width:150px">
        <span class="v2-label">Priority</span>
        <select class="v2-input" name="priority" value={values.priority ?? 'Medium'}><option value="">None</option>
          <option value="Low">Low</option>
          <option value="Medium">Medium</option>
          <option value="High">High</option>
        </select>
      </label>
      <label class="v2-field" style="flex:1;min-width:150px">
        <span class="v2-label">Status</span>
        <select class="v2-input" name="status" value={values.status ?? 'New'}>
          {#each statusOptions as option}<option value={option.value}>{option.label}</option>{/each}
        </select>
      </label>
      <label class="v2-field" style="flex:1;min-width:150px">
        <span class="v2-label">Due</span>
        <input class="v2-input" type="date" name="due_date" value={values.due_date ?? ''} />
      </label>
    </div>

    <TaskReminder bind:value={reminder} />

    <TaskParent parents={data.parents} bind:kind bind:selected />

    <TaskAssignees people={data.owners} bind:selected={assignees} />

    <label class="v2-field">
      <span class="v2-label">Description</span>
      <textarea class="v2-input" name="description" rows="4">{values.description ?? ''}</textarea>
    </label>

    <div style="display:flex;gap:9px;margin-top:6px">
      <button class="v2-btn v2-btn-primary" type="submit">Save</button>
      <a class="v2-btn" href={resolve(`/tasks/${data.task.id}`)}>Cancel</a>
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
