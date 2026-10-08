<script>
  import { page } from '$app/state';
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();
  let { endpoint, columns, rows, filename } = $props();
  let open = $state(false),
    scope = $state('filtered'),
    busy = $state(false),
    message = $state('');
  function modal(node) {
    node.showModal();
    return {
      destroy() {
        node.close();
      }
    };
  }
  async function download() {
    busy = true;
    message = '';
    try {
      const query = new URLSearchParams(page.url.searchParams);
      query.set('columns', columns.join(','));
      query.set('scope', scope);
      const body = new FormData();
      if (scope === 'page') for (const row of rows) body.append('ids', row.id);
      const response = await fetch(`${endpoint}?${query}`, { method: 'POST', body });
      if (!response.ok || !response.headers.get('content-type')?.includes('text/csv'))
        throw new Error(
          response.status === 403
            ? 'Your permissions do not allow this export.'
            : 'Could not export records. Please try again.'
        );
      const url = URL.createObjectURL(await response.blob());
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = filename;
      anchor.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      open = false;
    } catch (error) {
      message = error.message || 'Could not export records. Please try again.';
    } finally {
      busy = false;
    }
  }
</script>

<button
  class="v2-btn"
  type="button"
  onclick={() => {
    scope = 'filtered';
    message = '';
    open = true;
  }}>{ui('Export CSV')}</button
>
{#if open}
  <dialog
    use:modal
    aria-label={ui('Export records')}
    onclose={() => (open = false)}
    oncancel={(event) => {
      if (busy) event.preventDefault();
    }}
  >
    <h2>{ui('Export records')}</h2>
    <p>{ui('Includes the columns selected in your list, in the same order.')}</p>
    <fieldset disabled={busy}>
      <legend>{ui('Which records?')}</legend>
      <label
        ><input type="radio" bind:group={scope} value="filtered" /><span
          ><strong>{ui('All filtered results')}</strong><small
            >{ui('All pages matching your current filters.')}</small
          ></span
        ></label
      >
      <label
        ><input type="radio" bind:group={scope} value="page" disabled={!rows.length} /><span
          ><strong>{ui('Current page only')} ({rows.length})</strong><small
            >{ui('Only the records currently displayed.')}</small
          ></span
        ></label
      >
      <label
        ><input type="radio" bind:group={scope} value="all" /><span
          ><strong>{ui('All records')}</strong><small
            >{ui('Ignores filters. Includes only records you can export.')}</small
          ></span
        ></label
      >
    </fieldset>
    {#if message}<p class="v2-error" role="alert">{ui(message)}</p>{/if}
    <div class="actions">
      <button type="button" class="v2-btn" disabled={busy} onclick={() => (open = false)}
        >{ui('Cancel')}</button
      ><button
        type="button"
        class="v2-btn v2-btn-primary"
        disabled={busy || (scope === 'page' && !rows.length)}
        onclick={download}>{busy ? ui('Preparing export…') : ui('Export CSV')}</button
      >
    </div>
  </dialog>
{/if}

<style>
  dialog {
    width: min(30rem, calc(100vw - 2rem));
    max-height: calc(100dvh - 2rem);
    overflow: auto;
    margin: auto;
    padding: var(--crm-space-6);
    background: var(--crm-surface);
    color: var(--crm-text);
    border: 1px solid var(--crm-border);
    border-radius: var(--crm-radius-lg);
    box-shadow: var(--crm-shadow-lg);
  }
  dialog::backdrop {
    background: rgb(0 0 0 / 40%);
  }
  h2 {
    font-size: var(--crm-text-lg);
    margin: 0 0 var(--crm-space-3);
  }
  p,
  small {
    color: var(--crm-text-muted);
    font-size: var(--crm-text-sm);
  }
  fieldset {
    border: 0;
    padding: 0;
    margin: var(--crm-space-4) 0;
  }
  legend {
    font-weight: 600;
    margin-bottom: var(--crm-space-2);
  }
  label {
    display: flex;
    align-items: start;
    gap: var(--crm-space-3);
    padding: var(--crm-space-3);
    border: 1px solid var(--crm-border);
    border-radius: var(--crm-radius-md);
    margin-bottom: var(--crm-space-2);
    cursor: pointer;
  }
  label:has(input:checked) {
    border-color: var(--crm-primary);
    background: color-mix(in srgb, var(--crm-primary) 5%, var(--crm-surface));
  }
  input {
    margin-top: 0.25rem;
  }
  strong,
  small {
    display: block;
  }
  strong {
    font-size: var(--crm-text-sm);
  }
  small {
    margin-top: var(--crm-space-1);
  }
  .actions {
    display: flex;
    justify-content: flex-end;
    gap: var(--crm-space-2);
  }
</style>
