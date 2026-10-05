<script>
  import { page } from '$app/state';
  import { can } from '$lib/v2/permissions.js';
  import { resolve } from '$app/paths';
  import { goto } from '$app/navigation';
  /** @type {{kind:'contact'|'company'|'deal',id:string,inFlow?:boolean}} */
  let { kind, id, inFlow = false } = $props();
  let dialog;
  let loading = $state(false),
    busy = $state(false),
    error = $state(''),
    confirmation = $state('');
  let includeAssociated = $state(false);
  let impact = $state(/** @type {any} */ (null));
  const endpoint = $derived(resolve(`/record-delete/${kind}/${id}`));
  async function open() {
    includeAssociated = false;
    dialog.showModal();
    await preview();
  }
  async function preview() {
    confirmation = '';
    error = '';
    impact = null;
    loading = true;
    try {
      const response = await fetch(`${endpoint}?include_associated=${includeAssociated}`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.message);
      impact = data;
    } catch (err) {
      error = err.message || 'Could not load deletion details.';
    } finally {
      loading = false;
    }
  }
  async function remove() {
    if (loading || busy || !impact || impact.blocked || confirmation !== (impact.name || impact.id))
      return;
    busy = true;
    error = '';
    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: impact.token, confirmation })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message);
      dialog.close();
      await goto(
        resolve(kind === 'contact' ? '/contacts' : kind === 'company' ? '/accounts' : '/pipeline'),
        { invalidateAll: true }
      );
    } catch (err) {
      error = err.message || 'Could not delete this record.';
    } finally {
      busy = false;
    }
  }
</script>

{#if can(page.data.permissions, { contact: 'contacts', company: 'companies', deal: 'deals' }[kind], 'delete')}<button
    class="v2-btn delete-trigger"
    class:in-flow={inFlow}
    type="button"
    onclick={open}>Delete</button
  >{/if}
<dialog
  bind:this={dialog}
  aria-labelledby={`delete-${kind}-title`}
  oncancel={(e) => {
    if (busy) e.preventDefault();
  }}
>
  <h2 id={`delete-${kind}-title`}>Delete {kind}?</h2>
  <label class="associated-option"
    ><input
      type="checkbox"
      bind:checked={includeAssociated}
      onchange={preview}
      disabled={busy || loading}
    /> Also delete directly associated contacts, companies and deals</label
  >
  <p>
    {includeAssociated
      ? 'Only directly associated records are included. Their other associated records will be kept.'
      : 'Keep associated records and remove their link to this record.'}
  </p>
  {#if loading}<p>Checking linked records…</p>{:else if impact}
    <p><strong>{impact.name || impact.id}</strong></p>
    {#if impact.blocked}<p role="alert">{impact.message}</p>{:else}
      <p>
        This permanently deletes the record and the following related data. This cannot be undone in
        the CRM.
      </p>
      {#if includeAssociated && impact.associated?.length}
        <p>Associated records to delete:</p>
        <ul>
          {#each impact.associated as record}<li>{record.name} ({record.kind})</li>{/each}
        </ul>
      {/if}
      <ul>
        {#each impact.counts as item}<li>{item.label}: <strong>{item.count}</strong></li>{/each}
      </ul>
      <p>
        Invoices, estimates and recurring invoices are kept with their stored details. Associations
        to surviving records will be removed. Any calendar events that survive will lose their link
        to this record.
      </p>
      <label
        >Type <strong>{impact.name || impact.id}</strong> to confirm<input
          class="v2-input"
          aria-label="Confirm record name"
          autocomplete="off"
          spellcheck="false"
          bind:value={confirmation}
          disabled={busy}
        /></label
      >
    {/if}
  {/if}
  {#if error}<p class="error" role="alert">{error}</p>{/if}
  <div class="buttons">
    <button class="v2-btn" type="button" disabled={busy} onclick={() => dialog.close()}
      >Cancel</button
    ><button
      class="v2-btn danger"
      type="button"
      disabled={loading ||
        busy ||
        !impact ||
        impact.blocked ||
        confirmation !== (impact.name || impact.id)}
      onclick={remove}>{busy ? 'Deleting…' : 'Delete permanently'}</button
    >
  </div>
</dialog>

<style>
  .associated-option {
    display: flex;
    align-items: flex-start;
    gap: var(--crm-space-2);
  }
  .associated-option input {
    width: auto;
    margin-top: var(--crm-space-1);
  }
  .delete-trigger {
    position: fixed;
    right: 24px;
    bottom: 16px;
    z-index: 10;
    background: var(--v2-bg, white);
    color: var(--crm-danger);
  }
  dialog {
    margin: auto;
    width: min(480px, calc(100vw - 32px));
    height: fit-content;
    max-height: 90vh;
    overflow: auto;
    padding: var(--crm-space-6);
    border: 1px solid var(--v2-line);
    border-radius: var(--crm-radius-lg);
    background: var(--v2-bg, white);
    color: var(--v2-ink);
    box-shadow: var(--crm-shadow-lg);
  }
  dialog::backdrop {
    background: var(--crm-overlay);
  }
  h2 {
    font-size: var(--crm-text-lg);
    margin: 0 0 var(--crm-space-4);
  }
  p,
  li,
  label {
    font-size: var(--crm-text-sm);
    line-height: 1.6;
  }
  ul {
    padding-left: var(--crm-space-5);
    max-height: 180px;
    overflow: auto;
  }
  label {
    display: block;
    margin-top: var(--crm-space-4);
  }
  input {
    margin-top: 6px;
    width: 100%;
  }
  .buttons {
    display: flex;
    gap: var(--crm-space-2);
    justify-content: flex-end;
    margin-top: var(--crm-space-6);
  }
  .danger {
    background: var(--crm-danger-bg);
    color: var(--crm-danger);
    border-color: var(--crm-danger);
  }
  .danger:disabled {
    opacity: 0.4;
  }
  .error {
    color: var(--crm-danger);
  }
  @media (max-width: 767px) {
    .delete-trigger {
      bottom: 76px;
      right: 82px;
    }
  }
  .delete-trigger.in-flow {
    position: static;
    display: flex;
    margin: 28px 0 0 auto;
    width: fit-content;
  }
</style>
