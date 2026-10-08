<script>
  import ConfiguredCreationFields from '$lib/components/creation/ConfiguredCreationFields.svelte';
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();

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
  let contacts = $state(untrack(() => [...(form?.values?.contacts ?? [])]));
  let kind = $state(untrack(() => form?.values?.parent_kind ?? ''));
  let selected = $state(untrack(() => form?.values?.[form?.values?.parent_kind] ?? ''));
</script>

<PageHeader title={ui('New task')} record center width="62ch">
  {#snippet crumb()}
    <a href={resolve('/tasks')}>{ui('Tasks')}</a>
    <ChevronRight size={12} />
    <span>{ui('New')}</span>
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
      <p style="color:var(--v2-rust);font-size:var(--crm-text-sm);margin:0 0 14px" role="alert">
        {ui(form.error)}
      </p>
    {/if}

    {#if data.creationSchema}<ConfiguredCreationFields target="Task" {data} result={form} />{:else}
      <RecordSection title={ui('Task details')}>
        <label class="v2-field">
          <span class="v2-label">{ui('Title *')}</span>
          <input
            class="v2-input"
            name="title"
            required
            maxlength="200"
            value={values.title ?? ''}
            placeholder={ui('Task title')}
          />
        </label>
        <TaskParent parents={data.parents} bind:kind bind:selected bind:contacts />
      </RecordSection>
      <RecordSection title={ui('Assignment & schedule')}>
        <TaskAssignees people={data.owners} bind:selected={assignees} />
        <div style="display:flex;gap:12px;flex-wrap:wrap">
          <label class="v2-field" style="flex:1;min-width:150px">
            <span class="v2-label">{ui('Priority')}</span>
            <select class="v2-input" name="priority" value={values.priority ?? 'Medium'}
              ><option value="">{ui('None')}</option>
              <option value="Low">{ui('Low')}</option>
              <option value="Medium">{ui('Medium')}</option>
              <option value="High">{ui('High')}</option>
            </select>
          </label>
          <label class="v2-field" style="flex:1;min-width:150px">
            <span class="v2-label">{ui('Status')}</span>
            <select class="v2-input" name="status" value={values.status ?? 'New'}>
              {#each statusOptions as option}<option value={option.value}>{option.label}</option
                >{/each}
            </select>
          </label>
          <label class="v2-field" style="flex:1;min-width:150px">
            <span class="v2-label">{ui('Due')}</span>
            <input class="v2-input" type="date" name="due_date" value={values.due_date ?? ''} />
          </label>
        </div>
        <TaskReminder bind:value={reminder} />
      </RecordSection>
      <RecordSection title={ui('Additional details')} collapsible>
        <label class="v2-field">
          <span class="v2-label">{ui('Description')}</span>
          <textarea class="v2-input" name="description" rows="4" placeholder={ui('Add details…')}
            >{values.description ?? ''}</textarea
          >
        </label>
      </RecordSection>
    {/if}
    <div style="display:flex;gap:9px;margin-top:6px">
      <button class="v2-btn v2-btn-primary" type="submit">{ui('Create task')}</button>
      <a class="v2-btn" href={resolve('/tasks')}>{ui('Cancel')}</a>
    </div>
  </form>
</div>

<style>
  form.v2-pad {
    width: 100%;
    background: var(--v2-card);
    border-radius: var(--crm-radius-lg);
    margin-top: var(--crm-space-4);
  }
</style>
