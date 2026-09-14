<script>
  import LanguageSelect from '$lib/v2/components/LanguageSelect.svelte';
  import { enhance, deserialize } from '$app/forms';
  import { untrack, onMount, onDestroy } from 'svelte';
  import TagBadge from '$lib/v2/components/TagBadge.svelte';
  import { tagColors } from '$lib/v2/tag-colors.js';
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
  let selectedTags = $state(
    /** @type {string[]} */ (
      untrack(() => (result?.values?.tags ?? data.form?.tags ?? []).map(String))
    )
  );
  let availableTags = $state(/** @type {any[]} */ (untrack(() => [...(data.tagOptions ?? [])])));
  const originalTags = untrack(() =>
    JSON.stringify([...(data.form?.tags ?? [])].map(String).sort())
  );
  let newTagName = $state('');
  let tagsOpen = $state(false);
  let filteredTags = $derived(
    availableTags.filter(
      (tag) =>
        (tag.is_active !== false || selectedTags.includes(String(tag.id))) &&
        tag.name.toLowerCase().includes(newTagName.trim().toLowerCase())
    )
  );
  let exactTag = $derived(
    availableTags.find(
      (tag) => tag.is_active !== false && tag.name.toLowerCase() === newTagName.trim().toLowerCase()
    )
  );
  let pickedTags = $derived(availableTags.filter((tag) => selectedTags.includes(String(tag.id))));
  let newTagColor = $state('blue');
  let creatingTag = $state(false);
  let tagError = $state('');
  async function addTag() {
    if (!newTagName.trim() || creatingTag) return;
    if (exactTag) {
      selectedTags = [...new Set([...selectedTags, String(exactTag.id)])];
      newTagName = '';
      return;
    }
    if (!data.canCreateTags) return;
    creatingTag = true;
    tagError = '';
    try {
      const body = new FormData();
      body.set('name', newTagName.trim());
      body.set('color', newTagColor);
      const response = await fetch('?/createTag', {
        method: 'POST',
        body,
        headers: { 'x-sveltekit-action': 'true' }
      });
      const result = deserialize(await response.text());
      if (result.type !== 'success' || !result.data?.tag) {
        tagError =
          result.type === 'failure'
            ? String(result.data?.error ?? 'Could not create tag.')
            : 'Could not create tag. Refresh the page and try again.';
        return;
      }
      const tag = /** @type {{id: string, name: string, color: string}} */ (result.data.tag);
      availableTags = [...availableTags.filter((item) => item.id !== tag.id), tag];
      selectedTags = [...new Set([...selectedTags, String(tag.id)])];
      newTagName = '';
    } catch {
      tagError = 'Could not confirm tag creation. Refresh the page before trying again.';
    } finally {
      creatingTag = false;
    }
  }
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
    <div class="v2-field tag-field">
      <label for="contact-tags-picker">Tags</label>
      <input type="hidden" name="tags_present" value="1" />
      <input type="hidden" name="tags_original" value={originalTags} />
      {#each selectedTags as id}<input type="hidden" name="tags" value={id} />{/each}
      <details class="tag-dropdown" bind:open={tagsOpen}>
        <summary id="contact-tags-picker" class="v2-input">
          <span class="tag-selected">
            {#each pickedTags as tag (tag.id)}<TagBadge {tag} />{:else}Select tags{/each}
          </span><span aria-hidden="true">▾</span>
        </summary>
        <div class="tag-menu">
          <input
            class="v2-input"
            aria-label="Search or create tag"
            placeholder="Search or create tag"
            maxlength="50"
            bind:value={newTagName}
            onkeydown={(event) => {
              if (event.key === 'Enter') {
                event.preventDefault();
                void addTag();
              }
              if (event.key === 'Escape') {
                event.preventDefault();
                tagsOpen = false;
              }
            }}
          />
          <div class="tag-options">
            {#each filteredTags as tag (tag.id)}
              <label
                ><input
                  type="checkbox"
                  checked={selectedTags.includes(String(tag.id))}
                  onchange={(event) => {
                    selectedTags = event.currentTarget.checked
                      ? [...new Set([...selectedTags, String(tag.id)])]
                      : selectedTags.filter((id) => id !== String(tag.id));
                  }}
                /><TagBadge {tag} /></label
              >
            {:else}<span class="v2-sub">No matching tags</span>{/each}
          </div>
          {#if newTagName.trim() && !exactTag && data.canCreateTags}
            <div class="tag-create">
              <select class="v2-input" aria-label="Tag color" bind:value={newTagColor}>
                {#each Object.keys(tagColors) as color}<option value={color}
                    >{color[0].toUpperCase() + color.slice(1)}</option
                  >{/each}
              </select>
              <TagBadge tag={{ name: newTagName.trim(), color: newTagColor }} />
              <button class="v2-btn" type="button" disabled={creatingTag} onclick={addTag}>
                {creatingTag ? 'Creating…' : `Create “${newTagName.trim()}”`}
              </button>
            </div>
          {/if}
          {#if tagError}<p class="v2-error" role="alert">{tagError}</p>{/if}
        </div>
      </details>
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
      {#if inline}<button class="v2-btn" type="button" disabled={saving} onclick={onCancel}
          >Cancel</button
        >{:else}<a
          class="v2-btn"
          href={resolve(editing ? `/contacts/${data.contact.id}` : '/contacts')}>Cancel</a
        >{/if}
    </div>
  {/if}
</form>

<style>
  :is(.auto-save, .inline-edit) .fields {
    grid-template-columns: minmax(0, 1fr);
  }
  :is(.auto-save, .inline-edit) .tag-menu {
    position: static;
  }
  .save-status {
    min-height: 20px;
    font-size: 12px;
    color: var(--v2-slate);
  }

  .tag-field {
    position: relative;
  }
  .tag-dropdown summary {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    cursor: pointer;
    list-style: none;
    min-height: 40px;
  }
  .tag-dropdown summary::-webkit-details-marker {
    display: none;
  }
  .tag-selected {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    min-width: 0;
  }
  .tag-menu {
    position: absolute;
    left: 0;
    right: 0;
    z-index: 10;
    background: var(--v2-card, white);
    border: 1px solid var(--v2-line);
    border-radius: 8px;
    padding: 10px;
    box-shadow: 0 8px 20px #0002;
  }
  .tag-options {
    display: flex;
    flex-direction: column;
    gap: 8px;
    max-height: 200px;
    overflow-y: auto;
    padding: 10px 0;
  }
  .tag-options label {
    display: flex;
    gap: 6px;
    align-items: center;
    cursor: pointer;
  }
  .tag-create {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
    border-top: 1px solid var(--v2-line);
    padding-top: 10px;
  }
  .tag-create .v2-input {
    width: auto;
    max-width: 100%;
  }
  .tag-create button {
    max-width: 100%;
    white-space: normal;
    overflow-wrap: anywhere;
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
