<script>
  /**
   * One web form: the editor.
   *
   * FIVE SECTIONS, ONE SAVE
   * Fields, Behaviour, Spam, Embed and Activity all sit on this page, and the
   * first three are inside a single form posting to `?/save`. A per-section
   * save would mean three requests, three failure states, and an ordering
   * question nobody asked ("I changed the fields and the success message, why
   * did only one stick?").
   *
   * THE FIELD LIST TRAVELS AS JSON
   * Rows are added, removed and reordered in the browser, so index-derived
   * input names (`fields[3][label]`) would have to be renumbered across the
   * DOM on every move. Instead the array this component holds is serialised
   * into one hidden input at submit time. `withOrder` stamps `order` from list
   * position on the way out, and the server re-derives it from list position
   * anyway (`_write_fields` enumerates what it is given), so a client that
   * sent its own `order` could not reorder anything by lying about it.
   *
   * TWO WAYS TO REORDER, ONE IMPLEMENTATION
   * Above 768px each row has a drag handle. At or below it, the handle is
   * hidden and up/down buttons appear. Both paths call `moveField`, so they
   * cannot disagree about what a move means. Both controls are always in the
   * DOM and CSS alone decides which is usable: a JS breakpoint variable is a
   * second opinion about the viewport that can drift from the media query.
   *
   * PUBLISHING IS NOT A CHECKBOX HERE
   * It has its own endpoint, which validates the source state and the form's
   * shape. `is_published` is read-only on the update serializer, so a checkbox
   * bound to it would look like it worked and do nothing.
   */
  import { untrack } from 'svelte';
  import { enhance } from '$app/forms';
  import { resolve } from '$app/paths';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import Pill from '$lib/v2/components/Pill.svelte';
  import StatCard from '$lib/v2/components/StatCard.svelte';
  import NextAction from '$lib/v2/components/NextAction.svelte';
  import ConfirmAction from '$lib/v2/components/ConfirmAction.svelte';
  import { count, relativeTime, shortDate } from '$lib/v2/format.js';
  import { LEAD_SOURCES, LEAD_SOURCE_LABEL } from '$lib/v2/enums.js';
  import {
    moveField,
    withOrder,
    isFieldComplete,
    hasRequiredField,
    WEBFORM_CONTACT_FIELDS,
    WEBFORM_LEAD_FIELDS
  } from '$lib/v2/webform-fields.js';
  import { ChevronUp, ChevronDown, GripVertical, Plus, Trash2, Copy, Check } from '@lucide/svelte';

  /** @type {{ data: any, form: any }} */
  let { data, form } = $props();

  let wf = $derived(data.form);
  let canManage = $derived(data.canManage);
  let isContact = $derived(wf.target_model === 'Contact');
  let fieldOptions = $derived(isContact ? WEBFORM_CONTACT_FIELDS : WEBFORM_LEAD_FIELDS);
  const contactSources = [
    'META',
    'GOOGLE',
    'TIKTOK',
    'ORGANIC',
    'CALL',
    'CUSTOMER_REFERAL',
    'EMPLOYER_REFERAL',
    'WALK_IN'
  ];

  /**
   * The editable field list, seeded from the server ONCE and owned by the
   * browser from then on. `untrack` says that is deliberate: a `$derived`
   * would throw away every keystroke the moment anything invalidated `data`.
   *
   * Rows are keyed by a client-side `key` rather than by the row's `id`,
   * because a row added here has no id until it is saved, and `{#each}` needs
   * a stable key or Svelte re-uses the wrong DOM node on a reorder.
   */
  let fields = $state(untrack(() => seed(data.form.fields ?? [])));
  let nextKey = $state(1000);

  /** @param {any[]} rows */
  function seed(rows) {
    return rows.map((row, index) => ({
      key: index,
      source: row.source,
      lead_field: row.lead_field ?? '',
      custom_field: row.custom_field ?? null,
      label: row.label ?? '',
      placeholder: row.placeholder ?? '',
      external_name: row.external_name ?? '',
      is_required: Boolean(row.is_required)
    }));
  }

  /** Keep editable settings in state when switching sections or saving. */
  /** @param {any} row */
  function seedSettings(row) {
    return {
      name: row.name ?? '',
      origins: (row.allowed_origins ?? []).join('\n'),
      button: row.submit_button_label ?? '',
      message: row.success_message ?? '',
      redirect: row.redirect_url ?? '',
      owner: row.assign_to ?? '',
      source: row.target_model === 'Contact' ? row.contact_source : row.lead_source,
      inApp: Boolean(row.notify_in_app),
      email: Boolean(row.notify_email),
      recipients: [...(row.notify_profiles ?? [])],
      tags: [...(row.tags ?? [])],
      disposable: Boolean(row.reject_disposable_email),
      siteKey: row.captcha_site_key ?? ''
    };
  }
  let settings = $state(untrack(() => seedSettings(data.form)));
  let successMode = $state(untrack(() => data.form.success_mode));
  let captchaProvider = $state(untrack(() => data.form.captcha_provider ?? ''));
  let busy = $state(false);
  let activeTab = $state('configure');
  let connectionMode = $state('existing');
  let dirty = $state(false);
  let copyError = $state('');
  let copied = $state('');

  /**
   * Re-seed when the page starts describing a different form.
   *
   * SvelteKit re-uses this component across a `[id]` change rather than
   * remounting it, and the three `untrack`ed values above would then still
   * hold the previous form's fields. Guarded on the id so an ordinary
   * invalidation (a save, a publish) leaves the editor's own copy alone, which
   * is the whole reason it is untracked.
   */
  let loadedId = $state(untrack(() => data.form.id));
  $effect(() => {
    if (data.form.id === loadedId) return;
    loadedId = data.form.id;
    activeTab = 'configure';
    dirty = false;
    settings = seedSettings(data.form);
    fields = seed(data.form.fields ?? []);
    successMode = data.form.success_mode;
    captchaProvider = data.form.captcha_provider ?? '';
  });

  let complete = $derived(fields.every(isFieldComplete));

  /**
   * What stops this form being published, said before the round trip.
   *
   * The server runs the same checks and is what actually decides; this only
   * saves someone a 400 that says the same thing. The wording is kept close to
   * the API's own so the two never read like different rules.
   *
   * The last check reads the SAVED success mode rather than the select's
   * current value, on purpose: publish acts on the stored form, so a redirect
   * URL typed but not yet saved would not be there when the server looked.
   */
  let publishBlocker = $derived.by(() => {
    if (!fields.length) return 'Add at least one field first.';
    if (!hasRequiredField(fields)) {
      return 'Add an email field before publishing so returning visitors can be recognized.';
    }
    if (isContact && !fields.some((f) => f.source === 'lead' && f.lead_field === 'first_name'))
      return 'Add the Name property before publishing.';
    if (!complete) return 'Every field needs a label and something to write into.';
    if (wf.success_mode === 'redirect' && !wf.redirect_url) {
      return 'This form redirects on success but has no redirect URL set.';
    }
    return null;
  });

  const working = () => {
    busy = true;
    return async (/** @type {any} */ { update }) => {
      await update();
      busy = false;
    };
  };

  /** Save also reseeds the editor from whatever came back, so a row the
   *  server rejected or normalised does not linger in the browser's copy. */
  const saveSubmit = () => {
    busy = true;
    return async (/** @type {any} */ { update, result }) => {
      await update({ reset: false });
      busy = false;
      if (result?.type === 'success') {
        fields = seed(data.form.fields ?? []);
        settings = seedSettings(data.form);
        dirty = false;
      }
    };
  };

  function addField() {
    dirty = true;
    fields = [
      ...fields,
      {
        key: nextKey++,
        source: 'lead',
        lead_field: '',
        custom_field: null,
        label: '',
        placeholder: '',
        external_name: '',
        is_required: false
      }
    ];
  }

  /** @param {number} index */
  function removeField(index) {
    dirty = true;
    fields = fields.filter((_, i) => i !== index);
  }

  /**
   * When a row's target changes and the label is still the one the previous
   * target suggested (or empty), follow it. A label the person actually typed
   * is never overwritten: guessing is a convenience, not a correction.
   *
   * @param {number} index
   * @param {string} value
   */
  function pickLeadField(index, value) {
    const row = fields[index];
    const wasSuggested =
      !row.label.trim() ||
      row.label === (fieldOptions.find((f) => f.value === row.lead_field)?.label ?? row.lead_field);
    row.lead_field = value;
    row.custom_field = null;
    if (wasSuggested) row.label = fieldOptions.find((f) => f.value === value)?.label ?? value;
  }

  /**
   * @param {number} index
   * @param {string} value
   */
  function pickCustomField(index, value) {
    const row = fields[index];
    const previous = data.customFields.find((/** @type {any} */ c) => c.id === row.custom_field);
    const wasSuggested = !row.label.trim() || row.label === previous?.label;
    row.custom_field = value || null;
    row.lead_field = '';
    const picked = data.customFields.find((/** @type {any} */ c) => c.id === value);
    if (wasSuggested && picked) row.label = picked.label;
  }

  // ---- drag reorder, pointer only -------------------------------------
  //
  // `dragging` holds the index being carried. It is set on dragstart and
  // cleared on dragend, so an interrupted drag (Escape, drop outside the list)
  // leaves no stuck state.
  let dragging = $state(/** @type {number | null} */ (null));

  /** @param {number} index */
  function onDrop(index) {
    if (dragging === null || dragging === index) return;
    dirty = true;
    fields = moveField(fields, dragging, index - dragging);
    dragging = null;
  }

  /** @param {string} text @param {string} which */
  async function copy(text, which) {
    copyError = '';
    try {
      await navigator.clipboard.writeText(text);
      copied = which;
      setTimeout(() => (copied = ''), 1600);
    } catch {
      copyError = 'Could not copy automatically. Select the code below and copy it.';
    }
  }

  let actionError = $derived(
    form?.save?.error ??
      form?.publish?.error ??
      form?.unpublish?.error ??
      form?.delete?.error ??
      null
  );

  let submissions = $derived(data.submissions ?? []);
  let totals = $derived(data.analytics?.totals ?? null);

  /** @param {string} status */
  const statusTone = (status) =>
    status === 'accepted' || status === 'accepted_duplicate' ? 'moss' : 'slate';

  /** @param {string} status */
  const statusLabel = (status) =>
    ({
      accepted: isContact ? 'Contact created' : 'Lead created',
      accepted_duplicate: isContact ? 'Existing contact' : 'Merged into an existing lead',
      rejected_spam: 'Rejected as spam',
      rejected_invalid: 'Rejected, invalid',
      rejected_captcha: 'Rejected, captcha'
    })[status] ?? status;
</script>

<PageHeader title={wf.name} record>
  {#snippet crumb()}
    <a href={resolve('/settings/web-forms')}>Web forms</a>
  {/snippet}
  {#snippet sub()}
    <Pill tone={wf.is_published ? 'moss' : 'slate'}>
      {wf.is_published ? 'Published' : 'Draft'}
    </Pill>
    <span style="margin-left:8px">
      {wf.is_published
        ? 'Enabled. Your connected website can send submissions.'
        : 'Not receiving submissions yet. Configure, save and publish to begin.'}
    </span>
  {/snippet}
  {#snippet actions()}
    {#if canManage}
      {#if wf.is_published}
        <ConfirmAction
          action="?/unpublish"
          label="Unpublish"
          confirmLabel="Unpublish it"
          explain="Your website will stop sending new submissions to the CRM. Existing contacts are kept."
        />
      {:else}
        <form method="POST" action="?/publish" use:enhance={working}>
          <button
            class="v2-btn v2-btn-primary"
            disabled={busy || dirty || Boolean(publishBlocker)}
            title={dirty ? 'Save your changes before publishing' : undefined}
          >
            Publish
          </button>
        </form>
      {/if}
    {/if}
  {/snippet}
</PageHeader>

<div class="v2-scroll">
  <div class="v2-pad wf-body">
    {#if actionError}
      <div style="margin-bottom:18px">
        <NextAction label="That did not work" text={actionError} tone="rust" />
      </div>
    {:else if form?.saved}
      <p class="v2-sub wf-ok">Saved.</p>
    {/if}

    {#if !wf.is_published && publishBlocker && canManage}
      <div style="margin-bottom:18px">
        <NextAction label="Before you can publish" text={publishBlocker} />
      </div>
    {/if}

    <nav class="wf-tabs" aria-label="Web form sections">
      {#each [{ id: 'configure', label: '1. Configure' }, { id: 'connect', label: '2. Connect to website' }, { id: 'submissions', label: '3. Submissions' }] as tab}
        <button
          type="button"
          class:active={activeTab === tab.id}
          aria-pressed={activeTab === tab.id}
          onclick={() => (activeTab = tab.id)}>{tab.label}</button
        >
      {/each}
    </nav>
    {#if dirty}
      <p class="wf-notice" role="status">
        You have unsaved changes. <button type="button" onclick={() => (activeTab = 'configure')}
          >Return to configuration to save</button
        >.
      </p>
    {/if}

    <form
      hidden={activeTab !== 'configure'}
      method="POST"
      action="?/save"
      use:enhance={saveSubmit}
      oninput={() => (dirty = true)}
      onchange={() => (dirty = true)}
    >
      <section class="wf-section wf-intro">
        <h2>Set up your website form</h2>
        <p class="v2-sub">
          Website submission → {isContact ? 'Contact' : 'Lead'} in your organization → Team notification.
        </p>
        <div class="wf-grid">
          <div class="v2-field">
            <label for="name">Form name</label>
            <input
              id="name"
              name="name"
              class="v2-input"
              required
              maxlength="255"
              disabled={!canManage}
              bind:value={settings.name}
            />
            <p class="v2-hint">For your team, for example “Contact us — main website”.</p>
          </div>
          <div class="v2-field">
            <label for="allowed_origins">Website addresses</label>
            <textarea
              id="allowed_origins"
              name="allowed_origins"
              class="v2-input"
              rows="2"
              disabled={!canManage}
              placeholder="https://example.com"
              bind:value={settings.origins}></textarea>
            <p class="v2-hint">
              One address per line, including https://. Use the website address without a page path.
              Add the www version too if your site uses it.
            </p>
          </div>
        </div>
      </section>
      <!-- The whole ordered list, in one value. `withOrder` stamps `order`
           from list position; the server does the same from the array's own
           order, so this is a convenience and not the authority. -->
      <input type="hidden" name="fields" value={JSON.stringify(withOrder(fields))} />

      <!-- ============ Fields ============ -->
      <section class="wf-section">
        <div class="wf-section-head">
          <h2 class="v2-section">Information to collect</h2>
          <p class="v2-sub wf-section-sub">
            Choose where each website field will be saved in the CRM. {isContact
              ? 'Name and email are required.'
              : 'Email is required before publishing.'}
          </p>
        </div>

        <p class="v2-hint">
          Connecting an existing form? Use each website input’s name (for example “your-email”).
          Your website editor or developer can find it. Leave these names blank for a CRM-built
          form.
        </p>

        {#if !fields.length}
          <p class="v2-sub wf-empty">No fields yet. A form with no fields collects nothing.</p>
        {/if}

        <ul class="wf-fields">
          {#each fields as field, i (field.key)}
            <li
              class="wf-row"
              class:is-dragging={dragging === i}
              draggable={canManage}
              ondragstart={() => (dragging = i)}
              ondragend={() => (dragging = null)}
              ondragover={(e) => e.preventDefault()}
              ondrop={(e) => {
                e.preventDefault();
                onDrop(i);
              }}
            >
              <!-- Pointer reorder. Hidden below 768px, where a drag handle
                   competes with the scroll gesture and loses. -->
              <span class="wf-drag" aria-hidden="true"><GripVertical size={15} /></span>

              <div class="wf-row-body">
                <div class="v2-field">
                  <label for="tgt-{field.key}">Save in CRM property</label>
                  <select
                    id="tgt-{field.key}"
                    class="v2-input"
                    disabled={!canManage}
                    value={field.source === 'custom'
                      ? `custom:${field.custom_field}`
                      : `lead:${field.lead_field}`}
                    onchange={(e) => {
                      const value = e.currentTarget.value;
                      if (value.startsWith('custom:')) {
                        field.source = 'custom';
                        pickCustomField(i, value.slice(7));
                      } else {
                        field.source = 'lead';
                        pickLeadField(i, value.slice(5));
                      }
                    }}
                  >
                    <option value="lead:">Choose a property…</option>
                    <optgroup label={isContact ? 'Contact properties' : 'Lead properties'}>
                      {#each fieldOptions as f (f.value)}<option value={`lead:${f.value}`}
                          >{f.label}</option
                        >{/each}
                    </optgroup>
                    {#if data.customFields.length}
                      <optgroup label="Custom properties">
                        {#each data.customFields as c (c.id)}<option value={`custom:${c.id}`}
                            >{c.label}</option
                          >{/each}
                      </optgroup>
                    {/if}
                  </select>
                </div>

                <div class="v2-field">
                  <label for="external-{field.key}">Matching field on your website</label>
                  <input
                    id="external-{field.key}"
                    class="v2-input"
                    maxlength="128"
                    disabled={!canManage}
                    placeholder={field.lead_field || 'e.g. your-email'}
                    bind:value={field.external_name}
                  />
                </div>
                <details class="wf-details">
                  <summary>Field label and hint</summary>
                  <div class="wf-grid">
                    <div class="v2-field">
                      <label for="lbl-{field.key}">Label</label>
                      <input
                        id="lbl-{field.key}"
                        class="v2-input"
                        disabled={!canManage}
                        maxlength="255"
                        bind:value={field.label}
                      />
                    </div>
                    <div class="v2-field">
                      <label for="ph-{field.key}">Example shown inside the field</label>
                      <input
                        id="ph-{field.key}"
                        class="v2-input"
                        disabled={!canManage}
                        maxlength="255"
                        placeholder="Optional"
                        bind:value={field.placeholder}
                      />
                    </div>
                  </div>
                  <p class="v2-hint">
                    The label is also used in validation messages. The hint only appears in
                    CRM-built forms.
                  </p>
                </details>

                <label class="wf-check">
                  <input
                    type="checkbox"
                    disabled={!canManage ||
                      (isContact && ['first_name', 'email'].includes(field.lead_field))}
                    checked={isContact && ['first_name', 'email'].includes(field.lead_field)
                      ? true
                      : field.is_required}
                    onchange={(e) => (field.is_required = e.currentTarget.checked)}
                  />
                  {isContact && ['first_name', 'email'].includes(field.lead_field)
                    ? 'Always required'
                    : 'Visitor must complete this field'}
                </label>
              </div>

              {#if canManage}
                <div class="wf-row-actions">
                  <!-- Touch reorder. Shown below 768px, where the drag handle
                       is hidden. Both call `moveField`, one implementation. -->
                  <div class="wf-move">
                    <button
                      type="button"
                      class="wf-move-btn"
                      disabled={i === 0}
                      aria-label="Move {field.label || 'this field'} up"
                      onclick={() => {
                        dirty = true;
                        fields = moveField(fields, i, -1);
                      }}
                    >
                      <ChevronUp size={16} />
                    </button>
                    <button
                      type="button"
                      class="wf-move-btn"
                      disabled={i === fields.length - 1}
                      aria-label="Move {field.label || 'this field'} down"
                      onclick={() => {
                        dirty = true;
                        fields = moveField(fields, i, 1);
                      }}
                    >
                      <ChevronDown size={16} />
                    </button>
                  </div>
                  <button
                    type="button"
                    class="wf-move-btn"
                    aria-label="Remove {field.label || 'this field'}"
                    onclick={() => removeField(i)}
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              {/if}
            </li>
          {/each}
        </ul>

        {#if canManage}
          <button type="button" class="v2-btn v2-btn-sm wf-add" onclick={addField}>
            <Plus size={13} />Add a field
          </button>
        {/if}
      </section>

      <!-- ============ Behaviour ============ -->
      <section class="wf-section">
        <div class="wf-section-head">
          <h2 class="v2-section">After someone submits</h2>
          <p class="v2-sub wf-section-sub">
            Choose the confirmation shown to the visitor, who follows up, and who receives an alert.
          </p>
        </div>

        <div class="wf-grid">
          <div class="v2-field">
            <label for="success_mode">After a successful submission</label>
            <select
              id="success_mode"
              name="success_mode"
              class="v2-input"
              disabled={!canManage}
              bind:value={successMode}
            >
              <option value="message">Show a message</option>
              <option value="redirect">Open a thank-you page</option>
            </select>
          </div>

          {#if successMode === 'redirect'}
            <div class="v2-field">
              <label for="redirect_url">Thank-you page address</label>
              <input
                id="redirect_url"
                name="redirect_url"
                class="v2-input"
                type="url"
                maxlength="500"
                disabled={!canManage}
                bind:value={settings.redirect}
                placeholder="https://example.com/thanks"
              />
              <p class="v2-hint">After a successful submission, the visitor goes to this page.</p>
            </div>
          {:else}
            <div class="v2-field wf-wide">
              <label for="success_message">Confirmation message</label>
              <textarea
                id="success_message"
                name="success_message"
                class="v2-input"
                rows="2"
                disabled={!canManage}
                bind:value={settings.message}></textarea>
            </div>
          {/if}

          <div class="v2-field">
            <label for="assign_to">Assign new {isContact ? 'contacts' : 'leads'} to</label>
            <select
              id="assign_to"
              name="assign_to"
              class="v2-input"
              disabled={!canManage}
              bind:value={settings.owner}
            >
              <option value="">Unassigned</option>
              {#each data.profiles as p (p.id)}
                <option value={p.id}>{p.name}</option>
              {/each}
            </select>
          </div>

          <div class="v2-field">
            <label for="lead_source">Record the source as</label>
            <select
              id="lead_source"
              name={isContact ? 'contact_source' : 'lead_source'}
              class="v2-input"
              disabled={!canManage}
              bind:value={settings.source}
            >
              {#each isContact ? contactSources : LEAD_SOURCES as s (s)}
                <option value={s}
                  >{isContact
                    ? ({
                        META: 'Meta',
                        GOOGLE: 'Google',
                        TIKTOK: 'TikTok',
                        ORGANIC: 'Organic',
                        CALL: 'Phone call',
                        CUSTOMER_REFERAL: 'Customer referral',
                        EMPLOYER_REFERAL: 'Employee referral',
                        WALK_IN: 'Walk-in'
                      }[s] ?? s)
                    : (LEAD_SOURCE_LABEL[s] ?? s)}</option
                >
              {/each}
            </select>
            <p class="v2-hint">
              Used for reporting on new records. The form name is saved separately.
            </p>
          </div>

          <div class="v2-field">
            <label class="wf-check"
              ><input
                type="checkbox"
                name="notify_in_app"
                bind:checked={settings.inApp}
                disabled={!canManage}
              /> Notify inside the CRM</label
            >
            <label class="wf-check"
              ><input
                type="checkbox"
                name="notify_email"
                bind:checked={settings.email}
                disabled={!canManage}
              /> Notify by email</label
            >
          </div>
          <div class="v2-field">
            <fieldset class="wf-choices">
              <legend>Additional people to notify</legend>
              {#each data.profiles as p (p.id)}
                <label class="wf-check"
                  ><input
                    type="checkbox"
                    name="notify_profiles"
                    value={p.id}
                    bind:group={settings.recipients}
                    disabled={!canManage}
                  />{p.name}</label
                >
              {:else}<p class="v2-hint">Add team members in Users &amp; Teams.</p>{/each}
            </fieldset>
            <p class="v2-hint">
              The responsible user is included automatically. Recipients need access to the record.
              Personal CRM notification preferences still apply.
            </p>
          </div>
          <div class="v2-field wf-wide">
            <details class="wf-details">
              <summary>Tags for new records (optional)</summary>
              <div class="wf-choices">
                {#each data.tags as t (t.id)}
                  <label class="wf-check"
                    ><input
                      type="checkbox"
                      name="tags"
                      value={t.id}
                      bind:group={settings.tags}
                      disabled={!canManage}
                    />{t.name}</label
                  >
                {:else}<p class="v2-hint">
                    No tags yet. You can create them in Settings → Tags.
                  </p>{/each}
              </div>
            </details>
          </div>
          <p class="v2-hint wf-wide">
            {isContact
              ? 'If the email already belongs to a contact in this organization, the new submission is linked to that contact. Their details and owner stay unchanged.'
              : 'Returning visitors are matched to an existing lead by email.'}
          </p>
        </div>
      </section>

      <!-- ============ Spam ============ -->
      <details class="wf-section wf-details wf-advanced">
        <summary>Spam protection and CRM form appearance (optional)</summary>
        <div class="wf-section-head">
          <h2 class="v2-section">Spam protection</h2>
          <p class="v2-sub wf-section-sub">
            Basic spam protection is already enabled. Add visitor verification here if needed.
          </p>
        </div>

        <div class="wf-grid">
          <div class="v2-field wf-wide">
            <label class="wf-check">
              <input
                type="checkbox"
                name="reject_disposable_email"
                disabled={!canManage}
                bind:checked={settings.disposable}
              />
              Block disposable email addresses
            </label>
          </div>

          <div class="v2-field">
            <label for="captcha_provider">Visitor verification</label>
            <select
              id="captcha_provider"
              name="captcha_provider"
              class="v2-input"
              disabled={!canManage}
              bind:value={captchaProvider}
            >
              <option value="">Basic protection only</option>
              <option value="turnstile">Cloudflare Turnstile</option>
            </select>
          </div>

          {#if captchaProvider === 'turnstile'}
            <div class="v2-field">
              <label for="captcha_site_key">Turnstile site key</label>
              <input
                id="captcha_site_key"
                name="captcha_site_key"
                class="v2-input"
                maxlength="255"
                disabled={!canManage}
                bind:value={settings.siteKey}
              />
            </div>

            <div class="v2-field wf-wide">
              <label for="captcha_secret">Turnstile secret</label>
              <input
                id="captcha_secret"
                name="captcha_secret"
                class="v2-input"
                type="password"
                autocomplete="off"
                maxlength="255"
                disabled={!canManage}
                placeholder={wf.has_captcha_secret
                  ? 'Stored. Leave blank to keep it.'
                  : 'Paste the secret from Cloudflare'}
              />
              <p class="v2-hint">
                Get both keys from your Cloudflare Turnstile account. Leave this blank to keep a
                saved secret.
                {#if !wf.has_captcha_secret}
                  <strong>
                    Add a secret before enabling Turnstile, or submissions will be rejected.
                  </strong>
                {/if}
              </p>
            </div>
          {/if}
        </div>
        <div class="v2-field" style="margin-top:16px">
          <label for="submit_button_label">Button text for CRM-built forms</label>
          <input
            id="submit_button_label"
            name="submit_button_label"
            class="v2-input"
            maxlength="64"
            disabled={!canManage}
            bind:value={settings.button}
          />
          <p class="v2-hint">Existing website forms keep their own button and design.</p>
        </div>
      </details>

      {#if canManage}
        <div class="wf-save">
          <span class="v2-sub"
            >{dirty ? 'Unsaved changes' : 'Changes are saved when you press Save.'}</span
          >
          <button class="v2-btn v2-btn-primary" disabled={busy}
            >{busy ? 'Saving…' : 'Save configuration'}</button
          >
        </div>
      {/if}
    </form>

    <!-- ============ Embed ============ -->
    <section class="wf-section" hidden={activeTab !== 'connect'}>
      <div class="wf-section-head">
        <h2 class="v2-section">Connect to your website</h2>
        <p class="v2-sub wf-section-sub">
          Connect your existing form, or embed a new CRM form on your website.
        </p>
      </div>

      <div class="wf-connect-options" aria-label="Connection method">
        <button
          type="button"
          class:active={connectionMode === 'existing'}
          aria-pressed={connectionMode === 'existing'}
          onclick={() => (connectionMode = 'existing')}
        >
          <b>I already have a form</b><span>Keep your website’s current form and design.</span
          ></button
        >
        <button
          type="button"
          class:active={connectionMode === 'new'}
          aria-pressed={connectionMode === 'new'}
          onclick={() => (connectionMode = 'new')}
        >
          <b>I need a form</b><span>Add a ready-made CRM form to your website.</span></button
        >
      </div>
      {#if !wf.is_published}<p class="wf-notice">
          This form is still a draft. Save your configuration, then press Publish before testing it.
        </p>{/if}
      {#if connectionMode === 'existing' && !(wf.allowed_origins ?? []).length}
        <p class="wf-notice">
          Add and save your website address in Configure before connecting an existing form.
        </p>
      {/if}
      {#if copyError}<p role="alert" class="wf-notice">{copyError}</p>{/if}
      <div class="wf-snippet" hidden={connectionMode !== 'existing'}>
        <div class="wf-snippet-head">
          <b>Code for your existing form</b>
          <button
            type="button"
            class="v2-btn v2-btn-sm"
            onclick={() => copy(wf.connector_js, 'connector')}
          >
            {#if copied === 'connector'}<Check size={13} />Copied{:else}<Copy size={13} />Copy{/if}
          </button>
        </div>
        <ol class="v2-sub">
          <li>In Configure, match the website fields and add your website address.</li>
          <li>Save and publish this form.</li>
          <li>
            Give the website form id="contact-form", or change data-form in the snippet to its
            existing selector.
          </li>
          <li>
            Paste the snippet once on that page, after the form. Submit a test and open the
            Submissions tab.
          </li>
        </ol>
        <pre>{wf.connector_js}</pre>
        <p class="v2-hint">
          This connector handles submission to the CRM and keeps your form’s design. Replace any
          previous submit handler. Passwords, hidden inputs and files are not collected. If your
          site already processes submissions, have its developer call the endpoint below from that
          existing flow instead.
        </p>
        <details>
          <summary>Submit from your own code</summary>
          <p class="v2-hint">
            POST JSON using the CRM property names (for example first_name, email and description).
            Include a new UUID as request_id for each submission and reuse it when retrying. Use an
            allowed Origin; include cf-turnstile-response when verification is enabled. No CRM login
            or private API key belongs on your website.
          </p>
          <pre>{wf.submit_url}</pre>
        </details>
        <p class="v2-hint">
          Returning contacts are matched by email within this organization. Their details and owner
          stay unchanged; the message is added to their activity.
        </p>
      </div>
      <div class="wf-snippet" hidden={connectionMode !== 'new'}>
        <div class="wf-snippet-head">
          <b>Ready-made form (recommended)</b>
          <button
            type="button"
            class="v2-btn v2-btn-sm"
            onclick={() => copy(wf.embed_html, 'html')}
          >
            {#if copied === 'html'}<Check size={13} />Copied{:else}<Copy size={13} />Copy{/if}
          </button>
        </div>
        <p class="v2-hint">
          Paste this code into an HTML or embed block on your website. It shows the fields and
          confirmation you configured.
        </p>
        <pre>{wf.embed_html}</pre>
      </div>

      <details class="wf-snippet wf-details" hidden={connectionMode !== 'new'}>
        <summary>Alternative: use your website’s styling</summary>
        <div class="wf-snippet-head">
          <b>Form script</b>
          <span class="v2-sub">Inherits your site's styling.</span>
          <button type="button" class="v2-btn v2-btn-sm" onclick={() => copy(wf.embed_js, 'js')}>
            {#if copied === 'js'}<Check size={13} />Copied{:else}<Copy size={13} />Copy{/if}
          </button>
        </div>
        <pre>{wf.embed_js}</pre>
        {#if !(wf.allowed_origins ?? []).length}
          <p class="v2-hint wf-warn">
            Add your website address in Configure before using this script.
          </p>
        {/if}
      </details>
    </section>

    <!-- ============ Activity ============ -->
    <section class="wf-section" hidden={activeTab !== 'submissions'}>
      <div class="wf-section-head">
        <h2 class="v2-section">Received submissions</h2>
        <p class="v2-sub wf-section-sub">
          Recent submissions appear below. Open a contact to follow up. Totals cover the last 30
          days.
        </p>
      </div>

      {#if totals}
        <div class="v2-stats" style="margin-bottom:16px">
          <StatCard label="Accepted submissions" value={count(totals.submissions)} tone="ink" />
          <StatCard
            label="Spam blocked"
            value={count(totals.spam)}
            tone="slate"
            detail={totals.spam ? 'No record created' : 'None'}
          />
        </div>
      {/if}

      {#if data.activityError}
        <p role="alert" class="v2-sub">{data.activityError}</p>
      {:else if !submissions.length}
        <p class="v2-sub wf-empty">
          No submissions recorded yet. Send a test from your website, then refresh this page to see
          the result.
        </p>
      {:else}
        <div class="v2-table-wrap">
          <table class="v2-table">
            <thead>
              <tr>
                <th>Submitted</th>
                <th>Outcome</th>
                <th data-m="hide">Record</th>
                <th data-m="hide">From</th>
              </tr>
            </thead>
            <tbody>
              {#each submissions as s (s.id)}
                <tr>
                  <td>
                    <div class="v2-table-primary">{relativeTime(s.created_at)}</div>
                    <div class="v2-table-secondary">{shortDate(s.created_at)}</div>
                  </td>
                  <td data-m="tag"
                    ><Pill tone={statusTone(s.status)}>{statusLabel(s.status)}</Pill></td
                  >
                  <td data-m="meta">
                    {#if s.contact}
                      <a href={resolve(`/contacts/${s.contact}`)}>{s.contact_name}</a>
                    {:else if s.lead}
                      <a href={resolve(`/leads/${s.lead}`)}>{s.lead_name}</a>
                    {:else}
                      <span class="v2-muted">No record</span>
                    {/if}
                  </td>
                  <td data-m="hide" class="v2-muted">{s.referer || s.submitted_ip || '—'}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
        {#if data.count > submissions.length}
          <p class="v2-sub" style="margin-top:10px;font-size:12px">
            Showing the {submissions.length} most recent of
            <span class="v2-num">{count(data.count)}</span>.
          </p>
        {/if}
      {/if}
    </section>

    {#if canManage}
      <section class="wf-section wf-danger" hidden={activeTab !== 'configure'}>
        <div>
          <b>Delete this form</b>
          <p class="v2-sub" style="font-size:12px;margin:4px 0 0;max-width:60ch">
            Removes the form and its submission history. Records it already created stay where they
            are. Any embed still on your site will stop working.
          </p>
        </div>
        <ConfirmAction
          action="?/delete"
          label="Delete"
          confirmLabel="Delete permanently"
          explain="This cannot be undone."
        />
      </section>
    {/if}
  </div>
</div>

<style>
  [hidden] {
    display: none !important;
  }
  .wf-tabs {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    margin-bottom: 22px;
    border-bottom: 1px solid var(--v2-line);
    padding-bottom: 10px;
  }
  .wf-tabs button,
  .wf-connect-options button {
    border: 1px solid var(--v2-line);
    background: var(--v2-card);
    color: var(--v2-ink);
    border-radius: 8px;
    padding: 11px 15px;
    cursor: pointer;
    font: inherit;
    font-size: 13px;
  }
  .wf-tabs button.active,
  .wf-connect-options button.active {
    background: var(--v2-bg-sunk);
    border-color: var(--v2-slate);
    font-weight: 650;
  }
  .wf-intro {
    padding: 18px;
    border: 1px solid var(--v2-line);
    border-radius: var(--v2-radius);
    background: var(--v2-card);
  }
  .wf-intro h2 {
    margin: 0;
    font-size: 18px;
  }
  .wf-intro > p {
    margin: 8px 0 20px;
    font-size: 13px;
  }
  .wf-notice {
    padding: 12px 14px;
    border: 1px solid var(--v2-line);
    border-radius: 8px;
    font-size: 13px;
  }
  .wf-notice button {
    background: none;
    border: 0;
    color: inherit;
    text-decoration: underline;
    cursor: pointer;
    font: inherit;
  }
  .wf-details {
    margin: 12px 0;
  }
  .wf-details > summary {
    cursor: pointer;
    font-size: 13px;
    font-weight: 600;
    padding: 10px 0;
  }
  .wf-advanced {
    border: 1px solid var(--v2-line);
    border-radius: var(--v2-radius);
    padding: 6px 16px 12px;
  }
  .wf-choices {
    display: flex;
    flex-direction: column;
    gap: 12px;
    max-height: 190px;
    overflow-y: auto;
    margin: 0;
    padding: 12px;
    border: 1px solid var(--v2-line);
    border-radius: 8px;
  }
  .wf-choices legend {
    font-size: 13px;
    font-weight: 600;
  }
  .wf-connect-options {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(250px, 100%), 1fr));
    gap: 10px;
    margin-bottom: 18px;
  }
  .wf-connect-options button {
    text-align: left;
  }
  .wf-connect-options span {
    display: block;
    font-weight: 400;
    margin-top: 5px;
    font-size: 12px;
  }
  .wf-snippet > .v2-hint,
  .wf-snippet > details,
  .wf-snippet > summary {
    margin: 12px;
  }
  .wf-snippet ol {
    font-size: 13px;
    line-height: 1.7;
    padding: 12px 20px 12px 34px;
    list-style: decimal;
  }

  .wf-body {
    padding-top: 16px;
    padding-bottom: 40px;
    max-width: 900px;
  }

  .wf-section {
    margin-bottom: 30px;
  }

  .wf-section-head {
    margin-bottom: 12px;
  }

  .wf-section-sub {
    font-size: 12px;
    margin: 4px 0 0;
    max-width: 70ch;
  }

  .wf-ok {
    color: var(--v2-moss);
    font-weight: 550;
    font-size: 12.5px;
    margin: 0 0 16px;
  }

  .wf-empty {
    font-size: 12.5px;
    padding: 14px 15px;
    border: 1px dashed var(--v2-line);
    border-radius: var(--v2-radius);
    margin: 0;
  }

  /* ---- field editor ---- */

  .wf-fields {
    list-style: none;
    margin: 0;
    padding: 0;
  }

  /* Stacked, because that is what fits a phone. At 390px the four controls in
     a row share about 190px once the action column is subtracted, which turned
     "Company name" into "Comp" and every placeholder into "Placeholc". The
     side-by-side arrangement is added back at 768px, where there is room for
     it. Mobile-first: the wide layout is the enhancement. */
  .wf-row {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 12px 13px;
    border: 1px solid var(--v2-line);
    border-radius: var(--v2-radius);
    background: var(--v2-card);
    margin-bottom: 8px;
  }

  .wf-row.is-dragging {
    opacity: 0.5;
  }

  .wf-row-body {
    min-width: 0;
  }

  .wf-check {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    font-size: 12.5px;
    font-weight: 500;
  }

  /* Its own line on a phone, pushed right so the reorder and remove controls
     sit under the thumb rather than beside a truncated select. */
  .wf-row-actions {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 4px;
  }

  .wf-move {
    display: flex;
  }

  /* An explicit minimum rather than padding: these are icon-only, and an empty
     button has nothing to pad around. */
  .wf-move-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 44px;
    min-height: 44px;
    border: 1px solid var(--v2-line);
    border-radius: 8px;
    background: var(--v2-card);
    color: var(--v2-slate);
    cursor: pointer;
  }

  .wf-move-btn:hover:not(:disabled) {
    color: var(--v2-ink);
  }

  .wf-move-btn:disabled {
    opacity: 0.35;
    cursor: not-allowed;
  }

  /* Hidden by default, shown from 768px up. Mobile-first: the phone gets the
     buttons, and the pointer-only affordance is what is added on the way up,
     rather than the phone getting a desktop control taken away. */
  .wf-drag {
    display: none;
    color: var(--v2-slate);
  }

  .wf-add {
    margin-top: 4px;
  }

  /* Labels for the selects and inputs in a field row. The row's own layout
     carries the meaning visually; screen readers still need the words. */

  /* ---- settings grids ---- */

  .wf-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 14px;
  }

  .wf-save {
    position: sticky;
    bottom: 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    padding: 14px 0;
    background: var(--v2-bg);
    border-top: 1px solid var(--v2-line);
    z-index: 1;
  }

  /* ---- embed snippets ---- */

  .wf-snippet {
    border: 1px solid var(--v2-line);
    border-radius: var(--v2-radius);
    margin-bottom: 10px;
    overflow: hidden;
  }

  .wf-snippet-head {
    display: flex;
    align-items: center;
    gap: 9px;
    flex-wrap: wrap;
    padding: 9px 12px;
    border-bottom: 1px solid var(--v2-line);
    font-size: 12.5px;
  }

  .wf-snippet-head .v2-sub {
    font-size: 11.5px;
  }

  .wf-snippet-head button {
    margin-left: auto;
  }

  /* Scrolls inside its own box. Without this a long absolute URL widens the
     page and every section beside it inherits a sideways swipe. */
  .wf-snippet pre {
    margin: 0;
    padding: 11px 12px;
    overflow-x: auto;
    font-size: 12px;
    background: var(--v2-bg-sunk);
  }

  .wf-warn {
    padding: 0 12px 11px;
    color: var(--v2-clay);
  }

  .wf-danger {
    display: flex;
    gap: 14px;
    align-items: flex-start;
    justify-content: space-between;
    flex-wrap: wrap;
    padding: 14px 15px;
    border: 1px solid color-mix(in srgb, var(--v2-rust) 28%, var(--v2-line));
    border-radius: var(--v2-radius);
  }

  @media (min-width: 768px) {
    /* The pointer affordance, added at the width where a pointer is likely.
       Below this the up/down buttons are the only reorder, because a drag
       handle on a touch screen competes with the scroll gesture and loses. */
    .wf-drag {
      display: inline-flex;
      align-items: center;
      min-height: 44px;
      cursor: grab;
    }

    .wf-move {
      display: none;
    }

    /* Side by side, now that there is room for the words to fit inside the
       controls. */
    .wf-row {
      flex-direction: row;
      gap: 10px;
      align-items: flex-start;
    }

    .wf-row-body {
      flex: 1;
    }

    .wf-row-actions {
      flex: none;
    }

    .wf-grid {
      grid-template-columns: 1fr 1fr;
    }

    .wf-wide {
      grid-column: 1 / -1;
    }
  }
</style>
