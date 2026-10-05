<script>
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
  import { companyStages as defaultCompanyStages } from '$lib/v2/company-stages.js';
  import { deserialize } from '$app/forms';
  import { resolve } from '$app/paths';
  import { untrack, onMount, onDestroy } from 'svelte';
  let companyStages = $derived(
    configuredStages(page.data.pipelineConfig, 'Account', defaultCompanyStages)
  );
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
      preferred_communication_channel: '',
      website: '',
      assigned_to: '',
      industry: '',
      number_of_employees: '',
      annual_revenue: '',
      currency: data.org?.currency ?? 'USD',
      address_line: '',
      language: '',
      city: '',
      state: '',
      postcode: '',
      country: '',
      source: '',
      stage: 'LEAD',
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
  let pages = $state(
    /** @type {{name:string,url:string}[]} */ (
      untrack(() =>
        typeof values.pages === 'string'
          ? JSON.parse(values.pages || '[]')
          : [...(values.pages ?? [])]
      )
    )
  );
  let contacts = $state(/** @type {string[]} */ (untrack(() => [...(values.contacts ?? [])])));
  let contactSearch = $state('');
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
  const addresses = [
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
    return JSON.parse(
      JSON.stringify({
        name: values.name,
        email: values.email,
        phone: values.phone,
        assigned_to: values.assigned_to,
        preferred_communication_channel: values.preferred_communication_channel,
        tags: selectedTags,
        website: values.website,
        industry: values.industry,
        stage: values.stage,
        source: values.source,
        number_of_employees: values.number_of_employees ?? '',
        annual_revenue: values.annual_revenue ?? '',
        currency: values.currency,
        address_line: values.address_line,
        language: values.language,
        city: values.city,
        state: values.state,
        postcode: values.postcode,
        country: values.country,
        pages,
        contacts: [...contacts].sort()
      })
    );
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
  {#if autoSave}<div role="status">{autoStatus}</div>
    {#if autoError && !autoIssue}<div class="v2-error" role="alert">
        {autoError}<button
          type="button"
          class="v2-btn"
          onclick={() => {
            queued = snapshotValues();
            void flushAutoSave();
          }}>Retry</button
        >
      </div>{/if}{/if}
  <RecordSection title="Company details">
    <label
      >Name *<input
        class="v2-input"
        name="name"
        required
        maxlength="255"
        bind:value={values.name}
      /></label
    >
    <label
      >Domain<input
        class="v2-input"
        name="website"
        placeholder="example.com"
        bind:value={values.website}
      /></label
    >
    <label
      >Email<input
        class="v2-input"
        name="email"
        maxlength="254"
        type="email"
        bind:value={values.email}
      /></label
    >
    <label
      >Phone<input
        class="v2-input"
        name="phone"
        type="tel"
        maxlength="25"
        bind:value={values.phone}
      /></label
    >
  </RecordSection>
  <RecordSection title="Ownership & stage">
    <label
      >Owner<select class="v2-input" name="assigned_to" bind:value={values.assigned_to}
        ><option value="">Select user</option>{#each data.owners ?? [] as owner}<option
            value={owner.id}>{owner.name}</option
          >{/each}</select
      ></label
    >
    <input type="hidden" name="assigned_to_original" value={data.form?.assigned_to ?? ''} />
    <label
      >Stage<select class="v2-input" name="stage" bind:value={values.stage}
        >{#each companyStages as stage}<option value={stage.value}>{stage.label}</option
          >{/each}</select
      ></label
    >
    <label
      >Source<select class="v2-input" name="source" bind:value={values.source}
        ><option value="">Select source</option>{#each sources as [value, label]}<option {value}
            >{label}</option
          >{/each}</select
      ></label
    >
    <div class="v2-field">
      <span class="tags-label">Tags</span><TagPicker
        options={data.tagOptions ?? []}
        original={data.form?.tags ?? []}
        canCreate={data.canCreateTags}
        bind:selected={selectedTags}
        bind:creating={creatingTag}
      />
    </div>
  </RecordSection>
  <RecordSection title="Associated contacts">
    <div class="contacts-field">
      <span id="company-contacts-label">Contacts</span>
      <details class="contacts-dropdown">
        <summary
          class="v2-input"
          aria-labelledby="company-contacts-label company-contacts-selected"
        >
          <span id="company-contacts-selected"
            >{contacts.length
              ? contacts
                  .map(
                    (id) =>
                      (data.contacts ?? []).find((c) => String(c.id) === id)?.name ??
                      'Selected contact'
                  )
                  .join(', ')
              : 'Select contacts'}</span
          ><span aria-hidden="true">▾</span>
        </summary>
        <div class="contacts-menu">
          <input type="hidden" name="contacts_present" value="1" />
          <input
            type="hidden"
            name="contacts_original"
            value={JSON.stringify([...(data.form?.contacts ?? [])].sort())}
          />
          {#each contacts as id}<input type="hidden" name="contacts" value={id} />{/each}
          <input
            class="v2-input"
            type="search"
            aria-label="Search contacts"
            placeholder="Search contacts"
            bind:value={contactSearch}
          />
          <div class="contact-options">
            {#each (data.contacts ?? []).filter((c) => (c.name ?? c.first_name ?? '')
                .toLowerCase()
                .includes(contactSearch.toLowerCase())) as c}
              <label class="choice"
                ><input
                  type="checkbox"
                  checked={contacts.includes(String(c.id))}
                  onchange={(event) =>
                    (contacts = event.currentTarget.checked
                      ? [...new Set([...contacts, String(c.id)])]
                      : contacts.filter((id) => id !== String(c.id)))}
                />{c.name ?? c.first_name}</label
              >
            {:else}<span class="v2-sub">No matching contacts.</span>{/each}
          </div>
        </div>
      </details>
    </div>
  </RecordSection>
  <RecordSection title="Business details" collapsible={!editing}>
    <label
      >Industry<select class="v2-input" name="industry" bind:value={values.industry}
        ><option value="">Select industry</option>{#each data.industries ?? [] as option}<option
            value={option.value}>{option.label}</option
          >{/each}</select
      ></label
    >
    <label
      >Number of Employees<input
        class="v2-input"
        name="number_of_employees"
        type="number"
        min="0"
        step="1"
        bind:value={values.number_of_employees}
      /></label
    >
    <label
      >Annual revenue<input
        class="v2-input"
        name="annual_revenue"
        type="number"
        min="0"
        step="0.01"
        bind:value={values.annual_revenue}
      /></label
    >
    <label
      >Currency<input
        class="v2-input"
        name="currency"
        maxlength="3"
        bind:value={values.currency}
      /></label
    >
  </RecordSection>
  <RecordSection title="Communication" collapsible={!editing}>
    <LanguageSelect bind:value={values.language} />
    <label
      >Preferred Communication Channel<select
        class="v2-input"
        name="preferred_communication_channel"
        bind:value={values.preferred_communication_channel}
        ><option value="">Select channel</option><option value="SMS">SMS</option><option
          value="CALL">Call</option
        ><option value="EMAIL">Email</option></select
      ></label
    >
  </RecordSection>
  <RecordSection title="Address" collapsible={!editing}>
    <label
      >Country<select class="v2-input" name="country" bind:value={values.country}
        ><option value="">Select country</option
        >{#each countryOptions(values.country) as option}<option value={option.value}
            >{option.label}</option
          >{/each}</select
      ></label
    >
    {#each addresses as [key, label]}<label
        >{label}<input
          class="v2-input"
          name={key}
          maxlength={key === 'postcode' ? 64 : 255}
          bind:value={values[key]}
        /></label
      >{/each}
  </RecordSection>
  <fieldset>
    <legend>Pages</legend>
    {#each pages as page, index}<div class="page-row">
        <input
          class="v2-input"
          aria-label={`Page ${index + 1} name`}
          placeholder="Page name"
          required
          maxlength="100"
          bind:value={page.name}
        /><input
          class="v2-input"
          aria-label={`Page ${index + 1} link`}
          placeholder="https://…"
          type="url"
          required
          bind:value={page.url}
        /><button
          class="v2-btn"
          type="button"
          aria-label={`Remove page ${index + 1}`}
          onclick={() => (pages = pages.filter((_, i) => i !== index))}>×</button
        >
      </div>{/each}
    <input type="hidden" name="pages" value={JSON.stringify(pages)} />
    <button
      class="v2-btn"
      type="button"
      disabled={pages.length >= 50}
      onclick={() => (pages = [...pages, { name: '', url: '' }])}>Add page</button
    >
  </fieldset>

  {#if !autoSave}<div class="actions">
      <button class="v2-btn v2-btn-primary" type="submit" disabled={saving || creatingTag}
        >{saving ? 'Saving…' : editing ? 'Save company' : 'Create company'}</button
      >{#if inline}<button
          class="v2-btn"
          type="button"
          disabled={saving || creatingTag}
          onclick={onCancel}>Cancel</button
        >{:else}<a
          class="v2-btn"
          href={resolve(editing ? `/accounts/${data.account.id}` : '/accounts')}>Cancel</a
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

  :is(.auto-save, .inline-edit) .page-row {
    flex-wrap: wrap;
  }
  :is(.auto-save, .inline-edit) .contacts-menu {
    position: static;
    margin-top: var(--crm-space-1);
  }

  .contacts-field {
    min-width: 0;
    font-size: var(--crm-text-sm);
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .contacts-dropdown {
    position: relative;
  }
  .contacts-dropdown summary {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--crm-space-2);
    list-style: none;
    cursor: pointer;
  }
  .contacts-dropdown summary::-webkit-details-marker {
    display: none;
  }
  #company-contacts-selected {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .contacts-menu {
    position: absolute;
    z-index: 20;
    top: calc(100% + 4px);
    left: 0;
    right: 0;
    padding: var(--crm-space-3);
    background: var(--v2-surface, white);
    border: 1px solid var(--v2-line);
    border-radius: var(--crm-radius-md);
    box-shadow: var(--crm-shadow-lg);
  }

  label {
    display: flex;
    flex-direction: column;
    gap: 6px;
    font-size: var(--crm-text-sm);
    min-width: 0;
  }
  fieldset {
    border: 1px solid var(--v2-line);
    border-radius: var(--crm-radius-md);
    margin: var(--crm-space-5) 0;
    padding: var(--crm-space-4);
  }
  legend {
    font-size: var(--crm-text-sm);
  }
  .page-row {
    display: flex;
    gap: var(--crm-space-2);
    margin-bottom: 10px;
  }
  .page-row input {
    min-width: 0;
  }
  .contact-options {
    display: grid;
    gap: var(--crm-space-2);
    max-height: 240px;
    overflow: auto;
    padding-top: 10px;
  }
  .choice {
    flex-direction: row;
    align-items: center;
  }
  .actions {
    display: flex;
    gap: var(--crm-space-2);
    padding-bottom: var(--crm-space-6);
  }
  @media (max-width: 700px) {
    .page-row {
      flex-wrap: wrap;
    }
  }
</style>
