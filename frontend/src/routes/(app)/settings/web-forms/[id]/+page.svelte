<script>
  import { untrack } from 'svelte';
  import { enhance } from '$app/forms';
  import { resolve } from '$app/paths';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import Pill from '$lib/v2/components/Pill.svelte';
  import ConfirmAction from '$lib/v2/components/ConfirmAction.svelte';
  import WebFormPreview from '$lib/v2/components/WebFormPreview.svelte';
  import {
    WEBFORM_CONTACT_FIELDS,
    WEBFORM_LEAD_FIELDS,
    moveField
  } from '$lib/v2/webform-fields.js';
  import { appearanceDefaults, inspectFormHtml, mappingRows } from '$lib/v2/webform-builder.js';
  import { connectorSnippet, previewUrl } from '$lib/v2/webform-connection.js';
  import { LEAD_SOURCES, LEAD_SOURCE_LABEL } from '$lib/v2/enums.js';
  import { shortDate } from '$lib/v2/format.js';
  import { ArrowUp, ArrowDown, Plus, Trash2, Copy, Check } from '@lucide/svelte';
  /** @type {{ data:any, form:any }} */
  let { data, form } = $props();
  function seed(row) {
    return {
      ...row,
      appearance: { ...appearanceDefaults, ...row.appearance },
      fields: (row.fields ?? []).map((f) => ({ ...f })),
      captcha_secret: '',
      notify_profiles: [...(row.notify_profiles ?? [])],
      tags: [...(row.tags ?? [])]
    };
  }
  let config = $state(untrack(() => seed(data.form)));
  let originsText = $state(untrack(() => (data.form.allowed_origins ?? []).join('\n')));
  let saved = $state(untrack(() => JSON.stringify(config)));
  let loadedId = $state(untrack(() => data.form.id));
  let step = $state(1);
  let activity = $state(false);
  let mobile = $state(false);
  let editorTab = $state('fields');
  let busy = $state(false);
  let copied = $state(false);
  let notice = $state('');
  let html = $state('');
  let detected = $state([]);
  let selectedForm = $state(0);
  let mappings = $state([]);
  let inspectError = $state('');
  let testingSince = $state('');
  let testStatus = $state('');
  let dirty = $derived(JSON.stringify(config) !== saved);
  let existing = $derived(config.connection_mode === 'existing');
  let options = $derived(
    config.target_model === 'Contact' ? WEBFORM_CONTACT_FIELDS : WEBFORM_LEAD_FIELDS
  );
  let code = $derived(
    existing ? connectorSnippet(data.form.submit_url, config.website_form_id) : data.form.embed_html
  );
  let actionError = $derived(
    form?.save?.error ??
      form?.publish?.error ??
      form?.unpublish?.error ??
      form?.delete?.error ??
      form?.verify?.error
  );
  let blocker = $derived.by(() => {
    if (!config.name.trim()) return 'Enter a form name in Start.';
    if (!config.fields.some((f) => f.lead_field === 'email')) return 'Add Email in Prepare.';
    if (
      config.target_model === 'Contact' &&
      !config.fields.some((f) => f.lead_field === 'first_name')
    )
      return 'Add Name in Prepare.';
    if (config.fields.some((f) => !f.label.trim() || (!f.lead_field && !f.custom_field)))
      return 'Choose a property and label for every field in Prepare.';
    if (!existing && config.success_mode === 'redirect' && !config.redirect_url)
      return 'Enter the thank-you page URL in Configure.';
    if (existing && !code)
      return 'Use a form ID with letters, numbers, - or _, starting with a letter.';
    return '';
  });
  $effect(() => {
    if (loadedId === data.form.id) return;
    loadedId = data.form.id;
    originsText = (data.form.allowed_origins ?? []).join('\n');
    config = seed(data.form);
    saved = JSON.stringify(config);
    step = 1;
    activity = false;
    html = '';
    detected = [];
    mappings = [];
    notice = '';
    testingSince = '';
    testStatus = '';
  });
  function inspect() {
    inspectError = '';
    try {
      detected = inspectFormHtml(html);
      selectedForm = 0;
      selectDetected();
    } catch (err) {
      inspectError = err.message;
    }
  }
  function selectDetected() {
    mappings = mappingRows(detected[selectedForm].inputs).map((m) => ({
      ...m,
      property:
        config.target_model === 'Lead' && m.property === 'organization'
          ? 'company_name'
          : m.property
    }));
    const id = detected[selectedForm].id;
    if (id && /^[A-Za-z][A-Za-z0-9_-]*$/.test(id)) config.website_form_id = id;
    else config.website_form_id = '';
  }
  function applyMappings() {
    inspectError = '';
    if (mappings.some((m) => !m.property)) {
      inspectError = 'Choose a CRM property or Skip for each field.';
      return;
    }
    const chosen = mappings.filter((m) => m.property !== 'skip');
    if (!chosen.length) {
      inspectError = 'Select at least Name and Email to continue.';
      return;
    }
    const targets = chosen.map((m) => m.property);
    if (new Set(targets).size !== targets.length) {
      inspectError = 'Each CRM property can be used only once.';
      return;
    }
    config.fields = chosen.map((m) => {
      const custom = m.property.startsWith('custom:');
      const property = custom ? m.property.slice(7) : m.property;
      return {
        source: custom ? 'custom' : 'lead',
        lead_field: custom ? '' : property,
        custom_field: custom ? property : null,
        label: m.label,
        placeholder: '',
        external_name: m.name,
        is_required: ['first_name', 'email'].includes(property) || m.required
      };
    });
    html = '';
    detected = [];
    mappings = [];
    notice = 'Fields matched. Review them below.';
  }
  function addField() {
    config.fields = [
      ...config.fields,
      {
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
  function chooseField(row, value) {
    const custom = value.startsWith('custom:');
    row.source = custom ? 'custom' : 'lead';
    row.lead_field = custom ? '' : value;
    row.custom_field = custom ? value.slice(7) : null;
    row.label = custom
      ? (data.customFields.find((f) => f.id === row.custom_field)?.label ?? '')
      : (options.find((f) => f.value === value)?.label ?? '');
    if (['first_name', 'email'].includes(value)) row.is_required = true;
  }
  const save = ({ cancel, submitter }) => {
    notice = '';
    if (blocker) {
      notice = blocker;
      cancel();
      return;
    }
    busy = true;
    const advance = submitter?.value === 'next';
    return async ({ update, result }) => {
      try {
        await update({ reset: false });
        if (result.type === 'success') {
          config = seed(data.form);
          saved = JSON.stringify(config);
          notice = 'Saved.';
          testingSince = '';
          testStatus = '';
          if (advance) step = Math.min(4, step + 1);
        }
      } finally {
        busy = false;
      }
    };
  };
  const working = () => {
    busy = true;
    return async ({ update }) => {
      try {
        await update({ reset: false });
      } finally {
        busy = false;
      }
    };
  };
  const verify = () => {
    busy = true;
    return async ({ update, result }) => {
      try {
        await update({ reset: false, invalidateAll: false });
        if (result.type === 'success') {
          testingSince = result.data.testingSince;
          testStatus = result.data.received ? 'Submission received' : 'Waiting for submission';
        }
      } finally {
        busy = false;
      }
    };
  };
  async function copyCode() {
    try {
      await navigator.clipboard.writeText(code);
      copied = true;
    } catch {
      notice = 'Select the code below and copy it.';
    }
  }
</script>

<PageHeader title={data.form.name} record>
  {#snippet crumb()}<a href={resolve('/settings/web-forms')}>Web forms</a>{/snippet}
  {#snippet sub()}<Pill tone={data.form.is_published ? 'moss' : 'slate'}
      >{data.form.is_published ? 'Published' : 'Draft'}</Pill
    >{/snippet}
  {#snippet actions()}<a class="v2-btn" href={resolve('/help/knowledge/website-forms')}
      >Setup guide</a
    >{/snippet}
</PageHeader>
<div class="v2-scroll">
  <div class="v2-pad builder">
    <nav class="top-nav" aria-label="Form sections">
      <button class:active={!activity} onclick={() => (activity = false)}>Setup</button>
      <button class:active={activity} onclick={() => (activity = true)}
        >Submissions ({data.count ?? 0})</button
      >
    </nav>
    {#if actionError}<p class="error" role="alert">{actionError}</p>{/if}
    {#if notice}<p role="status">{notice}</p>{/if}
    {#if !activity}
      <nav class="steps" aria-label="Setup steps">
        {#each ['Start', 'Prepare', 'Configure', 'Install & test'] as title, i}
          <button
            class:current={step === i + 1}
            aria-current={step === i + 1 ? 'step' : undefined}
            onclick={() => {
              step = i + 1;
              notice = '';
            }}><span>{i + 1}</span>{title}</button
          >
        {/each}
      </nav>
      <form method="POST" action="?/save" use:enhance={save}>
        <input type="hidden" name="configuration" value={JSON.stringify(config)} />
        <fieldset disabled={!data.canManage || busy}>
          {#if step === 1}
            <section class="v2-card panel">
              <h2>How would you like to start?</h2>
              <div class="choices">
                <label class:selected={!existing}
                  ><input type="radio" bind:group={config.connection_mode} value="new" /><span
                    ><strong>Create a form</strong><small
                      >Build and place a form on your website.</small
                    ></span
                  ></label
                >
                <label class:selected={existing}
                  ><input type="radio" bind:group={config.connection_mode} value="existing" /><span
                    ><strong>Connect my existing form</strong><small
                      >Keep your website’s form and send a copy to the CRM.</small
                    ></span
                  ></label
                >
              </div>
              <label class="control"
                >Form name<input
                  class="v2-input"
                  maxlength="255"
                  bind:value={config.name}
                  placeholder="Contact us"
                /></label
              >
              <label class="control"
                >Website addresses<textarea
                  class="v2-input"
                  rows="2"
                  bind:value={originsText}
                  oninput={(e) =>
                    (config.allowed_origins = e.currentTarget.value
                      .split('\n')
                      .map((s) => s.trim())
                      .filter(Boolean))}
                  placeholder="https://example.com"></textarea><small
                  >One address per line. Include https:// and add www separately if used.</small
                ></label
              >
            </section>
          {:else if step === 2}
            {#if existing}
              <section class="v2-card panel">
                <h2>Match your website fields</h2>
                <details>
                  <summary>Paste your form HTML to detect fields</summary>
                  <label class="control"
                    >Form HTML<textarea
                      class="v2-input code"
                      rows="6"
                      bind:value={html}
                      placeholder="<form>…</form>"></textarea></label
                  >
                  <button type="button" class="v2-btn" onclick={inspect}>Detect fields</button>
                  {#if inspectError}<p class="error" role="alert">{inspectError}</p>{/if}
                  {#if detected.length}
                    {#if detected.length > 1}<label class="control"
                        >Choose the form<select
                          class="v2-input"
                          bind:value={selectedForm}
                          onchange={selectDetected}
                          >{#each detected as item, i}<option value={i}>{item.label}</option
                            >{/each}</select
                        ></label
                      >{/if}
                    {#each mappings as mapping}
                      <label class="mapping"
                        ><code>{mapping.name}</code><select
                          class="v2-input"
                          bind:value={mapping.property}
                          ><option value="">Choose a CRM property</option><option value="skip"
                            >Skip this field</option
                          >{#each options as opt}<option value={opt.value}>{opt.label}</option
                            >{/each}{#each data.customFields as f}<option value={`custom:${f.id}`}
                              >{f.label}</option
                            >{/each}</select
                        ></label
                      >
                    {/each}
                    <button type="button" class="v2-btn v2-btn-primary" onclick={applyMappings}
                      >Use these matches</button
                    >
                  {/if}
                </details>
                <label class="control"
                  >Website form ID<input
                    class="v2-input"
                    bind:value={config.website_form_id}
                    placeholder="contact-form"
                    maxlength="128"
                  /><small
                    >From &lt;form id="contact-form"&gt;. Leave blank only when the page has one
                    form.</small
                  ></label
                >
              </section>
            {/if}
            {#if !existing}<nav class="top-nav" aria-label="Form editor">
                <button
                  type="button"
                  class:active={editorTab === 'fields'}
                  onclick={() => (editorTab = 'fields')}>Fields</button
                ><button
                  type="button"
                  class:active={editorTab === 'appearance'}
                  onclick={() => (editorTab = 'appearance')}>Appearance</button
                >
              </nav>{/if}
            <div class:editor-layout={!existing}>
              <div>
                <section class="v2-card panel" hidden={!existing && editorTab !== 'fields'}>
                  <h2>{existing ? 'Fields to send to the CRM' : 'Contact form fields'}</h2>
                  {#each config.fields as row, i}
                    <div class="field-row">
                      <div class="row-head">
                        <strong>{row.label || `Field ${i + 1}`}</strong>
                        <div class="row-actions">
                          <button
                            type="button"
                            class="v2-btn icon"
                            aria-label={`Move ${row.label || 'field'} up`}
                            disabled={i === 0}
                            onclick={() => (config.fields = moveField(config.fields, i, -1))}
                            ><ArrowUp size={15} /></button
                          >
                          <button
                            type="button"
                            class="v2-btn icon"
                            aria-label={`Move ${row.label || 'field'} down`}
                            disabled={i === config.fields.length - 1}
                            onclick={() => (config.fields = moveField(config.fields, i, 1))}
                            ><ArrowDown size={15} /></button
                          >
                          <button
                            type="button"
                            class="v2-btn icon"
                            aria-label={`Remove ${row.label || 'field'}`}
                            onclick={() =>
                              (config.fields = config.fields.filter((_, n) => n !== i))}
                            ><Trash2 size={15} /></button
                          >
                        </div>
                      </div>
                      <div class="two">
                        <label class="control"
                          >CRM property<select
                            class="v2-input"
                            value={row.source === 'custom'
                              ? `custom:${row.custom_field}`
                              : row.lead_field}
                            onchange={(e) => chooseField(row, e.currentTarget.value)}
                            ><option value="">Select property</option>{#each options as opt}<option
                                value={opt.value}>{opt.label}</option
                              >{/each}{#each data.customFields as f}<option value={`custom:${f.id}`}
                                >{f.label}</option
                              >{/each}</select
                          ></label
                        >
                        <label class="control"
                          >{existing ? 'Website input name' : 'Label'}<input
                            class="v2-input"
                            maxlength="128"
                            bind:value={row[existing ? 'external_name' : 'label']}
                            placeholder={existing ? row.lead_field : ''}
                          /></label
                        >
                      </div>
                      {#if !existing}<label class="control"
                          >Placeholder<input
                            class="v2-input"
                            maxlength="128"
                            bind:value={row.placeholder}
                          /></label
                        >{/if}
                      <label class="check"
                        ><input
                          type="checkbox"
                          disabled={config.target_model === 'Contact' &&
                            ['first_name', 'email'].includes(row.lead_field)}
                          bind:checked={row.is_required}
                        />Required</label
                      >
                    </div>
                  {/each}
                  <button class="v2-btn" type="button" onclick={addField}
                    ><Plus size={16} />Add field</button
                  >
                </section>
                {#if !existing}
                  <section class="v2-card panel" hidden={editorTab !== 'appearance'}>
                    <h2>Appearance</h2>
                    <label class="control"
                      >Title<input
                        class="v2-input"
                        maxlength="120"
                        bind:value={config.appearance.title}
                        placeholder="Contact us"
                      /></label
                    >
                    <label class="control"
                      >Description<textarea
                        class="v2-input"
                        rows="2"
                        maxlength="500"
                        bind:value={config.appearance.description}></textarea></label
                    >
                    <label class="control"
                      >Button text<input
                        class="v2-input"
                        maxlength="64"
                        bind:value={config.submit_button_label}
                      /></label
                    >
                    <div class="two">
                      {#each [['button_color', 'Button color'], ['text_color', 'Text color'], ['background_color', 'Background']] as color}<label
                          class="control"
                          >{color[1]}<input
                            type="color"
                            bind:value={config.appearance[color[0]]}
                          /></label
                        >{/each}
                      <label class="control"
                        >Font<select class="v2-input" bind:value={config.appearance.font}
                          ><option value="system">System</option><option value="arial">Arial</option
                          ><option value="georgia">Georgia</option></select
                        ></label
                      >
                      <label class="control"
                        >Maximum width (px)<input
                          class="v2-input"
                          type="number"
                          min="280"
                          max="1000"
                          bind:value={config.appearance.width}
                        /></label
                      >
                      <label class="control"
                        >Rounded corners (px)<input
                          class="v2-input"
                          type="number"
                          min="0"
                          max="24"
                          bind:value={config.appearance.radius}
                        /></label
                      >
                      <label class="control"
                        >Columns<select class="v2-input" bind:value={config.appearance.columns}
                          ><option value={1}>One</option><option value={2}>Two</option></select
                        ></label
                      >
                    </div>
                  </section>
                {/if}
              </div>
              {#if !existing}<aside class="preview-card v2-card">
                  <div class="preview-head">
                    <strong>Live preview</strong>
                    <div>
                      <button
                        type="button"
                        class="v2-btn"
                        aria-pressed={!mobile}
                        onclick={() => (mobile = false)}>Desktop</button
                      ><button
                        type="button"
                        class="v2-btn"
                        aria-pressed={mobile}
                        onclick={() => (mobile = true)}>Mobile</button
                      >
                    </div>
                  </div>
                  <WebFormPreview
                    fields={config.fields}
                    appearance={config.appearance}
                    button={config.submit_button_label}
                    {mobile}
                  />
                  <p class="v2-hint">Preview only. Test submissions after publishing.</p>
                </aside>{/if}
            </div>
          {:else if step === 3}
            <section class="v2-card panel">
              <h2>Assign and notify</h2>
              <label class="control"
                >Responsible user<select class="v2-input" bind:value={config.assign_to}
                  ><option value={null}>Unassigned</option>{#each data.profiles as p}<option
                      value={p.id}>{p.name}</option
                    >{/each}</select
                ></label
              >
              <label class="check"
                ><input type="checkbox" bind:checked={config.notify_in_app} />Notify in the CRM</label
              >
              <label class="check"
                ><input type="checkbox" bind:checked={config.notify_email} />Notify by email</label
              >
              <details>
                <summary>Additional recipients</summary>{#each data.profiles as p}<label
                    class="check"
                    ><input
                      type="checkbox"
                      value={p.id}
                      bind:group={config.notify_profiles}
                    />{p.name}</label
                  >{/each}
              </details>
              <p class="v2-hint">The responsible user is included automatically.</p>
            </section>
            {#if !existing}<section class="v2-card panel">
                <h2>After submission</h2>
                <label class="control"
                  >Confirmation<select class="v2-input" bind:value={config.success_mode}
                    ><option value="message">Show a message</option><option value="redirect"
                      >Open a thank-you page</option
                    ></select
                  ></label
                >
                {#if config.success_mode === 'redirect'}<label class="control"
                    >Thank-you page URL<input
                      class="v2-input"
                      type="url"
                      bind:value={config.redirect_url}
                      placeholder="https://example.com/thank-you"
                    /></label
                  >{:else}<label class="control"
                    >Message<textarea class="v2-input" rows="3" bind:value={config.success_message}
                    ></textarea></label
                  >{/if}
              </section>{:else}<p class="v2-hint">
                Your website keeps its confirmation page and existing email delivery.
              </p>{/if}
            <details class="v2-card panel">
              <summary>More settings</summary>
              <label class="control"
                >Source<select
                  class="v2-input"
                  bind:value={
                    config[config.target_model === 'Contact' ? 'contact_source' : 'lead_source']
                  }
                  >{#each config.target_model === 'Contact' ? ['META', 'GOOGLE', 'TIKTOK', 'ORGANIC', 'CALL', 'CUSTOMER_REFERAL', 'EMPLOYER_REFERAL', 'WALK_IN'] : LEAD_SOURCES as source}<option
                      value={source}
                      >{LEAD_SOURCE_LABEL[source] ?? source.replaceAll('_', ' ')}</option
                    >{/each}</select
                ></label
              >
              <details>
                <summary>Tags</summary>{#each data.tags as tag}<label class="check"
                    ><input
                      type="checkbox"
                      value={tag.id}
                      bind:group={config.tags}
                    />{tag.name}</label
                  >{/each}
              </details>
              <label class="check"
                ><input type="checkbox" bind:checked={config.reject_disposable_email} />Block
                disposable email addresses</label
              >
              <label class="control"
                >Visitor verification<select class="v2-input" bind:value={config.captcha_provider}
                  ><option value="">Basic spam protection</option><option value="turnstile"
                    >Cloudflare Turnstile</option
                  ></select
                ></label
              >
              {#if config.captcha_provider === 'turnstile'}<label class="control"
                  >Turnstile site key<input
                    class="v2-input"
                    bind:value={config.captcha_site_key}
                  /></label
                ><label class="control"
                  >Turnstile secret<input
                    class="v2-input"
                    type="password"
                    autocomplete="off"
                    bind:value={config.captcha_secret}
                    placeholder={data.form.has_captcha_secret
                      ? 'Stored. Leave blank to keep it.'
                      : 'Enter secret'}
                  /></label
                ><a href={resolve('/help/knowledge/website-forms')}>Turnstile setup instructions</a
                >{/if}
            </details>
          {/if}
        </fieldset>
        {#if step < 4}<footer class="wizard-footer">
            <button
              type="button"
              class="v2-btn"
              disabled={step === 1 || busy}
              onclick={() => step--}>Back</button
            >
            <span class="v2-hint">{dirty ? 'Unsaved changes' : 'Saved'}</span>
            {#if data.canManage}<button class="v2-btn" disabled={busy} value="save">Save</button
              ><button class="v2-btn v2-btn-primary" disabled={busy} value="next"
                >{busy ? 'Saving…' : 'Save & continue'}</button
              >{:else}<button type="button" class="v2-btn" onclick={() => step++}>Continue</button
              >{/if}
          </footer>{:else if dirty}<div class="save-needed">
            <span>Save your changes to update the installation code.</span><button
              class="v2-btn v2-btn-primary"
              disabled={busy || !data.canManage}>Save changes</button
            >
          </div>{/if}
      </form>
      {#if step === 4}
        <section class="v2-card panel install">
          <h2>Install on your website</h2>
          {#if blocker}<p class="error">{blocker}</p>{/if}
          {#if !data.form.is_published}
            <p>Publish this form to enable submissions.</p>
            <form method="POST" action="?/publish" use:enhance={working}>
              <button
                class="v2-btn v2-btn-primary"
                disabled={busy || dirty || !!blocker || !data.canManage}>Publish form</button
              >
            </form>
          {:else if !dirty && !blocker}
            <ol>
              <li>Open the page’s HTML editor.</li>
              <li>
                {#if existing}Paste this code once, immediately after the closing <code
                    >&lt;/form&gt;</code
                  > tag.{:else}Paste this code in an HTML/embed block where the form should appear.{/if}
              </li>
              <li>Save and publish the website page.</li>
            </ol>
            <button class="v2-btn" onclick={copyCode}
              >{#if copied}<Check size={16} />Copied{:else}<Copy size={16} />Copy code{/if}</button
            >
            <textarea
              aria-label="Installation code"
              readonly
              class="v2-input code snippet"
              value={code}
              rows="4"></textarea>
            {#if !existing}<a
                class="v2-btn"
                target="_blank"
                rel="noreferrer"
                href={previewUrl(data.form.submit_url)}>Open published form</a
              >{/if}
          {/if}
        </section>
        {#if data.form.is_published && !dirty}
          <section class="v2-card panel">
            <h2>Test the connection</h2>
            <p>Start a test, then send an enquiry from your published website.</p>
            <form method="POST" action="?/verify" use:enhance={verify}>
              <input type="hidden" name="since" value={testingSince} />
              <button class="v2-btn v2-btn-primary" disabled={busy}
                >{busy ? 'Checking…' : testingSince ? 'Check for submission' : 'Start test'}</button
              >
            </form>
            {#if testStatus}<p role="status" class:received={testStatus === 'Submission received'}>
                {testStatus}
              </p>{/if}
            {#if testStatus === 'Submission received'}<p class="v2-hint">
                The CRM received a submission. Check the contact and recipient inbox to verify
                alerts.
              </p>
              <button
                class="v2-btn"
                onclick={() => {
                  testingSince = '';
                  testStatus = '';
                }}>New test</button
              >{/if}
          </section>
        {/if}
        <button class="v2-btn" onclick={() => (step = 3)}>Back</button>
      {/if}
    {:else}
      <section class="v2-card panel">
        <h2>Received submissions</h2>
        {#if data.analytics?.totals}<p class="v2-hint">
            Last 30 days: {data.analytics.totals.submissions ?? 0} accepted · {data.analytics.totals
              .spam ?? 0} spam blocked
          </p>{/if}
        {#if data.activityError}<p class="error">
            {data.activityError}
          </p>{:else if !data.submissions?.length}<p>No submissions yet.</p>{:else}<div
            class="table-wrap"
          >
            <table>
              <thead><tr><th>Date</th><th>Status</th><th>Record</th></tr></thead><tbody
                >{#each data.submissions as entry}<tr
                    ><td>{shortDate(entry.created_at)}</td><td
                      ><Pill
                        tone={['accepted', 'accepted_duplicate'].includes(entry.status)
                          ? 'moss'
                          : 'slate'}
                        >{{
                          accepted: 'Received',
                          accepted_duplicate: 'Existing contact',
                          rejected: 'Rejected',
                          spam: 'Spam blocked'
                        }[entry.status] ?? entry.status}</Pill
                      ></td
                    ><td
                      >{#if entry.contact}<a href={resolve(`/contacts/${entry.contact}`)}
                          >{entry.contact_name || entry.payload?.email || 'Open contact'}</a
                        >{:else if entry.lead}<a href={resolve(`/leads/${entry.lead}`)}
                          >{entry.lead_name || 'Open lead'}</a
                        >{:else}{entry.payload?.email ?? '—'}{/if}</td
                    ></tr
                  >{/each}</tbody
              >
            </table>
          </div>
          {#if data.count > data.submissions.length}<p class="v2-hint">
              Showing the latest {data.submissions.length} of {data.count} submissions.
            </p>{/if}{/if}
      </section>
      {#if data.canManage}<div class="management">
          {#if data.form.is_published}<ConfirmAction
              action="?/unpublish"
              label="Unpublish"
              confirmLabel="Unpublish form"
              explain="Stop new submissions. Existing contacts are kept."
            />{/if}<ConfirmAction
            action="?/delete"
            label="Delete form"
            confirmLabel="Delete form"
            explain="Delete this form and its submission history. Existing contacts are kept."
          />
        </div>{/if}
    {/if}
  </div>
</div>

<style>
  [hidden] {
    display: none !important;
  }
  .builder {
    container-type: inline-size;
    max-width: 1440px;
    padding-bottom: 40px;
  }
  .top-nav {
    display: flex;
    gap: 24px;
    border-bottom: 1px solid var(--v2-line, #e6e2df);
    margin-bottom: 24px;
  }
  .top-nav button {
    background: none;
    border: 0;
    padding: 12px 0;
    color: var(--v2-muted, #7d7680);
    cursor: pointer;
  }
  .top-nav .active {
    border-bottom: 2px solid currentColor;
    color: var(--v2-ink, #343234);
  }
  .steps {
    display: flex;
    gap: 8px;
    margin-bottom: 24px;
  }
  .steps button {
    display: flex;
    align-items: center;
    gap: 10px;
    flex: 1;
    background: transparent;
    border: 1px solid var(--v2-line, #e6e2df);
    border-radius: 8px;
    padding: 12px;
    color: inherit;
    cursor: pointer;
  }
  .steps span {
    border: 1px solid currentColor;
    border-radius: 50%;
    width: 24px;
    height: 24px;
    display: grid;
    place-items: center;
  }
  .steps .current {
    background: var(--v2-tint, #ebe6ed);
    font-weight: 600;
  }
  fieldset {
    margin: 0;
    padding: 0;
    border: 0;
    min-width: 0;
  }
  .panel {
    padding: 24px;
    margin-bottom: 20px;
  }
  h2 {
    font-size: 18px;
    margin: 0 0 20px;
    font-weight: 600;
  }
  .control {
    display: flex;
    flex-direction: column;
    gap: 7px;
    margin: 16px 0;
    font-size: 14px;
  }
  .control .v2-input {
    width: 100%;
    box-sizing: border-box;
  }
  .control small,
  .choices small {
    color: var(--v2-muted, #7d7680);
    font-weight: 400;
    font-size: 13px;
  }
  .choices {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }
  .choices label {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 20px;
    border: 1px solid var(--v2-line, #e6e2df);
    border-radius: 10px;
    cursor: pointer;
  }
  .choices .selected {
    border-color: #81748b;
    background: #f7f4f8;
  }
  .choices span {
    display: grid;
    gap: 6px;
  }
  .two {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0 16px;
  }
  .editor-layout {
    display: grid;
    grid-template-columns: minmax(320px, 1fr) minmax(320px, 1.1fr);
    gap: 24px;
  }
  .preview-card {
    align-self: start;
    position: sticky;
    top: 0;
    padding: 20px;
    overflow: hidden;
  }
  .preview-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 24px;
  }
  .preview-head div {
    display: flex;
    gap: 6px;
  }
  .preview-head [aria-pressed='true'] {
    background: #ebe6ed;
  }
  .preview-card .v2-hint {
    margin-top: 24px;
  }
  .field-row {
    border-bottom: 1px solid var(--v2-line, #e6e2df);
    padding: 0 0 20px;
    margin-bottom: 20px;
  }
  .row-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
  }
  .row-actions {
    display: flex;
    gap: 4px;
  }
  .icon {
    padding: 6px;
  }
  .check {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    margin: 12px 0;
  }
  details {
    margin: 16px 0;
  }
  summary {
    cursor: pointer;
    font-weight: 500;
  }
  details.panel {
    margin-bottom: 20px;
  }
  .mapping {
    display: grid;
    grid-template-columns: 1fr 1fr;
    align-items: center;
    gap: 16px;
    margin: 12px 0;
  }
  .mapping code {
    overflow-wrap: anywhere;
  }
  .code {
    font-family: ui-monospace, monospace;
    font-size: 12px;
  }
  .snippet {
    display: block;
    width: 100%;
    box-sizing: border-box;
    margin: 16px 0;
  }
  .wizard-footer {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    gap: 12px;
    padding: 16px 0;
  }
  .wizard-footer > button:first-child {
    margin-right: auto;
  }
  .error {
    color: #b63d27;
  }
  .received {
    color: #4c742d;
    font-weight: 600;
  }
  .save-needed {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
    margin-bottom: 20px;
  }
  .install ol {
    padding-left: 22px;
  }
  .install li {
    margin: 12px 0;
  }
  .table-wrap {
    overflow: auto;
  }
  table {
    width: 100%;
    text-align: left;
    border-collapse: collapse;
  }
  th,
  td {
    padding: 12px;
    border-bottom: 1px solid #e6e2df;
  }
  .management {
    display: flex;
    gap: 12px;
  }
  button:disabled {
    cursor: not-allowed;
  }
  input[type='color'] {
    width: 100%;
    height: 38px;
    border: 1px solid #e6e2df;
    background: #fff;
    border-radius: 6px;
  }
  @container (max-width: 720px) {
    .editor-layout {
      grid-template-columns: 1fr;
    }
    .preview-card {
      position: static;
    }
  }
  @media (max-width: 950px) {
    .editor-layout {
      grid-template-columns: 1fr;
    }
    .preview-card {
      position: static;
    }
  }
  @media (max-width: 600px) {
    .steps {
      display: grid;
      grid-template-columns: 1fr 1fr;
    }
    .choices,
    .two {
      grid-template-columns: 1fr;
    }
    .panel {
      padding: 16px;
    }
    .wizard-footer {
      flex-wrap: wrap;
    }
    .wizard-footer .v2-hint {
      display: none;
    }
    .preview-head {
      flex-wrap: wrap;
    }
  }
</style>
