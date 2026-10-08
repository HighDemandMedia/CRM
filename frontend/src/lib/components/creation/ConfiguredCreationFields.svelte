<script>
  import { untrack } from 'svelte';
  import { page } from '$app/state';
  import { useI18n } from '$lib/i18n/context.js';
  import StageRequirementField from '$lib/components/pipelines/StageRequirementField.svelte';
  import StageRuleNotice from '$lib/components/pipelines/StageRuleNotice.svelte';
  import { configuredStages } from '$lib/v2/pipeline-config.js';
  import AssociationPicker from './AssociationPicker.svelte';
  import ContactDuplicates from '$lib/components/contacts/ContactDuplicates.svelte';
  import TaskAssignees from '$lib/components/tasks/TaskAssignees.svelte';
  import TaskReminder from '$lib/components/tasks/TaskReminder.svelte';
  import TagPicker from '$lib/v2/components/TagPicker.svelte';
  import {
    inputKey,
    initialCreationValues,
    creationPayload,
    missingCreationFields
  } from './creation-values.js';
  const { ui } = useI18n();
  let { target, data, result = null, creatingTag = $bindable(false) } = $props();
  const schema = $derived(result?.creationSchema ?? data.creationSchema);
  const fields = $derived.by(() => {
    const configured = schema.selected;
    const requiredKeys = new Set([
      ...(result?.stageRequirements?.stage === (values?.stage ?? values?.status)
        ? (result.stageRequirements.fields ?? [])
        : []
      ).map((field) => field.key),
      ...(target === 'Case' && values?.status === 'Resolved' ? ['resolution_note'] : [])
    ]);
    const extra = (schema.fields ?? []).filter(
      (field) =>
        (requiredKeys.has(field.key) || result?.fieldErrors?.[field.key]) &&
        !configured.some((row) => row.key === field.key)
    );
    return [
      ...configured.map((field) => ({
        ...field,
        required: field.required || requiredKeys.has(field.key)
      })),
      ...extra.map((field) => ({ ...field, required: requiredKeys.has(field.key) }))
    ];
  });
  let values = $state(
    untrack(() => initialCreationValues(target, data.creationSchema.selected, data, result?.values))
  );
  $effect(() => {
    const defaults = initialCreationValues(target, fields, data, result?.values);
    for (const field of fields)
      if (values[field.key] === undefined) values[field.key] = defaults[field.key];
  });
  let payloadError = $state('');
  let submitted = $state(false);
  const missing = $derived(submitted ? missingCreationFields(fields, values) : []);
  const serialized = $derived.by(() => {
    try {
      return JSON.stringify(creationPayload(target, fields, values));
    } catch {
      return '';
    }
  });
  function records(field) {
    const source =
      field.key === 'account'
        ? (data.accounts ?? data.parents?.account)
        : field.key === 'contacts'
          ? (data.contacts ?? data.parents?.contact)
          : field.key === 'opportunity'
            ? data.parents?.opportunity
            : field.key === 'case'
              ? data.parents?.case
              : [];
    return (source ?? []).map((row) => ({
      ...row,
      id: String(row.id),
      type: field.key,
      label: field.label
    }));
  }
  function chosen(field) {
    const ids = field.multiple
      ? values[field.key] || []
      : values[field.key]
        ? [values[field.key]]
        : [];
    return ids.map(
      (id) =>
        records(field).find((row) => row.id === String(id)) ?? {
          id,
          type: field.key,
          name: ui('Selected record'),
          label: field.label
        }
    );
  }
  function select(field, record) {
    if (target === 'Task' && ['account', 'opportunity', 'case'].includes(field.key)) {
      for (const key of ['account', 'opportunity', 'case']) if (key !== field.key) values[key] = '';
    }
    values[field.key] = field.multiple ? [...(values[field.key] || []), record.id] : record.id;
  }
  function remove(field, record) {
    values[field.key] = field.multiple ? values[field.key].filter((id) => id !== record.id) : '';
  }
  function descriptor(field) {
    let options = field.options;
    if (['status', 'stage'].includes(field.key))
      options = configuredStages(page.data.pipelineConfig, target, options);
    if (field.key === 'source' && target === 'Contact') options = data.sources ?? options;
    if (field.key === 'industry') options = data.industries ?? options;
    return {
      ...field,
      label: field.custom ? field.label : ui(field.label),
      options,
      name: field.custom ? field.key : inputKey(target, field.key),
      // The domain accepts example.com as well as full URLs.
      field_type:
        field.key === 'website' ? 'text' : field.key === 'country' ? 'dropdown' : field.field_type
    };
  }
  function guard(node) {
    function check(event) {
      submitted = true;
      const absent = missingCreationFields(fields, values);
      if (absent.length) {
        event.preventDefault();
        event.stopImmediatePropagation();
        node
          .querySelector(
            `[data-field="${absent[0].key}"] input, [data-field="${absent[0].key}"] select, [data-field="${absent[0].key}"] button`
          )
          ?.focus();
      }
      payloadError = serialized ? '' : ui('Check the format of the property values.');
      if (!serialized) {
        event.preventDefault();
        event.stopImmediatePropagation();
      }
    }
    const form = node.closest('form');
    form?.addEventListener('submit', check, true);
    return { destroy: () => form?.removeEventListener('submit', check, true) };
  }
</script>

<div class="configured-fields" use:guard>
  <StageRuleNotice issue={result?.stageRequirements} />
  <input type="hidden" name="_creation_values" value={serialized} />
  {#if payloadError}<p class="v2-error" role="alert">{payloadError}</p>{/if}
  {#each fields as field, index (field.key)}
    {@const key = inputKey(target, field.key)}
    {#if index === 0 || fields[index - 1].section !== field.section}
      <h3>{ui(field.section)}</h3>
    {/if}
    <div class="creation-field" data-field={field.key}>
      {#if field.key === 'assigned_to'}
        <TaskAssignees
          people={data.owners ?? []}
          multiple={target === 'Task'}
          compact
          bind:selected={
            () =>
              target === 'Task'
                ? values[field.key] || []
                : values[field.key]
                  ? [values[field.key]]
                  : [],
            (ids) => (values[field.key] = target === 'Task' ? ids : (ids[0] ?? ''))
          }
        />
        {#if field.required}<small>{ui('Required')}</small>{/if}
      {:else if field.relation && field.key !== 'tags'}
        <AssociationPicker
          records={records(field)}
          chosen={chosen(field)}
          label={field.label}
          onselect={(record) => select(field, record)}
          onremove={(record) => remove(field, record)}
        />
        {#if field.required}<small>{ui('Required')}</small>{/if}
      {:else if field.key === 'tags'}
        <span class="field-label">{ui('Tags')}{field.required ? ' *' : ''}</span>
        <TagPicker
          options={data.tagOptions ?? []}
          canCreate={data.canCreateTags}
          bind:selected={values[field.key]}
          bind:creating={creatingTag}
        />
      {:else if field.key === 'reminder_days'}
        <TaskReminder bind:value={values[field.key]} />
        {#if field.required}<small>{ui('Required')}</small>{/if}
      {:else}
        <StageRequirementField
          field={descriptor(field)}
          required={field.required}
          bind:value={values[field.key]}
        />
      {/if}
      {#if missing.some((row) => row.key === field.key)}<p class="v2-error" role="alert">
          {ui('This field is required.')}
        </p>{/if}
      {#if result?.fieldErrors?.[key] || result?.fieldErrors?.[field.key]}
        <p class="v2-error" role="alert">
          {result.fieldErrors[key] || result.fieldErrors[field.key]}
        </p>
      {/if}
    </div>
  {/each}
  {#if target === 'Contact'}<ContactDuplicates
      name={values.first_name || ''}
      email={values.email || ''}
      phone={values.phone || ''}
    />{/if}
</div>

<style>
  .configured-fields {
    display: grid;
    gap: var(--crm-space-4);
  }
  h3 {
    font-size: var(--crm-text-sm);
    margin: var(--crm-space-3) 0 0;
    padding-bottom: var(--crm-space-2);
    border-bottom: 1px solid var(--crm-border);
  }
  .creation-field {
    min-width: 0;
  }
  .creation-field :global(.requirement-field),
  .creation-field :global(.parent-picker) {
    margin-bottom: 0;
  }
  .field-label {
    display: block;
    font-size: var(--crm-text-sm);
    margin-bottom: var(--crm-space-2);
  }
  small {
    color: var(--crm-text-muted);
  }
</style>
