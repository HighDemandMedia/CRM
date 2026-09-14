<script>
  import LanguageSelect from '$lib/v2/components/LanguageSelect.svelte';
  import { enhance, deserialize } from '$app/forms';
  import { resolve } from '$app/paths';
  import { untrack, onMount, onDestroy } from 'svelte';
  import { STAGES, STAGE_LABEL } from '$lib/v2/enums.js';
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
  let contacts = $state(/** @type {string[]} */ (untrack(() => [...(values.contacts ?? [])])));
  let saving = $state(false);
  let associationError = $state('');
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
    ['state', 'State'],
    ['postcode', 'Zip Code']
  ];
  let autoReady = $state(false);
  let autoStatus = $state('');
  let autoError = $state('');
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
    autoBusy = true;
    autoStatus = 'Saving…';
    autoError = '';
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
    associationError = '';
    if (!values.account && !contacts.length) {
      cancel();
      associationError = 'Associate at least one contact or company.';
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
  {#if result?.error}<p class="v2-error" role="alert">{result.error}</p>{/if}
  {#if result?.saved}<p role="status">Saved</p>{/if}
  {#if autoSave}<div class="save-status" role="status">{autoStatus}</div>
    {#if autoError}<div class="v2-error" role="alert">
        {autoError}<button
          type="button"
          class="v2-btn"
          onclick={() => {
            queued = snapshotValues();
            void flushAutoSave();
          }}>Retry</button
        >
      </div>{/if}{/if}
  <div class="fields">
    <LanguageSelect bind:value={values.language} />
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
      >Amount<input
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
      >Stage *<select class="v2-input" name="stage" required bind:value={values.stage}
        >{#each STAGES as stage}<option value={stage}>{STAGE_LABEL[stage]}</option>{/each}</select
      ></label
    >
    <label
      >Close Date<input
        class="v2-input"
        name="closed_on"
        type="date"
        bind:value={values.closed_on}
      /></label
    >
    <label
      >Deal Owner *<select
        class="v2-input"
        name="assigned_to"
        required
        bind:value={values.assigned_to}
        ><option value="">Select user</option>{#each data.owners as owner}<option value={owner.id}
            >{owner.name}</option
          >{/each}</select
      ></label
    >
    <input type="hidden" name="assigned_to_original" value={data.form?.assigned_to ?? ''} />
    <label
      >Priority *<select class="v2-input" name="priority" required bind:value={values.priority}
        ><option value="">Select priority</option>{#each ['Low', 'Medium', 'High'] as label}<option
            value={label.toUpperCase()}>{label}</option
          >{/each}</select
      ></label
    >
    <label
      >Source *<select class="v2-input" name="lead_source" required bind:value={values.lead_source}
        ><option value="">Select source</option>{#each sources as [value, label]}<option {value}
            >{label}</option
          >{/each}</select
      ></label
    >
    {#each addressFields as [key, label]}<label
        >{label}<input class="v2-input" name={key} bind:value={values[key]} /></label
      >{/each}
    <label
      >Country<select class="v2-input" name="country" bind:value={values.country}
        ><option value="">Select country</option>{#each data.countries as [value, label]}<option
            {value}>{label}</option
          >{/each}</select
      ></label
    >
  </div>
  <fieldset>
    <legend>Associate *</legend>
    <label
      >Company<select class="v2-input" name="account" bind:value={values.account}
        ><option value="">Select company</option>{#each data.accounts as company}<option
            value={company.id}>{company.name}</option
          >{/each}</select
      ></label
    >
    <div class="contacts">
      <span>Contacts</span>
      <details>
        <summary class="v2-input"
          >{contacts.length ? `${contacts.length} selected` : 'Select contacts'}</summary
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
            >{:else}<span>No contacts available.</span>{/each}
        </div>
      </details>
    </div>
    <input type="hidden" name="contacts_present" value="1" /><input
      type="hidden"
      name="contacts_original"
      value={JSON.stringify([...(data.form?.contacts ?? [])].sort())}
    />
    {#each contacts as id}<input type="hidden" name="contacts" value={id} />{/each}
    {#if associationError}<p class="v2-error" role="alert">{associationError}</p>{/if}
  </fieldset>
  {#if showNotes}<label class="notes-field"
      >Notes<textarea class="v2-input" name="description" rows="4" bind:value={values.description}
      ></textarea></label
    >
  {/if}
  {#if !autoSave}<div class="actions">
      <button class="v2-btn v2-btn-primary" disabled={saving} type="submit"
        >{saving ? 'Saving…' : editing ? 'Save deal' : 'Create deal'}</button
      >{#if inline}<button class="v2-btn" type="button" disabled={saving} onclick={onCancel}
          >Cancel</button
        >{:else}<a
          class="v2-btn"
          href={resolve(editing ? `/pipeline/${data.deal.id}` : '/pipeline')}>Cancel</a
        >{/if}
    </div>
  {/if}
</form>

<style>
  :is(.auto-save, .inline-edit) .fields {
    grid-template-columns: minmax(0, 1fr);
  }
  :is(.auto-save, .inline-edit) fieldset {
    min-width: 0;
  }
  .save-status {
    font-size: 12px;
    min-height: 18px;
    margin-bottom: 8px;
  }

  .notes-field {
    margin-bottom: 20px;
  }
  .notes-field textarea {
    resize: vertical;
    min-height: 100px;
  }
  .fields {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }
  label,
  .contacts {
    display: flex;
    flex-direction: column;
    gap: 6px;
    font-size: 13px;
    min-width: 0;
  }
  fieldset {
    margin: 20px 0;
    border: 1px solid var(--v2-line);
    border-radius: 8px;
    padding: 16px;
    display: grid;
    gap: 14px;
  }
  legend {
    font-size: 14px;
  }
  .options {
    max-height: 200px;
    overflow: auto;
    padding: 12px;
    border: 1px solid var(--v2-line);
  }
  .choice {
    flex-direction: row;
    align-items: center;
    margin-bottom: 8px;
  }
  .actions {
    display: flex;
    gap: 8px;
    margin-bottom: 24px;
  }
  summary {
    cursor: pointer;
  }
  @media (max-width: 700px) {
    .fields {
      grid-template-columns: 1fr;
    }
  }
</style>
