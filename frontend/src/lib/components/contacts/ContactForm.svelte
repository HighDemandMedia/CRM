<script>
  import LanguageSelect from '$lib/v2/components/LanguageSelect.svelte';
  import { enhance, deserialize } from '$app/forms';
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
      stage: '',
      appointment_at: '',
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
    const changes = contactChanges(baseline, snapshot);
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
    const snapshot = JSON.parse(JSON.stringify({ ...values, tags: selectedTags }));
    untrack(() => {
      queued = snapshot;
      clearTimeout(autoTimer);
      autoTimer = setTimeout(flushAutoSave, 700);
    });
  });
  onDestroy(() => clearTimeout(autoTimer));
  let appointmentLocal = $state('');
  let appointmentReady = $state(false);
  onMount(() => {
    if (values.appointment_at) {
      const date = new Date(values.appointment_at);
      const pad = (/** @type {number} */ n) => String(n).padStart(2, '0');
      if (Number.isFinite(date.getTime()))
        appointmentLocal = `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
    }
    appointmentReady = true;
    baseline = JSON.parse(JSON.stringify({ ...values, tags: selectedTags }));
    autoReady = true;
  });
  let saving = $state(false);
  const textFields = /** @type {const} */ ([
    { key: 'name', label: 'Name', required: true, type: 'text', max: 255, autocomplete: 'name' },
    { key: 'phone', label: 'Phone', required: true, type: 'tel', max: 25, autocomplete: 'tel' },
    {
      key: 'email',
      label: 'Email',
      required: false,
      type: 'email',
      max: 254,
      autocomplete: 'email'
    }
  ]);
  const addressFields = /** @type {const} */ ([
    { key: 'address_line', label: 'Address', autocomplete: 'street-address', max: 255 },
    { key: 'city', label: 'City', autocomplete: 'address-level2', max: 255 },
    { key: 'postcode', label: 'Zip Code', autocomplete: 'postal-code', max: 64 },
    { key: 'state', label: 'State', autocomplete: 'address-level1', max: 255 }
  ]);
</script>

<form
  class="v2-form"
  class:auto-save={autoSave}
  class:inline-edit={inline}
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
    if (autoSave) {
      cancel();
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
  {#if result?.error}<p class="v2-error" role="alert">{result.error}</p>{/if}
  {#if autoSave}
    <div class="save-status" role="status">{autoStatus}</div>
    {#if autoError}<div class="v2-error" role="alert">
        {autoError}
        <button
          type="button"
          class="v2-btn"
          onclick={() => {
            queued = JSON.parse(JSON.stringify({ ...values, tags: selectedTags }));
            void flushAutoSave();
          }}>Retry</button
        >
      </div>{/if}
  {/if}
  <div class="fields">
    <LanguageSelect bind:value={values.language} />

    {#each textFields as field (field.key)}
      <div class="v2-field">
        <label for={'contact-' + field.key}>{field.label}{field.required ? ' *' : ''}</label>
        <input
          id={'contact-' + field.key}
          class="v2-input"
          name={field.key}
          type={field.type}
          required={field.required}
          maxlength={field.max}
          autocomplete={field.autocomplete}
          bind:value={values[field.key]}
        />
      </div>
    {/each}
    <div class="v2-field">
      <span class="tags-label">Tags</span><TagPicker
        options={data.tagOptions ?? []}
        original={data.form?.tags ?? []}
        canCreate={data.canCreateTags}
        bind:selected={selectedTags}
        bind:creating={creatingTag}
      />
    </div>
    <div class="v2-field">
      <label for="contact-appointment">Appointment</label>
      <input
        id="contact-appointment"
        class="v2-input"
        type="datetime-local"
        disabled={!appointmentReady}
        bind:value={appointmentLocal}
        onchange={() => {
          values.appointment_at = appointmentLocal ? new Date(appointmentLocal).toISOString() : '';
        }}
      />
      <input type="hidden" name="appointment_at" value={values.appointment_at ?? ''} />
    </div>
    <div class="v2-field">
      <label for="contact-source">Source *</label>
      <select
        id="contact-source"
        name="source"
        class="v2-input"
        required
        bind:value={values.source}
      >
        <option value="">Select source</option>
        {#each data.sources ?? [] as option}<option value={option.value}>{option.label}</option
          >{/each}
      </select>
    </div>
    <div class="v2-field">
      <label for="contact-stage">Stage *</label>
      <select id="contact-stage" name="stage" class="v2-input" required bind:value={values.stage}>
        <option value="">Select stage</option>
        {#each data.stages ?? [] as option}<option value={option.value}>{option.label}</option
          >{/each}
      </select>
    </div>
    <div class="v2-field">
      <label for="contact-owner">Contact Owner</label>
      <select
        id="contact-owner"
        name="assigned_to"
        class="v2-input"
        bind:value={values.assigned_to}
      >
        <option value="">Unassigned</option>
        {#each data.owners ?? [] as owner}
          <option value={owner.id}>{owner.name}</option>
        {/each}
      </select>
      {#if editing}
        <input type="hidden" name="assigned_to_original" value={data.form?.assigned_to ?? ''} />
      {/if}
      {#if editing && data.server?.owner_count > 1}
        <p class="v2-sub">
          This contact has multiple owners. Choosing another owner replaces the current assignments.
        </p>
      {/if}
    </div>
    {#each addressFields as field (field.key)}
      <div class="v2-field">
        <label for={'contact-' + field.key}>{field.label}</label>
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
    <div class="v2-field">
      <label for="contact-channel">Preferred Communication Channel</label>
      <select
        id="contact-channel"
        name="preferred_communication_channel"
        class="v2-input"
        bind:value={values.preferred_communication_channel}
      >
        <option value="">Not specified</option>
        {#each data.communication_channels ?? [] as option}<option value={option.value}
            >{option.label}</option
          >{/each}
      </select>
    </div>
  </div>
  {#if !autoSave && !inline}
    <div class="v2-field">
      <label for="contact-notes">Notes</label>
      <textarea
        id="contact-notes"
        class="v2-input"
        name="description"
        rows="5"
        bind:value={values.description}></textarea>
    </div>
  {/if}
  {#if !editing && data.defaults?.account}
    <input type="hidden" name="account" value={data.defaults.account} />
  {/if}
  {#if !autoSave}
    <div class="actions">
      <button class="v2-btn v2-btn-primary" type="submit" disabled={saving || creatingTag}>
        {saving ? 'Saving…' : editing ? 'Save contact' : 'Create contact'}
      </button>
      {#if inline}<button
          class="v2-btn"
          type="button"
          disabled={saving || creatingTag}
          onclick={onCancel}>Cancel</button
        >{:else}<a
          class="v2-btn"
          href={resolve(editing ? `/contacts/${data.contact.id}` : '/contacts')}>Cancel</a
        >{/if}
    </div>
  {/if}
</form>

<style>
  .tags-label {
    display: block;
    font-size: 13px;
    margin-bottom: 6px;
  }

  :is(.auto-save, .inline-edit) .fields {
    grid-template-columns: minmax(0, 1fr);
  }
  .save-status {
    min-height: 20px;
    font-size: 12px;
    color: var(--v2-slate);
  }

  .fields {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0 18px;
  }
  .actions {
    display: flex;
    gap: 10px;
    margin-top: 22px;
    padding-bottom: 40px;
  }
  @media (max-width: 720px) {
    .fields {
      grid-template-columns: 1fr;
    }
  }
</style>
