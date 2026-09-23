<script>
  import { enhance } from '$app/forms';
  import { resolve } from '$app/paths';
  import { Paperclip, FileText } from '@lucide/svelte';
  /** @type {{attachments: Array<{id:string,name:string,href:`/api/attachments/${string}/download`}>,action?:string}} */
  let { attachments, action = '?/attach' } = $props();
  let fileBusy = $state(false);
  let fileName = $state('');
  let fileError = $state('');
  let uploadStatus = $state('');
  /** @type {HTMLInputElement} */
  let fileInput;
</script>

<div class="attachment-section">
  <header class="association-heading">
    <h2>Attachments</h2>
    <form
      method="POST"
      {action}
      enctype="multipart/form-data"
      use:enhance={() => {
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
        aria-label="Choose attachment"
        hidden
        disabled={fileBusy}
        onchange={(event) => {
          fileName = event.currentTarget.files?.[0]?.name ?? '';
          if (fileName) event.currentTarget.form?.requestSubmit();
        }}
      />
      <button
        type="button"
        class="association-icon"
        aria-label={fileBusy ? 'Uploading attachment' : 'Add attachment'}
        title={fileBusy ? 'Uploading…' : 'Add attachment'}
        disabled={fileBusy}
        onclick={() => fileInput.click()}
      >
        <Paperclip size={16} />
      </button>
    </form>
  </header>
  {#if fileBusy || uploadStatus}<p class="v2-sub" role="status">
      {fileBusy ? `Uploading ${fileName}…` : uploadStatus}
    </p>{/if}
  {#if fileError}
    <p class="v2-error" role="alert">{fileError}</p>
    {#if fileName}<button
        type="button"
        class="v2-btn"
        disabled={fileBusy}
        onclick={() => fileInput.form?.requestSubmit()}>Retry upload</button
      >{/if}
  {/if}
  {#each attachments as file (file.id)}
    <a
      class="related-item"
      href={resolve(file.href)}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={`Open attachment ${file.name}`}><FileText size={15} /><span>{file.name}</span></a
    >
  {:else}<p class="v2-sub">No attachments.</p>{/each}
</div>

<style>
  form {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
    margin: 0;
  }
  .attachment-section > .v2-sub {
    margin: 6px 0 0;
    font-size: 12px;
  }
  .related-item {
    display: flex;
    align-items: center;
    gap: 8px;
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
