<script>
  import { resolve } from '$app/paths';

  import {
    fieldInputType,
    fieldInputStep,
    propertyInputAttributes,
    propertyPlaceholder
  } from '$lib/v2/custom-field-input.js';
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();

  import { countryOptions } from '$lib/constants/countries.js';
  import { onMount } from 'svelte';
  import TagPicker from '$lib/v2/components/TagPicker.svelte';
  /** @type {{field:any,target?:string,value?:any,required?:boolean}} */
  let { field, target = '', value = $bindable(''), required = true } = $props();
  let options = $state([]),
    search = $state(''),
    error = $state(''),
    loading = $state(false);
  let multiple = $derived(
    field.multiple === true || field.multiple === 'True' || field.field_type === 'multi_select'
  );
  let sequence = 0,
    timer;
  async function load() {
    const current = ++sequence;
    loading = true;
    error = '';
    try {
      const response = await fetch(
        `/api/stage-transition?target=${encodeURIComponent(target)}&relation=${encodeURIComponent(field.relation)}&q=${encodeURIComponent(search)}`
      );
      const body = await response.json();
      if (current !== sequence) return;
      if (!response.ok) throw new Error(body.error);
      options = body.options;
    } catch (e) {
      if (current === sequence) error = e.message;
    } finally {
      if (current === sequence) loading = false;
    }
  }
  onMount(() => {
    if (field.relation) void load();
    return () => {
      clearTimeout(timer);
      sequence++;
    };
  });
  let choices = $derived(
    field.key === 'country'
      ? countryOptions(value)
      : field.relation
        ? options
        : (field.options || []).map((o) => (typeof o === 'string' ? { value: o, label: o } : o))
  );
  let kind = $derived(
    field.field_type === 'datetime' ? 'datetime-local' : fieldInputType(field.field_type)
  );
  let constraints = $derived({
    ...propertyInputAttributes(field.field_type),
    ...(field.max_length != null ? { maxlength: field.max_length } : {}),
    ...(field.min != null ? { min: field.min } : {}),
    ...(field.max != null ? { max: field.max } : {})
  });
</script>

<div class="requirement-field" data-property-control>
  {#if field.is_read_only === true || field.is_read_only === 'True'}
    <strong>{field.label}</strong>
    <p>
      {ui('Schedule the appointment in')} <a href={resolve('/calendar')}>{ui('Calendar')}</a>{ui(
        ', then return to change the stage.'
      )}
    </p>
  {:else}
    <label for={`requirement-${field.key}`}
      >{field.label}
      {#if required}<span>*</span>{/if}</label
    >
    {#if field.relation && field.relation !== 'Tags'}<input
        class="v2-input"
        aria-label={`Search ${field.label}`}
        placeholder={ui('Search by name…')}
        bind:value={search}
        oninput={() => {
          clearTimeout(timer);
          timer = setTimeout(load, 250);
        }}
      />{/if}
    {#if field.relation === 'Tags'}
      <TagPicker
        inputId={`requirement-${field.key}`}
        options={options.map((option) => ({
          id: String(option.value),
          name: option.label,
          color: option.color
        }))}
        bind:selected={value}
        onSearch={(query) => {
          search = query;
          clearTimeout(timer);
          timer = setTimeout(load, 250);
        }}
      />
    {:else if field.key === 'pages'}
      {#each value || [] as entry, index (entry)}<div class="page-link">
          <input
            class="v2-input"
            aria-label={ui('Page name')}
            placeholder={ui('Page name')}
            bind:value={entry.name}
            {required}
          /><input
            class="v2-input"
            type="url"
            aria-label={ui('Page URL')}
            placeholder="https://…"
            bind:value={entry.url}
            {required}
          /><button
            class="v2-btn"
            type="button"
            aria-label={ui('Remove page')}
            onclick={() => (value = value.filter((_, i) => i !== index))}>×</button
          >
        </div>{/each}
      <button
        type="button"
        class="v2-btn"
        onclick={() => (value = [...(value || []), { name: '', url: '' }])}>{ui('Add page')}</button
      >
    {:else if field.relation || ['dropdown', 'multi_select'].includes(field.field_type)}
      {#if multiple}<div class="options">
          {#each choices as option (option.value)}<label
              ><input
                type="checkbox"
                name={field.name ?? field.key}
                data-property-required={required ? 'true' : undefined}
                value={String(option.value)}
                bind:group={value}
              />{option.label}</label
            >{/each}
        </div>
      {:else}<select
          id={`requirement-${field.key}`}
          class="v2-input"
          name={field.name ?? field.key}
          bind:value
          {required}
          ><option value="">{ui('Select…')}</option>{#each choices as option (option.value)}<option
              value={String(option.value)}>{option.label}</option
            >{/each}</select
        >{/if}
    {:else if field.field_type === 'checkbox'}<select
        id={`requirement-${field.key}`}
        class="v2-input"
        name={field.name ?? field.key}
        bind:value
        {required}
        ><option value="">{ui('Select…')}</option><option value="true">{ui('Yes')}</option><option
          value="false">{ui('No')}</option
        ></select
      >
    {:else if ['textarea', 'list'].includes(field.field_type)}<textarea
        id={`requirement-${field.key}`}
        class="v2-input"
        name={field.name ?? field.key}
        data-property-type={field.field_type}
        {...constraints}
        bind:value
        {required}
        rows="3"
        placeholder={ui(propertyPlaceholder(field, target))}></textarea>
    {:else}<input
        id={`requirement-${field.key}`}
        class="v2-input"
        type={kind}
        name={field.name ?? field.key}
        data-property-type={field.field_type}
        {...constraints}
        bind:value
        {required}
        placeholder={ui(propertyPlaceholder(field, target))}
        step={fieldInputStep(field.field_type)}
      />{/if}
    {#if loading}<small>{ui('Loading options…')}</small>{:else if error}<small role="alert"
        >{ui(error)}</small
      >{/if}
  {/if}
</div>

<style>
  .page-link {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: var(--crm-space-2);
  }
  .page-link input:first-child {
    grid-column: 1/-1;
  }
  .requirement-field {
    display: grid;
    gap: var(--crm-space-2);
    margin-bottom: var(--crm-space-6);
    font-size: var(--crm-text-sm);
  }
  label {
    font-weight: 500;
  }
  span {
    color: var(--crm-warning);
  }
  .options {
    display: grid;
    gap: 10px;
    max-height: 200px;
    overflow: auto;
  }
  .options label {
    display: flex;
    align-items: center;
    gap: var(--crm-space-2);
  }
  small {
    color: var(--v2-slate);
  }
</style>
