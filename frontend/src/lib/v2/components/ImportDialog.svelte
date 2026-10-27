<script>
  import { tick } from 'svelte';
  import {
    Download,
    Upload,
    FileSpreadsheet,
    Check,
    X,
    ArrowLeft,
    ArrowRight,
    LoaderCircle,
    CircleCheck
  } from '@lucide/svelte';
  import { invalidateAll } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { page } from '$app/state';
  import Notice from '$lib/components/Notice.svelte';
  import { useI18n } from '$lib/i18n/context.js';
  import { errorReportCsv, importBatches } from '$lib/v2/import-review.js';
  import { can } from '$lib/v2/permissions.js';

  const { ui } = useI18n();
  let { module, hideTrigger = false, onDismiss = () => {} } = $props();
  let open = $state(false),
    busy = $state(false),
    message = $state('');
  let schema = $state(null),
    file = $state(null),
    result = $state(null),
    created = $state(null);
  let step = $state(1),
    dragging = $state(false),
    fileInput = $state(null),
    stepHeading = $state(null);
  let operation = $state('');
  let importedCount = $state(0);
  let rejected = $derived(result?.invalid_records ?? []);
  const steps = ['Prepare', 'Upload', 'Review'];
  const objectLabels = {
    contacts: 'Contacts',
    companies: 'Companies',
    deals: 'Deals',
    tasks: 'Tasks',
    tickets: 'Tickets'
  };
  async function goToStep(next) {
    step = next;
    await tick();
    stepHeading?.focus();
  }
  let endpoint = $derived(resolve(`/imports/${module}`));
  function close() {
    open = false;
    onDismiss();
  }
  function modal(node) {
    node.showModal();
    return { destroy: () => node.close() };
  }
  export async function show() {
    open = true;
    step = 1;
    dragging = false;
    operation = 'schema';
    busy = true;
    message = '';
    schema = null;
    file = null;
    result = null;
    created = null;
    importedCount = 0;
    try {
      const response = await fetch(endpoint);
      if (!response.headers.get('content-type')?.includes('application/json'))
        throw new Error('Could not load the import. Reload the page and try again.');
      const data = await response.json();
      if (!response.ok) throw new Error(data.message);
      schema = data;
    } catch (error) {
      message = error.message || 'Could not load the import template.';
    } finally {
      busy = false;
    }
  }
  function downloadTemplate() {
    // Headers only: example records must never be accidentally imported.
    const csv =
      '\ufeff' +
      schema.fields.map((f) => '"' + f.key.replaceAll('"', '""') + '"').join(',') +
      '\r\n';
    downloadCsv(csv, `${module}-template.csv`);
  }
  function downloadCsv(csv, filename) {
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function downloadErrors() {
    downloadCsv(errorReportCsv(rejected, schema.fields, ui), `${module}-errors.csv`);
  }
  function chooseFiles(files) {
    if (busy) return;
    file = null;
    result = null;
    message = '';
    created = null;
    importedCount = 0;
    if (!files?.length) return;
    if (files.length !== 1) {
      message = 'Choose one CSV file at a time.';
      return;
    }
    const candidate = files[0];
    if (!candidate.name.toLowerCase().endsWith('.csv') || candidate.size > schema.max_bytes) {
      message = 'Choose a CSV file of 2 MB or less.';
      return;
    }
    if (!candidate.size) {
      message = 'This file is empty. Choose a completed CSV.';
      return;
    }
    file = candidate;
  }
  function choose(event) {
    const files = event.currentTarget.files;
    if (files?.length) chooseFiles(files);
    event.currentTarget.value = '';
  }
  function drop(event) {
    event.preventDefault();
    dragging = false;
    chooseFiles(event.dataTransfer.files);
  }
  async function requestUpload(action, start = 0) {
    const body = new FormData();
    body.set('file', file);
    body.set('action', action);
    if (action === 'commit') {
      body.set('token', result.token);
      body.set('start', String(start));
    }
    const response = await fetch(endpoint, { method: 'POST', body });
    if (!response.headers.get('content-type')?.includes('application/json'))
      throw new Error('Could not complete the import. Retry the same file to check its result.');
    const data = await response.json();
    if (!response.ok) {
      // Preserve the approved file and token: retrying must resume the same receipt.
      const detail = Array.isArray(data.errors)
        ? data.errors
            .slice(0, 3)
            .map((e) => `${e.row ? `${ui('Row')} ${e.row} · ` : ''}${e.field}: ${ui(e.message)}`)
            .join(' · ')
        : '';
      throw new Error(detail || data.message);
    }
    return data;
  }
  async function upload(action) {
    busy = true;
    operation = action;
    message = '';
    try {
      if (action === 'preview') {
        result = await requestUpload('preview');
        importedCount = 0;
        await goToStep(3);
      } else {
        const data = await importBatches(
          (start) => requestUpload('commit', start),
          importedCount,
          (count) => {
            importedCount = count;
          }
        );
        created = data.created;
        try {
          await invalidateAll();
        } catch {
          message = 'Records were imported. Reload the list to see them.';
        }
      }
    } catch (error) {
      message =
        error.message || 'Could not complete the import. Retry the same file to check its result.';
    } finally {
      busy = false;
    }
  }
  function formatHint(field) {
    if (field.relation === 'Profile') return ui('Existing user email');
    if (field.relation === 'Contact') return ui('Existing contact emails, separated by ;');
    if (field.relation) return ui('Existing names; separate multiple values with ;');
    if (field.field_type === 'phone') return ui('International number, for example +12025550123');
    if (field.field_type === 'date') return 'YYYY-MM-DD';
    if (field.field_type === 'datetime') return 'YYYY-MM-DDTHH:mm:ss-04:00';
    if (field.field_type === 'checkbox') return 'true / false';
    if (field.field_type === 'multi_select') return ui('Separate values with ;');
    if (field.field_type === 'list') return ui('JSON list');
    return ui(field.field_type);
  }
</script>

{#if !hideTrigger && page.data.permissions?.is_admin && can(page.data.permissions, module, 'create')}
  <button type="button" class="v2-btn" onclick={show}>{ui('Import CSV')}</button>
{/if}
{#if open}
  <dialog
    use:modal
    aria-labelledby="csv-import-title"
    onclose={close}
    oncancel={(e) => {
      if (busy) e.preventDefault();
    }}
  >
    <header>
      <div>
        <h2 id="csv-import-title">{ui('Import records')}</h2>
        <p class="object-label">{ui(objectLabels[module])}</p>
      </div>
      <button
        type="button"
        class="close-button"
        disabled={busy}
        onclick={close}
        aria-label={ui('Close')}
        title={ui('Close')}><X size={20} strokeWidth={2} aria-hidden="true" /></button
      >
    </header>
    {#if created === null}
      <ol class="steps" aria-label={ui('Import progress')}>
        {#each steps as label, index (label)}
          <li
            class:current={step === index + 1}
            class:complete={step > index + 1}
            aria-current={step === index + 1 ? 'step' : undefined}
          >
            <span class="step-number"
              >{#if step > index + 1}<Check size={14} aria-hidden="true" />{:else}{index +
                  1}{/if}</span
            >{ui(label)}
          </li>
        {/each}
      </ol>
    {/if}
    <div class="content" aria-busy={busy}>
      {#if message}<Notice message={ui(message)} />{/if}
      {#if created !== null}
        <section class="success" role="status">
          <span class="success-icon"><CircleCheck size={28} /></span>
          <h3>{ui('Import complete')}</h3>
          <p>
            <strong>{created}</strong>
            {ui(created === 1 ? 'record imported.' : 'records imported.')}
          </p>
          {#if rejected.length}<p>
              {rejected.length}
              {ui('records skipped. Correct the error file and upload it again.')}
            </p>
            <button type="button" class="v2-btn" onclick={downloadErrors}
              ><Download size={16} aria-hidden="true" />{ui('Download errors')}</button
            >
          {/if}
        </section>
      {:else if schema}
        <h3 bind:this={stepHeading} tabindex="-1" class="step-heading">
          {ui(
            step === 1
              ? 'Prepare your file'
              : step === 2
                ? 'Upload your file'
                : 'Review before importing'
          )}
        </h3>
        {#if step === 1}
          <p>{ui('Download the template, fill in your records and save it as CSV.')}</p>
          <div class="template-card">
            <FileSpreadsheet size={28} aria-hidden="true" />
            <div class="file-info">
              <strong>{ui('Import template')}</strong><span
                >{ui('Includes your current properties.')}</span
              >
            </div>
            <button type="button" class="v2-btn" disabled={busy} onclick={downloadTemplate}
              ><Download size={16} aria-hidden="true" />{ui('Download template')}</button
            >
          </div>
          <details>
            <summary>{ui('Column guide')}</summary>
            <div class="guide">
              <table>
                <thead><tr><th>{ui('Property')}</th><th>{ui('Format')}</th></tr></thead><tbody>
                  {#each schema.fields as field (field.key)}<tr
                      ><td
                        ><strong>{ui(field.label)}{field.required ? ' *' : ''}</strong><code
                          >{field.key}</code
                        ></td
                      ><td
                        >{formatHint(field)}{#if field.options?.length}<details>
                            <summary>{ui('Allowed values')}</summary>{field.options
                              .map((o) => (typeof o === 'string' ? o : o.value))
                              .join(', ')}
                          </details>{/if}</td
                      ></tr
                    >{/each}
                </tbody>
              </table>
            </div>
          </details>
        {:else if step === 2}
          <p>{ui('Choose your completed template. You will review it before importing.')}</p>
          <input
            hidden
            bind:this={fileInput}
            type="file"
            accept=".csv,text/csv"
            onchange={choose}
            disabled={busy}
            aria-label={ui('Choose CSV file')}
          />
          <section
            class="dropzone"
            class:dragging
            aria-label={ui('Upload CSV file')}
            ondragover={(e) => {
              e.preventDefault();
              if (!busy) dragging = true;
            }}
            ondragleave={(e) => {
              if (!e.currentTarget.contains(/** @type {Node | null} */ (e.relatedTarget)))
                dragging = false;
            }}
            ondrop={drop}
          >
            <span class="upload-icon"><Upload size={26} aria-hidden="true" /></span>
            <strong>{ui('Drag your CSV here')}</strong><span
              >{ui('or choose a file from your device')}</span
            >
            <button type="button" class="v2-btn" disabled={busy} onclick={() => fileInput?.click()}
              >{ui(file ? 'Replace file' : 'Choose file')}</button
            >
            <small>CSV · UTF-8 · {schema.max_rows} {ui('records max.')} · 2 MB</small>
          </section>
          {#if file}
            <div class="selected-file" role="status">
              <FileSpreadsheet size={22} aria-hidden="true" />
              <div class="file-info">
                <strong title={file.name}>{file.name}</strong><span
                  >{Math.max(1, Math.ceil(file.size / 1024))} KB · {ui('Ready to review')}</span
                >
              </div>
              <button
                type="button"
                class="close-button"
                disabled={busy}
                aria-label={ui('Remove file')}
                onclick={() => chooseFiles([])}><X size={18} aria-hidden="true" /></button
              >
            </div>
          {/if}
        {:else}
          {#if file}<p class="review-file" title={file.name}>
              <FileSpreadsheet size={16} aria-hidden="true" />{file.name}
            </p>{/if}
          {#if result}
            <section aria-live="polite">
              <div class="review-counts">
                <div><strong>{result.total}</strong><span>{ui('Total records')}</span></div>
                <div><strong>{result.valid}</strong><span>{ui('Valid')}</span></div>
                <div><strong>{result.invalid}</strong><span>{ui('With errors')}</span></div>
              </div>
              {#each result.errors.filter((e) => !e.row) as error, index (index)}
                <Notice message={ui(error.message)} />
              {/each}
              {#if rejected.length}
                <div class="error-toolbar">
                  <p>
                    {ui('Download the error report to correct rejected records.')}
                  </p>
                  <button type="button" class="v2-btn" onclick={downloadErrors}
                    ><Download size={16} aria-hidden="true" />{ui('Download errors')}</button
                  >
                </div>
              {:else}
                <p class="ready">
                  <CircleCheck size={18} aria-hidden="true" />{ui(
                    'Validation complete. Ready to import.'
                  )}
                </p>
              {/if}
            </section>
          {/if}
        {/if}
      {:else if busy}<p role="status">{ui('Loading…')}</p>{/if}
      {#if operation === 'commit' && created === null}
        <div class="import-progress" role="status">
          <span>{importedCount} / {result?.valid ?? 0} {ui('records imported.')}</span>
          <progress
            value={importedCount}
            max={result?.valid || 1}
            aria-label={ui('Import progress')}
          ></progress>
          {#if !busy && message}<p>
              {ui('Import paused. Retry to continue without duplicating saved records.')}
            </p>{/if}
        </div>
      {/if}
      {#if busy && schema && created === null}<p class="processing" role="status">
          <LoaderCircle size={16} class="import-spinner" aria-hidden="true" />{ui(
            operation === 'commit' ? 'Importing records…' : 'Checking your file…'
          )}
        </p>{/if}
    </div>
    <footer>
      {#if created !== null}
        <button type="button" class="v2-btn v2-btn-primary" disabled={busy} onclick={close}
          >{ui('Done')}</button
        >
      {:else}
        <button type="button" class="v2-btn" disabled={busy} onclick={close}>{ui('Cancel')}</button>
        <div class="footer-actions">
          {#if step > 1}<button
              type="button"
              class="v2-btn"
              disabled={busy}
              onclick={() => goToStep(step - 1)}
              ><ArrowLeft size={16} aria-hidden="true" />{ui('Back')}</button
            >{/if}
          {#if schema}
            {#if step === 1}<button
                type="button"
                class="v2-btn v2-btn-primary"
                disabled={busy}
                onclick={() => goToStep(2)}
                >{ui('Continue to upload')}<ArrowRight size={16} aria-hidden="true" /></button
              >
            {:else if step === 2}<button
                type="button"
                class="v2-btn v2-btn-primary"
                disabled={busy || !file}
                onclick={() => upload('preview')}
                >{ui(busy ? 'Checking…' : 'Upload and review')}<ArrowRight
                  size={16}
                  aria-hidden="true"
                /></button
              >
            {:else if result?.token}<button
                type="button"
                class="v2-btn v2-btn-primary"
                disabled={busy}
                onclick={() => upload('commit')}
                >{busy
                  ? ui('Importing…')
                  : operation === 'commit'
                    ? ui('Resume import')
                    : `${ui('Import')} ${result.valid} ${ui('valid records')}`}</button
              >
            {:else}<button
                type="button"
                class="v2-btn v2-btn-primary"
                disabled={busy}
                onclick={() => goToStep(2)}>{ui('Choose corrected file')}</button
              >{/if}
          {/if}
        </div>
      {/if}
    </footer>
  </dialog>
{/if}

<style>
  dialog {
    width: min(42rem, calc(100vw - 2rem));
    max-height: calc(100dvh - 2rem);
    margin: auto;
    padding: 0;
    overflow: auto;
    border: 1px solid var(--crm-border);
    border-radius: var(--crm-radius-lg);
    background: var(--crm-surface);
    color: var(--crm-text);
    box-shadow: var(--crm-shadow-lg);
  }
  dialog::backdrop {
    background: rgb(0 0 0 / 40%);
  }
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 1.25rem 1.5rem 1rem;
  }
  h2 {
    font-size: var(--crm-text-lg);
    font-weight: 650;
    margin: 0;
  }
  h3 {
    font-size: var(--crm-text-base);
    font-weight: 650;
    margin: 0 0 0.5rem;
  }
  p {
    font-size: var(--crm-text-sm);
    color: var(--crm-text-muted);
    margin: 0.5rem 0 1rem;
  }
  .object-label {
    margin: 0.25rem 0 0;
  }
  .steps {
    display: flex;
    list-style: none;
    padding: 0 1.5rem 1rem;
    margin: 0;
    gap: 0.5rem;
    border-bottom: 1px solid var(--crm-border);
  }
  .steps li {
    flex: 1;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    color: var(--crm-text-muted);
    font-size: var(--crm-text-sm);
  }
  .step-number {
    display: grid;
    place-items: center;
    width: 1.5rem;
    height: 1.5rem;
    flex-shrink: 0;
    border: 1px solid var(--crm-border);
    border-radius: 50%;
    font-size: 0.75rem;
  }
  .current {
    font-weight: 650;
    color: var(--crm-text) !important;
  }
  .current .step-number {
    background: var(--crm-primary);
    border-color: var(--crm-primary);
    color: white;
  }
  .complete .step-number {
    background: var(--crm-canvas);
    color: var(--crm-text);
  }
  .content {
    padding: 1.5rem;
    min-width: 0;
  }
  .step-heading:focus {
    outline: none;
  }
  .template-card,
  .selected-file {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 1rem;
    margin: 1rem 0;
    border: 1px solid var(--crm-border);
    border-radius: var(--crm-radius-md);
  }
  .template-card {
    background: var(--crm-canvas);
    flex-wrap: wrap;
  }
  .file-info {
    flex: 1;
    min-width: 0;
  }
  .file-info strong,
  .file-info span {
    display: block;
    font-size: var(--crm-text-sm);
  }
  .file-info strong {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .file-info span {
    color: var(--crm-text-muted);
    margin-top: 0.25rem;
  }
  .dropzone {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    gap: 0.5rem;
    padding: 1.25rem;
    border: 1px dashed var(--crm-border);
    border-radius: var(--crm-radius-md);
    background: var(--crm-canvas);
    font-size: var(--crm-text-sm);
  }
  .dropzone.dragging {
    border-color: var(--crm-primary);
    background: color-mix(in srgb, var(--crm-primary) 6%, var(--crm-surface));
  }
  .dropzone > span:not(.upload-icon),
  small {
    color: var(--crm-text-muted);
  }
  .upload-icon {
    color: var(--crm-primary);
    margin-bottom: 0.25rem;
  }
  .dropzone button {
    margin: 0.5rem 0;
  }
  .close-button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 2.5rem;
    height: 2.5rem;
    padding: 0;
    flex-shrink: 0;
    border: 0;
    border-radius: 50%;
    background: transparent;
    color: var(--crm-text-muted);
    cursor: pointer;
  }
  .close-button:hover:not(:disabled) {
    background: var(--crm-canvas);
    color: var(--crm-text);
  }
  .close-button:focus-visible {
    outline: 2px solid var(--crm-primary);
    outline-offset: 2px;
  }
  .close-button:disabled {
    opacity: 0.45;
    cursor: default;
  }
  @media (pointer: coarse) {
    .close-button {
      width: 2.75rem;
      height: 2.75rem;
    }
  }
  .review-counts {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 0.75rem;
    margin: 1rem 0;
  }
  .review-counts > div {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }
  .review-counts strong {
    font-size: 1.5rem;
  }
  .review-counts span,
  .import-progress {
    font-size: var(--crm-text-sm);
    color: var(--crm-text-muted);
  }
  .error-toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
  }
  .error-toolbar p {
    flex: 1;
    min-width: 12rem;
    margin: 0.5rem 0;
  }
  .import-progress {
    margin-top: 1rem;
  }
  progress {
    display: block;
    width: 100%;
    margin-top: 0.5rem;
    accent-color: var(--crm-primary);
  }
  .ready,
  .processing,
  .review-file {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  .review-file {
    overflow-wrap: anywhere;
  }
  .ready {
    color: var(--crm-text);
  }
  .success {
    text-align: center;
    padding: 1.5rem 0;
  }
  .success-icon {
    display: inline-flex;
    padding: 0.75rem;
    margin-bottom: 0.75rem;
    border-radius: 50%;
    background: var(--crm-canvas);
  }
  footer {
    align-items: center;
    position: sticky;
    bottom: 0;
    display: flex;
    justify-content: space-between;
    gap: 0.75rem;
    padding: 1rem 1.5rem;
    border-top: 1px solid var(--crm-border);
    background: var(--crm-surface);
  }
  .footer-actions {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
    justify-content: flex-end;
  }
  .guide {
    overflow: auto;
    max-height: 14rem;
    margin-top: 0.5rem;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: var(--crm-text-sm);
  }
  td,
  th {
    padding: 0.5rem;
    border-bottom: 1px solid var(--crm-border);
    text-align: left;
    overflow-wrap: anywhere;
  }
  th {
    white-space: nowrap;
  }
  code {
    display: block;
    font-size: 0.75rem;
    color: var(--crm-text-muted);
  }
  summary {
    cursor: pointer;
    font-size: var(--crm-text-sm);
  }
  :global(.import-spinner) {
    animation: csv-spin 1s linear infinite;
  }
  @keyframes csv-spin {
    to {
      transform: rotate(360deg);
    }
  }
  @media (prefers-reduced-motion: reduce) {
    :global(.import-spinner) {
      animation: none;
    }
  }
  @media (max-width: 480px) {
    header,
    .content {
      padding: 1rem;
    }
    .steps {
      padding: 0 1rem 1rem;
    }
    footer {
      padding: 0.75rem 1rem;
      flex-wrap: wrap;
    }
    .footer-actions {
      flex: 1;
    }
    .steps li {
      gap: 0.35rem;
      font-size: 0.8rem;
    }
    .template-card > button {
      width: 100%;
      justify-content: center;
    }
  }
</style>
