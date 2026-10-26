<script>
  import RecordEditActions from '$lib/components/RecordEditActions.svelte';
  import { toast } from 'svelte-sonner';
  import PhoneInput from '$lib/components/PhoneInput.svelte';
  import Notice from '$lib/components/Notice.svelte';
  import { page } from '$app/state';
  import { canChooseOwner } from '$lib/v2/permissions.js';
  import ConfiguredCreationFields from '$lib/components/creation/ConfiguredCreationFields.svelte';
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();

  import CountrySelect from '$lib/components/CountrySelect.svelte';
  import { recordValidation } from '$lib/components/creation/validation.js';
  import RecordSection from '$lib/components/creation/RecordSection.svelte';
  import ContactDuplicates from './ContactDuplicates.svelte';
  import StageRuleNotice from '$lib/components/pipelines/StageRuleNotice.svelte';
  import { creationEnhance } from '$lib/components/creation/enhance.js';
  const enhance = creationEnhance();
  import LanguageSelect from '$lib/v2/components/LanguageSelect.svelte';
  import { deserialize } from '$app/forms';
  import { untrack, onMount, onDestroy } from 'svelte';
  import TagPicker from '$lib/v2/components/TagPicker.svelte';
  import { contactChanges } from '$lib/v2/contact-autosave.js';
  import { resolve } from '$app/paths';

  /** @type {{data:any, result?:any, editing?:boolean, autoSave?:boolean, inline?:boolean, onCancel?:()=>void, onSaved?:()=>Promise<void>}} */
  let {
    data,
    result = null,
    editing = false,
    autoSave = false,
    inline = false,
    onCancel = () => {},
    onSaved = async () => {}
  } = $props();
  let values = $state(
    untrack(() => ({
      name: '',
      phone: '',
      email: '',
      source: '',
      stage: 'LEAD',
      country: '',
      address_line: '',
      language: '',
      city: '',
      postcode: '',
      state: '',
      preferred_communication_channel: '',
      description: '',
      assigned_to: '',
      ...(data.form ?? {}),
      ...(result?.values ?? {})
    }))
  );
  let creatingTag = $state(false);
  let selectedTags = $state(
    /** @type {string[]} */ (
      untrack(() => (result?.values?.tags ?? data.form?.tags ?? []).map(String))
    )
  );
  const editBaseline = untrack(() => JSON.stringify({ ...values, tags: selectedTags }));
  const editDirty = $derived(JSON.stringify({ ...values, tags: selectedTags }) !== editBaseline);
  let autoReady = $state(false);
  let autoStatus = $state('');
  let autoFieldErrors = $state({});
  let formElement;
  let autoError = $state('');
  let autoIssue = $state(null);
  let autoBusy = false;
  /** @type {Record<string, any>} */
  let baseline = {};
  /** @type {Record<string, any> | null} */
  let queued = null;
  /** @type {ReturnType<typeof setTimeout> | undefined} */
  let autoTimer;
  async function flushAutoSave() {
    clearTimeout(autoTimer);
    if (autoBusy || !queued) return;
    const snapshot = queued;
    queued = null;
    const changes = contactChanges(baseline, snapshot);
    if (!Object.keys(changes).length) return;
    if (formElement && !formElement.checkValidity()) return;
    autoFieldErrors = {};
    autoBusy = true;
    autoStatus = 'Saving…';
    autoError = '';
    autoIssue = null;
    let saved = false;
    try {
      const body = new FormData();
      body.set('changes', JSON.stringify(changes));
      const response = await fetch('?/saveFields', {
        method: 'POST',
        body,
        headers: { 'x-sveltekit-action': 'true' }
      });
      const result = deserialize(await response.text());
      if (result.type !== 'success') {
        autoFieldErrors = result.type === 'failure' ? (result.data?.fieldErrors ?? {}) : {};
        autoIssue = result.type === 'failure' ? result.data?.stageRequirements : null;
        autoError =
          result.type === 'failure'
            ? String(result.data?.error ?? 'Could not save changes.')
            : 'Could not save changes. Check your session.';
        autoStatus = '';
        return;
      }
      baseline = snapshot;
      saved = true;
      autoStatus = 'Saved';
      await onSaved();
    } catch {
      autoError = saved
        ? 'Saved, but the profile could not refresh.'
        : 'Could not confirm the save. Your changes remain here.';
      autoStatus = '';
    } finally {
      autoBusy = false;
      if (queued) void flushAutoSave();
    }
  }
  $effect(() => {
    if (!autoSave || !autoReady) return;
    const snapshot = JSON.parse(JSON.stringify({ ...values, tags: selectedTags }));
    untrack(() => {
      queued = snapshot;
      clearTimeout(autoTimer);
      autoTimer = setTimeout(flushAutoSave, 700);
    });
  });
  onDestroy(() => clearTimeout(autoTimer));
  onMount(() => {
    baseline = JSON.parse(JSON.stringify({ ...values, tags: selectedTags }));
    autoReady = true;
  });
  let saving = $state(false);
  const textFields = /** @type {const} */ ([
    { key: 'name', label: 'Name', required: true, type: 'text', max: 255, autocomplete: 'name' },
    {
      key: 'email',
      label: 'Email',
      required: false,
      type: 'email',
      max: 254,
      autocomplete: 'email'
    },
    { key: 'phone', label: 'Phone', required: false, type: 'tel', max: 25, autocomplete: 'tel' }
  ]);
  const addressFields = /** @type {const} */ ([
    { key: 'address_line', label: 'Address', autocomplete: 'street-address', max: 255 },
    { key: 'city', label: 'City', autocomplete: 'address-level2', max: 255 },
    { key: 'state', label: 'State / region', autocomplete: 'address-level1', max: 255 },
    { key: 'postcode', label: 'Postal code', autocomplete: 'postal-code', max: 64 }
  ]);
</script>

{#snippet formActions()}
  <div class="actions" class:record-edit-actions={inline && editing}>
    <button class="v2-btn v2-btn-primary" type="submit" disabled={saving || creatingTag}>
      {saving ? ui('Saving…') : editing ? ui('Save contact') : ui('Create contact')}
    </button>
    {#if inline}<button
        class="v2-btn"
        type="button"
        disabled={saving || creatingTag}
        onclick={onCancel}>{ui('Cancel')}</button
      >{:else}<a
        class="v2-btn"
        href={resolve(editing ? `/contacts/${data.contact.id}` : '/contacts')}>{ui('Cancel')}</a
      >{/if}
  </div>
{/snippet}

<form
  bind:this={formElement}
  use:recordValidation={result?.fieldErrors ?? autoFieldErrors}
  class="v2-form"
  class:auto-save={autoSave}
  class:inline-edit={inline}
  aria-busy={saving}
  onfocusout={() => {
    if (autoSave && autoReady) setTimeout(flushAutoSave, 0);
  }}
  onsubmit={(event) => {
    if (autoSave) {
      event.preventDefault();
      void flushAutoSave();
    }
  }}
  method="POST"
  action={editing ? '?/save' : '?/create'}
  use:enhance={({ cancel }) => {
    if (saving || creatingTag) {
      cancel();
      return;
    }
    if (autoSave) {
      cancel();
      void flushAutoSave();
      return;
    }
    saving = true;
    return async ({ result: actionResult, update }) => {
      try {
        await update({ reset: false });
        if (inline && actionResult.type === 'success') {
          toast.success(ui('Changes saved.'));
          await onSaved();
        }
      } finally {
        saving = false;
      }
    };
  }}
>
  {#if !autoSave && inline && editing}
    <RecordEditActions dirty={editDirty} {saving} blocked={creatingTag} oncancel={onCancel} />
  {/if}
  <fieldset class="record-form-fields" disabled={saving}>
    <StageRuleNotice issue={autoIssue || result?.stageRequirements} />
    {#if result?.error && !result?.stageRequirements}<Notice message={result.error} />{/if}
    {#if autoSave}
      <div class="save-status" role="status">{autoStatus}</div>
      {#if autoError && !autoIssue}<Notice message={autoError}>
          {#snippet actions()}
            <button
              type="button"
              class="v2-btn"
              onclick={() => {
                queued = JSON.parse(JSON.stringify({ ...values, tags: selectedTags }));
                void flushAutoSave();
              }}>{ui('Retry')}</button
            >
          {/snippet}</Notice
        >{/if}
    {/if}
    {#if !editing && data.creationSchema}
      <ConfiguredCreationFields target="Contact" {data} {result} bind:creatingTag />
    {:else}
      <RecordSection title={ui('Contact details')}>
        {#each textFields as field (field.key)}
          <div class="v2-field">
            <label for={'contact-' + field.key}>{ui(field.label)}{field.required ? ' *' : ''}</label
            >
            {#if field.type === 'tel'}<PhoneInput
                id={'contact-' + field.key}
                name={field.key}
                bind:value={values[field.key]}
                required={field.required}
              />{:else}<input
                id={'contact-' + field.key}
                class="v2-input"
                name={field.key}
                type={field.type}
                required={field.required}
                maxlength={field.max}
                autocomplete={field.autocomplete}
                bind:value={values[field.key]}
              />{/if}
          </div>
        {/each}
        <ContactDuplicates
          name={values.name || ''}
          email={values.email || ''}
          phone={values.phone || ''}
          exclude={data.contact?.id || ''}
        />
      </RecordSection>
      <RecordSection title={ui('Ownership & stage')}>
        {#if canChooseOwner(page.data.permissions, 'contacts')}
          <div class="v2-field">
            <label for="contact-owner">{ui('Contact Owner')}</label>
            <select
              id="contact-owner"
              name="assigned_to"
              class="v2-input"
              bind:value={values.assigned_to}
            >
              <option value="">{ui('Unassigned')}</option>
              {#each data.owners ?? [] as owner (owner.id)}
                <option value={owner.id}>{owner.name}</option>
              {/each}
            </select>
            {#if editing}
              <input
                type="hidden"
                name="assigned_to_original"
                value={data.form?.assigned_to ?? ''}
              />
            {/if}
            {#if editing && data.server?.owner_count > 1}
              <p class="v2-sub">
                {ui(
                  'This contact has multiple owners. Choosing another owner replaces the current assignments.'
                )}
              </p>
            {/if}
          </div>
        {/if}
        <div class="v2-field">
          <label for="contact-stage">{ui('Stage')}</label>
          <select id="contact-stage" name="stage" class="v2-input" bind:value={values.stage}>
            <option value="">{ui('Select stage')}</option>
            {#each data.stages ?? [] as option (option.value)}<option value={option.value}
                >{option.label}</option
              >{/each}
          </select>
        </div>
        <div class="v2-field">
          <label for="contact-source">{ui('Source')}</label>
          <select id="contact-source" name="source" class="v2-input" bind:value={values.source}>
            <option value="">{ui('Select source')}</option>
            {#each data.sources ?? [] as option (option.value)}<option value={option.value}
                >{option.label}</option
              >{/each}
          </select>
        </div>
        <div class="v2-field">
          <span class="tags-label">{ui('Tags')}</span><TagPicker
            options={data.tagOptions ?? []}
            original={data.form?.tags ?? []}
            canCreate={data.canCreateTags}
            bind:selected={selectedTags}
            bind:creating={creatingTag}
          />
        </div>
      </RecordSection>
      <RecordSection title={ui('Communication')} collapsible={!editing}>
        <LanguageSelect bind:value={values.language} />
        <div class="v2-field">
          <label for="contact-channel">{ui('Preferred Communication Channel')}</label>
          <select
            id="contact-channel"
            name="preferred_communication_channel"
            class="v2-input"
            bind:value={values.preferred_communication_channel}
          >
            <option value="">{ui('Not specified')}</option>
            {#each data.communication_channels ?? [] as option (option.value)}<option
                value={option.value}>{option.label}</option
              >{/each}
          </select>
        </div>
      </RecordSection>
      <RecordSection title={ui('Address')} collapsible={!editing}>
        <div class="v2-field">
          <label for="contact-country">{ui('Country')}</label>
          <CountrySelect id="contact-country" name="country" bind:value={values.country} />
        </div>
        {#each addressFields as field (field.key)}
          <div class="v2-field">
            <label for={'contact-' + field.key}>{ui(field.label)}</label>
            <input
              id={'contact-' + field.key}
              class="v2-input"
              name={field.key}
              maxlength={field.max}
              autocomplete={field.autocomplete}
              bind:value={values[field.key]}
            />
          </div>
        {/each}
      </RecordSection>
      {#if !autoSave && !inline}
        <RecordSection title={ui('Notes')} collapsible={!editing}
          ><div class="v2-field">
            <label for="contact-notes">{ui('Notes')}</label>
            <textarea
              id="contact-notes"
              class="v2-input"
              name="description"
              rows="5"
              bind:value={values.description}></textarea>
          </div></RecordSection
        >
      {/if}
      {#if !editing && data.defaults?.account}
        <input type="hidden" name="account" value={data.defaults.account} />
      {/if}
    {/if}
  </fieldset>
  {#if !autoSave && !(inline && editing)}{@render formActions()}{/if}
</form>

<style>
  .tags-label {
    display: block;
    font-size: var(--crm-text-sm);
    margin-bottom: 6px;
  }

  .save-status {
    min-height: 20px;
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
  }

  .actions {
    display: flex;
    gap: 10px;
    margin-top: var(--crm-space-6);
    padding-bottom: var(--crm-space-10);
  }
</style>
