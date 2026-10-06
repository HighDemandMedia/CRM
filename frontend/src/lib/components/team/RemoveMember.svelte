<script>
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();

  import { invalidateAll } from '$app/navigation';
  import { resolve } from '$app/paths';
  let { id, hideTrigger = false } = $props();
  let dialog;
  let preview = $state(null),
    loading = $state(false),
    busy = $state(false),
    error = $state(''),
    confirmation = $state(''),
    reassign = $state('');
  export async function open() {
    preview = null;
    error = '';
    confirmation = '';
    reassign = '';
    loading = true;
    dialog.showModal();
    try {
      const response = await fetch(resolve(`/team/${id}/remove`));
      const data = await response.json();
      if (!response.ok) throw new Error(data.message);
      preview = data;
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  }
  async function remove() {
    if (!preview || confirmation !== preview.email || busy) return;
    busy = true;
    error = '';
    try {
      const response = await fetch(resolve(`/team/${id}/remove`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: preview.token, confirmation, reassign_to: reassign || null })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message);
      dialog.close();
      await invalidateAll();
    } catch (err) {
      error = err.message;
    } finally {
      busy = false;
    }
  }
</script>

{#if !hideTrigger}<button class="v2-btn v2-btn-sm danger" type="button" onclick={open}
    >{ui('Remove')}</button
  >{/if}
<dialog
  bind:this={dialog}
  aria-labelledby={`remove-member-${id}`}
  oncancel={(e) => {
    if (busy) e.preventDefault();
  }}
>
  <h2 id={`remove-member-${id}`}>{ui('Remove from organization')}</h2>
  {#if loading}<p>{ui('Loading assigned records…')}</p>{:else if preview}
    <p>
      <strong>{preview.name}</strong>
      {ui(
        'will lose access to this organization. Their account and access to other organizations will remain.'
      )}
    </p>
    <p>
      {ui(
        'Records, history and meetings are kept. Team membership and access tokens for this organization are removed.'
      )}
    </p>
    <div class="counts">
      {#each Object.entries(preview.counts) as [label, count]}<span
          >{label}: <strong>{count}</strong></span
        >{/each}
    </div>
    <label
      >{ui('Reassign their records to')}<select
        class="v2-input"
        bind:value={reassign}
        disabled={busy}
        ><option value="">{ui('Remove their assignment only')}</option
        >{#each preview.candidates as person}<option value={person.id}
            >{person.name}{preview.candidates.filter((p) => p.name === person.name).length > 1
              ? ` · ${person.email}`
              : ''}</option
          >{/each}</select
      ></label
    >
    <p class="hint">
      {ui(
        'Other assigned users stay assigned. Without a replacement, records with no remaining owner become unassigned.'
      )}
    </p>
    <label
      >{ui('Type')} <strong>{preview.email}</strong>
      {ui('to confirm')}<input
        class="v2-input"
        aria-label={ui('Confirm user email')}
        bind:value={confirmation}
        disabled={busy}
        autocomplete="off"
        spellcheck="false"
      /></label
    >
  {/if}
  {#if error}<p class="error" role="alert">{ui(error)}</p>{/if}
  <div class="actions">
    <button class="v2-btn" type="button" disabled={busy} onclick={() => dialog.close()}
      >{ui('Cancel')}</button
    ><button
      class="v2-btn danger"
      type="button"
      disabled={loading || busy || !preview || confirmation !== preview.email}
      onclick={remove}>{busy ? ui('Removing…') : ui('Remove from organization')}</button
    >
  </div>
</dialog>

<style>
  dialog {
    width: min(520px, calc(100vw - 32px));
    max-height: 85vh;
    overflow: auto;
    border: 1px solid var(--v2-line-soft);
    border-radius: var(--crm-radius-xl);
    padding: var(--crm-space-6);
    color: var(--v2-ink);
    background: var(--v2-white, var(--crm-surface));
    text-align: left;
  }
  dialog::backdrop {
    background: var(--crm-overlay);
  }
  h2 {
    font-size: var(--crm-text-lg);
    margin: 0 0 18px;
  }
  p {
    font-size: var(--crm-text-sm);
    line-height: 1.6;
  }
  label {
    display: grid;
    gap: var(--crm-space-2);
    font-size: var(--crm-text-sm);
    margin: 18px 0;
  }
  .counts {
    display: flex;
    flex-wrap: wrap;
    gap: var(--crm-space-3);
    font-size: var(--crm-text-xs);
    padding: var(--crm-space-3) 0;
  }
  .hint {
    color: var(--v2-slate);
    font-size: var(--crm-text-xs);
  }
  .actions {
    display: flex;
    justify-content: flex-end;
    gap: var(--crm-space-2);
    margin-top: var(--crm-space-6);
  }
  .danger,
  .error {
    color: var(--v2-rust, var(--crm-danger));
  }
</style>
