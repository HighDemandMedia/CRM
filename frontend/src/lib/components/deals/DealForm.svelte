<script>
  import ConfiguredCreationFields from '$lib/components/creation/ConfiguredCreationFields.svelte';
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();

  import { countryOptions } from '$lib/constants/countries.js';
  import { recordValidation } from '$lib/components/creation/validation.js';
  import RecordSection from '$lib/components/creation/RecordSection.svelte';
  import StageRuleNotice from '$lib/components/pipelines/StageRuleNotice.svelte';
  import { configuredStages } from '$lib/v2/pipeline-config.js';
  import { page } from '$app/state';

  import { creationEnhance } from '$lib/components/creation/enhance.js';
  const enhance = creationEnhance();
  import TagPicker from '$lib/v2/components/TagPicker.svelte';
  import LanguageSelect from '$lib/v2/components/LanguageSelect.svelte';
  import { deserialize } from '$app/forms';
  import { resolve } from '$app/paths';
  import { untrack, onMount, onDestroy } from 'svelte';
  import { STAGES, STAGE_LABEL } from '$lib/v2/enums.js';
  let stageOptions = $derived(
    configuredStages(
      page.data.pipelineConfig,
      'Opportunity',
      STAGES.map((value) => ({ value, label: STAGE_LABEL[value] }))
    )
  );
  /** @type {{data:any,result?:any,editing?:boolean, autoSave?:boolean, inline?:boolean, onCancel?:()=>void, showNotes?:boolean, onSaved?:()=>Promise<void>}} */
  let {
    data,
    result = null,
    editing = false,
    autoSave = false,
    inline = false,
    onCancel = () => {},
    showNotes = true,
    onSaved = async () => {}
  } = $props();
  let values = $state(
    untrack(() => ({
      name: '',
      phone: '',
      email: '',
      amount: '',
      stage: data.defaults?.stage ?? 'PROSPECTING',
      closed_on: '',
      assigned_to: data.defaults?.assigned_to ?? '',
      priority: '',
      lead_source: '',
      address_line: '',
      language: '',
      city: '',
      state: '',
      postcode: '',
      country: '',
      account: '',
      description: '',
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
  let contacts = $state(/** @type {string[]} */ (untrack(() => [...(values.contacts ?? [])])));
  let saving = $state(false);
  const sources = [
    ['META', 'Meta'],
    ['GOOGLE', 'Google'],
    ['TIKTOK', 'TikTok'],
    ['ORGANIC', 'Organic'],
    ['CALL', 'Call'],
    ['CUSTOMER_REFERAL', 'Customer Referal'],
    ['EMPLOYER_REFERAL', 'Employer Referal'],
    ['WALK_IN', 'Walk In']
  ];
  const addressFields = [
    ['address_line', 'Address'],
    ['city', 'City'],
    ['state', 'State / region'],
    ['postcode', 'Postal code']
  ];
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
    const changes = Object.fromEntries(
      Object.entries(snapshot).filter(
        ([key, value]) => JSON.stringify(baseline[key] ?? '') !== JSON.stringify(value ?? '')
      )
    );
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
    const snapshot = snapshotValues();
    untrack(() => {
      queued = snapshot;
      clearTimeout(autoTimer);
      autoTimer = setTimeout(flushAutoSave, 700);
    });
  });
  onDestroy(() => clearTimeout(autoTimer));

  function snapshotValues() {
    const snapshot = {
      name: values.name,
      email: values.email,
      phone: values.phone,
      tags: selectedTags,
      stage: values.stage,
      closed_on: values.closed_on,
      assigned_to: values.assigned_to,
      priority: values.priority,
      lead_source: values.lead_source,
      address_line: values.address_line,
      language: values.language,
      city: values.city,
      state: values.state,
      postcode: values.postcode,
      country: values.country,
      account: values.account,
      ...(showNotes ? { description: values.description } : {}),
      contacts: [...contacts].sort(),
      ...(data.server?.amount_source === 'CALCULATED' ? {} : { amount: values.amount ?? '' })
    };
    return JSON.parse(JSON.stringify(snapshot));
  }
  onMount(() => {
    baseline = snapshotValues();
    autoReady = true;
  });
</script>

<form
  bind:this={formElement}
  use:recordValidation={result?.fieldErrors ?? autoFieldErrors}
  class="v2-form"
  class:auto-save={autoSave}
  class:inline-edit={inline}
  onfocusout={() => {
    if (autoSave && autoReady) setTimeout(flushAutoSave, 0);
  }}
  method="POST"
  action={editing ? '?/save' : '?/create'}
  use:enhance={({ cancel }) => {
    if (autoSave) {
      cancel();
      queued = snapshotValues();
      void flushAutoSave();
      return;
    }
    saving = true;
    return async ({ result: actionResult, update }) => {
      try {
        await update({ reset: false });
        if (inline && actionResult.type === 'success') await onSaved();
      } finally {
        saving = false;
      }
    };
  }}
>
  <StageRuleNotice issue={autoIssue || result?.stageRequirements} />
  {#if result?.error && !result?.stageRequirements}<p class="v2-error" role="alert">
      {result.error}
    </p>{/if}
  {#if result?.saved}<p role="status">{ui('Saved')}</p>{/if}
  {#if autoSave}<div class="save-status" role="status">{autoStatus}</div>
    {#if autoError && !autoIssue}<div class="v2-error" role="alert">
        {autoError}<button
          type="button"
          class="v2-btn"
          onclick={() => {
            queued = snapshotValues();
            void flushAutoSave();
          }}>{ui('Retry')}</button
        >
      </div>{/if}{/if}
  {#if !editing && data.creationSchema}
    <ConfiguredCreationFields target="Opportunity" {data} {result} bind:creatingTag />
  {:else}
    <RecordSection title={ui('Deal details')}>
      <label
        >{ui('Name *')}<input
          class="v2-input"
          name="name"
          required
          maxlength="255"
          bind:value={values.name}
        /></label
      >
      <label
        >{ui('Amount')}<input
          class="v2-input"
          name="amount"
          type="number"
          min="0"
          step="0.01"
          disabled={data.server?.amount_source === 'CALCULATED'}
          bind:value={values.amount}
        /></label
      >
      <label
        >{ui('Stage')}<select class="v2-input" name="stage" bind:value={values.stage}
          >{#each stageOptions as stage}<option value={stage.value}>{stage.label}</option
            >{/each}</select
        ></label
      >
      <label
        >{ui('Close Date')}<input
          class="v2-input"
          name="closed_on"
          type="date"
          bind:value={values.closed_on}
        /></label
      >
    </RecordSection>
    <RecordSection title={ui('Associated records')}>
      <label
        >{ui('Company')}<select class="v2-input" name="account" bind:value={values.account}
          ><option value="">{ui('Select company')}</option>{#each data.accounts as company}<option
              value={company.id}>{company.name}</option
            >{/each}</select
        ></label
      >
      <div class="contacts">
        <span>{ui('Contacts')}</span>
        <details>
          <summary class="v2-input"
            >{contacts.length ? `${contacts.length} selected` : ui('Select contacts')}</summary
          >
          <div class="options">
            {#each data.contacts as contact}<label class="choice"
                ><input
                  type="checkbox"
                  checked={contacts.includes(String(contact.id))}
                  onchange={(event) =>
                    (contacts = event.currentTarget.checked
                      ? [...new Set([...contacts, String(contact.id)])]
                      : contacts.filter((id) => id !== String(contact.id)))}
                />{contact.name}</label
              >{:else}<span>{ui('No contacts available.')}</span>{/each}
          </div>
        </details>
      </div>
      <input type="hidden" name="contacts_present" value="1" /><input
        type="hidden"
        name="contacts_original"
        value={JSON.stringify([...(data.form?.contacts ?? [])].sort())}
      />
      {#each contacts as id}<input type="hidden" name="contacts" value={id} />{/each}
    </RecordSection>
    <RecordSection title={ui('Ownership & classification')}>
      <label
        >{ui('Deal Owner')}<select
          class="v2-input"
          name="assigned_to"
          bind:value={values.assigned_to}
          ><option value="">{ui('Select user')}</option>{#each data.owners as owner}<option
              value={owner.id}>{owner.name}</option
            >{/each}</select
        ></label
      >
      <input type="hidden" name="assigned_to_original" value={data.form?.assigned_to ?? ''} />
      <label
        >{ui('Priority')}<select class="v2-input" name="priority" bind:value={values.priority}
          ><option value="">{ui('Select priority')}</option
          >{#each ['Low', 'Medium', 'High'] as label}<option value={label.toUpperCase()}
              >{ui(label)}</option
            >{/each}</select
        ></label
      >
      <label
        >{ui('Source')}<select class="v2-input" name="lead_source" bind:value={values.lead_source}
          ><option value="">{ui('Select source')}</option>{#each sources as [value, label]}<option
              {value}>{label}</option
            >{/each}</select
        ></label
      >
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
      <label
        >{ui('Email')}<input
          class="v2-input"
          type="email"
          name="email"
          maxlength="254"
          bind:value={values.email}
        /></label
      >
      <label
        >{ui('Phone')}<input
          class="v2-input"
          type="tel"
          name="phone"
          maxlength="25"
          bind:value={values.phone}
        /></label
      >
      <LanguageSelect bind:value={values.language} />
    </RecordSection>
    <RecordSection title={ui('Address')} collapsible={!editing}>
      <label
        >{ui('Country')}<select class="v2-input" name="country" bind:value={values.country}
          ><option value="">{ui('Select country')}</option
          >{#each countryOptions(values.country) as { value, label }}<option {value}>{label}</option
            >{/each}</select
        ></label
      >
      {#each addressFields as [key, label]}<label
          >{ui(label)}<input
            class="v2-input"
            name={key}
            maxlength={key === 'postcode' ? 64 : 255}
            bind:value={values[key]}
          /></label
        >{/each}
    </RecordSection>

    {#if showNotes}<RecordSection title={ui('Notes')} collapsible={!editing}
        ><label class="notes-field"
          >{ui('Notes')}<textarea
            class="v2-input"
            name="description"
            rows="4"
            bind:value={values.description}></textarea></label
        ></RecordSection
      >
    {/if}
  {/if}
  {#if !autoSave}<div class="actions">
      <button class="v2-btn v2-btn-primary" disabled={saving || creatingTag} type="submit"
        >{saving ? ui('Saving…') : editing ? ui('Save deal') : ui('Create deal')}</button
      >{#if inline}<button
          class="v2-btn"
          type="button"
          disabled={saving || creatingTag}
          onclick={onCancel}>{ui('Cancel')}</button
        >{:else}<a
          class="v2-btn"
          href={resolve(editing ? `/pipeline/${data.deal.id}` : '/pipeline')}>{ui('Cancel')}</a
        >{/if}
    </div>
  {/if}
</form>

<style>
  .tags-label {
    display: block;
    font-size: var(--crm-text-sm);
    margin-bottom: 6px;
  }

  .save-status {
    font-size: var(--crm-text-xs);
    min-height: 18px;
    margin-bottom: var(--crm-space-2);
  }

  .notes-field {
    margin-bottom: var(--crm-space-5);
  }
  .notes-field textarea {
    resize: vertical;
    min-height: 100px;
  }
  label,
  .contacts {
    display: flex;
    flex-direction: column;
    gap: 6px;
    font-size: var(--crm-text-sm);
    min-width: 0;
  }
  .options {
    max-height: 200px;
    overflow: auto;
    padding: var(--crm-space-3);
    border: 1px solid var(--v2-line);
  }
  .choice {
    flex-direction: row;
    align-items: center;
    margin-bottom: var(--crm-space-2);
  }
  .actions {
    display: flex;
    gap: var(--crm-space-2);
    margin-bottom: var(--crm-space-6);
  }
  summary {
    cursor: pointer;
  }
</style>
