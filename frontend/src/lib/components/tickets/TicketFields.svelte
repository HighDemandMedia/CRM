<script>
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();

  import RecordSection from '$lib/components/creation/RecordSection.svelte';
  import { page } from '$app/state';
  import { configuredStages } from '$lib/v2/pipeline-config.js';
  const statuses = $derived(
    configuredStages(
      page.data.pipelineConfig,
      'Case',
      defaultStatuses.map(([value, label]) => ({ value, label }))
    ).map((s) => [s.value, s.label])
  );
  import {
    statuses as defaultStatuses,
    priorities,
    categories,
    sources,
    localDateInput,
    dueDateEnd
  } from './options.js';
  import TaskAssignees from '$lib/components/tasks/TaskAssignees.svelte';
  import TicketAssociates from './TicketAssociates.svelte';
  let { values = $bindable(), options } = $props();
  let due = $state(localDateInput(values.due_at).slice(0, 10));
</script>

<RecordSection title={ui('Ticket details')}>
  <label
    >{ui('Title *')}<input
      class="v2-input"
      name="name"
      required
      bind:value={values.name}
      maxlength="64"
    /></label
  >
  <label
    >{ui('Description')}<textarea
      class="v2-input"
      name="description"
      bind:value={values.description}
      rows="4"></textarea></label
  >
</RecordSection>
<RecordSection title={ui('Assignment & status')}>
  <TaskAssignees
    people={options.owners}
    multiple={false}
    compact
    bind:selected={
      () => (values.assigned_to ? [values.assigned_to] : []),
      (ids) => (values.assigned_to = ids[0] ?? '')
    }
  />
  <TicketAssociates bind:values {options} />
  <label
    >{ui('Status')}<select class="v2-input" name="status" bind:value={values.status}
      >{#each statuses as [value, label]}<option {value}>{label}</option>{/each}</select
    ></label
  >
  <label
    >{ui('Priority')}<select class="v2-input" name="priority" bind:value={values.priority}
      ><option value="">{ui('None')}</option>{#each priorities as [value, label]}<option {value}
          >{label}</option
        >{/each}</select
    ></label
  >
  <label
    >{ui('Due date')}<input class="v2-input" type="date" bind:value={due} /><input
      type="hidden"
      name="due_at"
      value={dueDateEnd(due)}
    /></label
  >
  {#if values.status === 'Resolved'}<label
      >{ui('Resolution note *')}<textarea
        class="v2-input"
        name="resolution_note"
        required
        bind:value={values.resolution_note}
        rows="3"
        placeholder={ui('How was it resolved?')}></textarea></label
    >{/if}
  {#if values.status === 'Pending'}<label
      >{ui('Waiting on')}<select
        class="v2-input"
        name="waiting_reason"
        bind:value={values.waiting_reason}
        ><option value="">{ui('Select')}</option><option value="Customer">{ui('Customer')}</option
        ><option value="Internal">{ui('Internal')}</option></select
      ></label
    >{/if}
</RecordSection>
<RecordSection title={ui('Classification')}>
  <label
    >{ui('Category')}<select class="v2-input" name="category" bind:value={values.category}
      >{#each categories as value}<option>{value}</option>{/each}</select
    ></label
  >
  <label
    >{ui('Source')}<select class="v2-input" name="source" bind:value={values.source}
      >{#each sources as value}<option>{value}</option>{/each}</select
    ></label
  >
</RecordSection>

<style>
  label {
    display: grid;
    gap: 6px;
    font-size: var(--crm-text-xs);
    color: var(--v2-muted);
  }
  .v2-input {
    width: 100%;
    min-width: 0;
    color: var(--v2-ink);
  }
</style>
