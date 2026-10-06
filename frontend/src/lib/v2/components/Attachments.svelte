<script>
  import { attachmentError } from '$lib/v2/attachment-policy.js';
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();

  import { page } from '$app/state';
  import { can, recordModule } from '$lib/v2/permissions.js';
  import { enhance } from '$app/forms';
  import { resolve } from '$app/paths';
  import { invalidateAll } from '$app/navigation';
  import { Paperclip, FileText, Trash2 } from '@lucide/svelte';
  /** @typedef {{id:string,name:string,href:string|null,canDelete?:boolean}} Attachment */
  /** @type {{attachments: Attachment[],action?:string,allowUpload?:boolean}} */
  let { attachments, action = '?/attach', allowUpload = true } = $props();
  let fileBusy = $state(false);
  let fileName = $state('');
  let fileError = $state('');
  let uploadStatus = $state('');
  /** @type {HTMLInputElement} */
  let fileInput = $state();
  let selected = $state(/** @type {Attachment|null} */ (null));
  let deleting = $state(false);
  let deleteError = $state('');
  let removed = $state(/** @type {string[]} */ ([]));
  function modal(/** @type {HTMLDialogElement} */ node) {
    node.showModal();
    return { destroy: () => node.close() };
  }
  async function remove() {
    if (!selected || deleting) return;
    deleting = true;
    deleteError = '';
    const file = selected;
    try {
      const response = await fetch(resolve(`/api/attachments/${file.id}`), { method: 'DELETE' });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.message || 'Could not delete this attachment.');
      removed = [...removed, file.id];
      selected = null;
      uploadStatus = `${file.name} deleted`;
      await invalidateAll();
    } catch (/** @type {any} */ err) {
      if (selected) deleteError = err.message || 'Could not delete this attachment.';
      else fileError = 'Attachment deleted. Refresh the page to update its activity.';
    } finally {
      deleting = false;
    }
  }
</script>

<div class="attachment-section">
  <header class="association-heading">
    <h2>{ui('Attachments')}</h2>
    {#if allowUpload && (!recordModule(page.url.pathname) || can(page.data.permissions, recordModule(page.url.pathname), 'attachments'))}<form
        method="POST"
        {action}
        enctype="multipart/form-data"
        use:enhance={({ cancel }) => {
          const message = attachmentError(fileInput.files?.[0]);
          if (message) {
            fileError = message;
            cancel();
            return;
          }
          fileBusy = true;
          fileError = '';
          uploadStatus = '';
          return async ({ result, update }) => {
            fileBusy = false;
            if (result.type === 'success') {
              fileName = '';
              uploadStatus = 'File uploaded';
              await update();
            } else
              fileError =
                result.type === 'failure'
                  ? String(result.data?.message ?? 'Could not attach file.')
                  : 'Could not attach file.';
          };
        }}
      >
        <input
          bind:this={fileInput}
          type="file"
          name="attachment"
          aria-label={ui('Choose attachment')}
          hidden
          disabled={fileBusy}
          onchange={(event) => {
            const file = event.currentTarget.files?.[0];
            fileError = attachmentError(file);
            uploadStatus = '';
            if (fileError) {
              event.currentTarget.value = '';
              fileName = '';
              return;
            }
            fileName = file?.name ?? '';
            if (fileName) event.currentTarget.form?.requestSubmit();
          }}
        />
        <button
          type="button"
          class="association-icon"
          aria-label={fileBusy ? ui('Uploading attachment') : ui('Add attachment')}
          title={fileBusy ? ui('Uploading…') : ui('Add attachment')}
          disabled={fileBusy}
          onclick={() => fileInput.click()}
        >
          <Paperclip size={16} />
        </button>
      </form>{/if}
  </header>
  {#if allowUpload}<p class="v2-sub">{ui('Up to 25 MB per file.')}</p>{/if}
  {#if fileBusy || uploadStatus}<p class="v2-sub" role="status">
      {fileBusy ? ui('Uploading {name}…', { name: fileName }) : ui(uploadStatus)}
    </p>{/if}
  {#if fileError}
    <p class="v2-error" role="alert">{ui(fileError)}</p>
    {#if fileName}<button
        type="button"
        class="v2-btn"
        disabled={fileBusy}
        onclick={() => fileInput.form?.requestSubmit()}>{ui('Retry upload')}</button
      >{/if}
  {/if}
  {#each attachments.filter((file) => !removed.includes(file.id)) as file (file.id)}
    <div class="attachment-row">
      {#if file.href}
        <a
          class="related-item"
          href={resolve(/** @type {`/api/attachments/${string}/download`} */ (file.href))}
          target="_blank"
          rel="noopener noreferrer"
          aria-label={`Open attachment ${file.name}`}
          ><FileText size={15} /><span>{file.name}</span></a
        >
      {:else}<span class="related-item"><FileText size={15} /><span>{file.name}</span></span>{/if}
      {#if file.canDelete && can(page.data.permissions, recordModule(page.url.pathname), 'delete_attachments')}
        <button
          type="button"
          class="association-icon delete-file"
          aria-label={`Delete attachment ${file.name}`}
          title={ui('Delete attachment')}
          onclick={() => {
            selected = file;
            deleteError = '';
          }}
        >
          <Trash2 size={15} />
        </button>
      {/if}
    </div>
  {:else}<p class="v2-sub">{ui('No attachments.')}</p>{/each}
</div>

{#if selected}
  <dialog
    use:modal
    class="delete-dialog"
    aria-labelledby="delete-attachment-title"
    aria-describedby="delete-attachment-description"
    oncancel={(event) => {
      if (deleting) event.preventDefault();
    }}
    onclose={() => {
      if (!deleting) selected = null;
    }}
  >
    <h2 id="delete-attachment-title">{ui('Delete attachment?')}</h2>
    <p id="delete-attachment-description">
      <strong>{selected.name}</strong>
      {ui('will be permanently removed from this record and file storage. This cannot be undone.')}
    </p>
    {#if deleteError}<p class="v2-error" role="alert">{ui(deleteError)}</p>{/if}
    <div class="dialog-actions">
      <button class="v2-btn" type="button" disabled={deleting} onclick={() => (selected = null)}
        >{ui('Cancel')}</button
      >
      <button class="v2-btn danger" type="button" disabled={deleting} onclick={remove}
        >{deleting ? ui('Deleting…') : ui('Delete attachment')}</button
      >
    </div>
  </dialog>
{/if}

<style>
  .attachment-row {
    display: flex;
    align-items: center;
    gap: var(--crm-space-2);
  }
  .attachment-row .related-item {
    flex: 1;
    min-width: 0;
  }
  .delete-file {
    flex-shrink: 0;
  }
  .delete-file:hover {
    color: var(--v2-danger, var(--crm-danger));
  }
  .delete-dialog {
    position: fixed;
    inset: 0;
    margin: auto;
    width: min(440px, calc(100vw - 32px));
    max-height: calc(100dvh - 32px);
    overflow-y: auto;
    padding: var(--crm-space-6);
    border: 1px solid var(--v2-border, var(--crm-border));
    border-radius: var(--crm-radius-lg);
  }
  .delete-dialog::backdrop {
    background: var(--crm-overlay);
  }
  .delete-dialog h2 {
    margin: 0 0 var(--crm-space-3);
    font-size: var(--crm-text-lg);
  }
  .delete-dialog p {
    overflow-wrap: anywhere;
    line-height: 1.5;
  }
  .dialog-actions {
    display: flex;
    justify-content: flex-end;
    gap: var(--crm-space-2);
    margin-top: var(--crm-space-6);
  }
  .danger {
    background: var(--crm-danger-bg);
    color: var(--crm-danger);
    border-color: var(--crm-danger);
  }
  form {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: var(--crm-space-2);
    margin: 0;
  }
  .attachment-section > .v2-sub {
    margin: 6px 0 0;
    font-size: var(--crm-text-xs);
  }
  .related-item {
    display: flex;
    align-items: center;
    gap: var(--crm-space-2);
    padding: 6px 0;
  }
  .related-item span {
    min-width: 0;
    overflow-wrap: anywhere;
  }
  .v2-sub {
    overflow-wrap: anywhere;
    min-width: 0;
  }
</style>
