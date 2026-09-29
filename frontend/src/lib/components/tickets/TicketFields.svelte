<script>
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
  let { values = $bindable(), options, showAssociates = true } = $props();
  let due = $state(localDateInput(values.due_at).slice(0, 10));
</script>

<RecordSection title="Ticket details">
  <label
    >Title *<input
      class="v2-input"
      name="name"
      required
      bind:value={values.name}
      maxlength="64"
    /></label
  >
  <label
    >Description<textarea
      class="v2-input"
      name="description"
      bind:value={values.description}
      rows="4"></textarea></label
  >
</RecordSection>
<RecordSection title="Assignment & status">
  <TaskAssignees
    people={options.owners}
    multiple={false}
    compact
    bind:selected={
      () => (values.assigned_to ? [values.assigned_to] : []),
      (ids) => (values.assigned_to = ids[0] ?? '')
    }
  />
  <label
    >Status<select class="v2-input" name="status" bind:value={values.status}
      >{#each statuses as [value, label]}<option {value}>{label}</option>{/each}</select
    ></label
  >
  <label
    >Priority<select class="v2-input" name="priority" bind:value={values.priority}
      ><option value="">None</option>{#each priorities as [value, label]}<option {value}
          >{label}</option
        >{/each}</select
    ></label
  >
  <label
    >Due date<input class="v2-input" type="date" bind:value={due} /><input
      type="hidden"
      name="due_at"
      value={dueDateEnd(due)}
    /></label
  >
  {#if values.status === 'Resolved'}<label
      >Resolution note *<textarea
        class="v2-input"
        name="resolution_note"
        required
        bind:value={values.resolution_note}
        rows="3"
        placeholder="How was it resolved?"></textarea></label
    >{/if}
  {#if values.status === 'Pending'}<label
      >Waiting on<select class="v2-input" name="waiting_reason" bind:value={values.waiting_reason}
        ><option value="">Select</option><option>Customer</option><option>Internal</option></select
      ></label
    >{/if}
</RecordSection>
<RecordSection title="Classification">
  <label
    >Category<select class="v2-input" name="category" bind:value={values.category}
      >{#each categories as value}<option>{value}</option>{/each}</select
    ></label
  >
  <label
    >Source<select class="v2-input" name="source" bind:value={values.source}
      >{#each sources as value}<option>{value}</option>{/each}</select
    ></label
  >
</RecordSection>
<RecordSection title="Associated records">
  {#if showAssociates}<TicketAssociates bind:values {options} />{:else}
    <input type="hidden" name="account" value={values.account ?? ''} />
    {#each values.contacts ?? [] as contact}<input
        type="hidden"
        name="contacts"
        value={contact}
      />{/each}
  {/if}
</RecordSection>

<style>
  label {
    display: grid;
    gap: 6px;
    font-size: 12px;
    color: var(--v2-muted);
  }
  .v2-input {
    width: 100%;
    min-width: 0;
    color: var(--v2-ink);
  }
</style>
