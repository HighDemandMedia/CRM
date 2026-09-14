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
  <button type="button" class="v2-btn" disabled={fileBusy} onclick={() => fileInput.click()}>
    <Paperclip size={15} />{fileBusy ? 'Uploading…' : 'Add attachment'}
  </button>
  <span class="v2-sub" role="status">{fileBusy ? fileName : uploadStatus}</span>
  {#if fileError}
    <p class="v2-error" role="alert">{fileError}</p>
    {#if fileName}<button type="submit" class="v2-btn" disabled={fileBusy}>Retry upload</button
      >{/if}
  {/if}
</form>
{#each attachments as file (file.id)}
  <a
    class="related-item"
    href={resolve(file.href)}
    target="_blank"
    rel="noopener noreferrer"
    aria-label={`Open attachment ${file.name}`}><FileText size={15} /><span>{file.name}</span></a
  >
{:else}<p class="v2-sub">No attachments.</p>{/each}

<style>
  form {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 8px;
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
