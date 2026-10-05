<script>
  import * as Dialog from '$lib/components/ui/dialog/index.js';
  import { goto, invalidateAll } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { ArrowLeftRight, Search } from '@lucide/svelte';
  /** @type {{contact:any, onClose:()=>void}} */
  let { contact, onClose } = $props();
  let open = $state(true),
    query = $state(''),
    results = $state(/** @type {any[]} */ ([]));
  let primaryId = $state(''),
    preview = $state(/** @type {any} */ (null));
  let choices = $state(/** @type {Record<string,string>} */ ({}));
  let busy = $state(false),
    searching = $state(false),
    error = $state(''),
    confirmed = $state(false);
  $effect(() => {
    const text = query.trim();
    if (preview || text.length < 2) {
      results = [];
      searching = false;
      return;
    }
    const controller = new AbortController();
    searching = true;
    const timer = setTimeout(async () => {
      try {
        const response = await fetch(
          `/api/contacts/${contact.id}/merge/?q=${encodeURIComponent(text)}`,
          { signal: controller.signal }
        );
        const data = await response.json();
        if (!response.ok) throw new Error(data.error);
        if (!controller.signal.aborted) results = data.results;
      } catch (err) {
        if (!controller.signal.aborted) error = err.message || 'Could not find contacts.';
      } finally {
        if (!controller.signal.aborted) searching = false;
      }
    }, 250);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  });
  async function compare(secondary, primary = contact.id) {
    busy = true;
    error = '';
    confirmed = false;
    try {
      const response = await fetch(`/api/contacts/${primary}/merge/?secondary=${secondary}`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.error);
      primaryId = primary;
      preview = data;
      choices = Object.fromEntries(data.properties.map((row) => [row.key, row.default]));
    } catch (err) {
      error = err.message || 'Could not compare contacts.';
    } finally {
      busy = false;
    }
  }
  async function merge() {
    if (!confirmed || busy) return;
    busy = true;
    error = '';
    try {
      const response = await fetch(`/api/contacts/${primaryId}/merge/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: preview.token, choices, confirm: true })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error);
      open = false;
      onClose();
      await goto(resolve(`/contacts/${data.id}`));
      await invalidateAll();
    } catch (err) {
      error = err.message || 'Could not merge contacts.';
    } finally {
      busy = false;
    }
  }
  function display(value, row) {
    if (row.is_datetime && value) return new Date(value).toLocaleString();
    return value == null || value === ''
      ? '—'
      : typeof value === 'object'
        ? JSON.stringify(value)
        : String(value);
  }
</script>

<Dialog.Root
  bind:open
  onOpenChange={(value) => {
    if (!value) onClose();
  }}
>
  <Dialog.Content
    class="max-h-[90dvh] overflow-y-auto sm:max-w-3xl"
    showCloseButton={!busy}
    onInteractOutside={(event) => {
      if (busy) event.preventDefault();
    }}
    onEscapeKeydown={(event) => {
      if (busy) event.preventDefault();
    }}
  >
    <Dialog.Header>
      <Dialog.Title>Merge contacts</Dialog.Title>
      <Dialog.Description
        >{preview
          ? 'Choose which values to keep in the surviving contact.'
          : `Find the contact to merge with ${contact.name}.`}</Dialog.Description
      >
    </Dialog.Header>
    {#if !preview}
      <label class="search"
        ><Search size={16} /><input
          class="v2-input"
          aria-label="Find contact to merge"
          placeholder="Search name, email or phone…"
          bind:value={query}
          disabled={busy}
        /></label
      >
      <div class="matches">
        {#if searching}<p>Searching…</p>{:else}{#each results as result (result.id)}
            <button class="match" disabled={busy} onclick={() => compare(result.id)}
              ><strong>{result.name}</strong><span
                >{[result.email, result.phone].filter(Boolean).join(' · ') || result.id}</span
              ></button
            >
          {:else}{#if query.trim().length >= 2}<p>No matching contacts.</p>{/if}{/each}{/if}
      </div>
    {:else}
      <div class="records">
        <div>
          <small>Keep this contact and its ID</small><strong>{preview.primary.name}</strong><span
            >{preview.primary.id.slice(0, 8)}…{preview.primary.id.slice(-4)}</span
          >
        </div>
        <button
          class="v2-btn"
          disabled={busy}
          aria-label="Switch primary contact"
          title="Switch primary contact"
          onclick={() => compare(preview.primary.id, preview.secondary.id)}
          ><ArrowLeftRight size={16} /></button
        >
        <div>
          <small>Merge into the primary</small><strong>{preview.secondary.name}</strong><span
            >{preview.secondary.id.slice(0, 8)}…{preview.secondary.id.slice(-4)}</span
          >
        </div>
      </div>
      <div class="comparison">
        {#each preview.properties as row (row.key)}
          <fieldset disabled={busy}>
            <legend>{row.label}</legend>
            <div class="values">
              {#each ['primary', 'secondary'] as side}<label
                  class:chosen={choices[row.key] === side}
                  ><input
                    type="radio"
                    name={`merge-${row.key}`}
                    value={side}
                    bind:group={choices[row.key]}
                  /><span
                    ><small
                      >{side === 'primary' ? preview.primary.name : preview.secondary.name}</small
                    >{display(row[side], row)}</span
                  ></label
                >{/each}
            </div>
          </fieldset>
        {:else}<p>Both contacts have the same properties.</p>{/each}
      </div>
      <div class="consequences">
        Notes, files, activity, tags, owners and associations will be combined. The secondary
        contact will be archived and its old links will open the primary. Its portal access will
        end. There is no automatic undo.
      </div>
      <label class="confirmation"
        ><input type="checkbox" bind:checked={confirmed} disabled={busy} />I confirm these records
        represent the same contact.</label
      >
    {/if}
    {#if error}<p class="v2-error" role="alert">{error}</p>
      {#if preview}<button
          class="v2-btn"
          disabled={busy}
          onclick={() => compare(preview.secondary.id, preview.primary.id)}
          >Refresh comparison</button
        >{/if}{/if}
    <Dialog.Footer>
      <button
        class="v2-btn"
        disabled={busy}
        onclick={() => {
          open = false;
          onClose();
        }}>Cancel</button
      >
      {#if preview}<button
          class="v2-btn"
          disabled={busy}
          onclick={() => {
            preview = null;
            confirmed = false;
            error = '';
          }}>Choose another contact</button
        ><button class="v2-btn v2-btn-primary" disabled={busy || !confirmed} onclick={merge}
          >{busy ? 'Merging…' : 'Merge contacts'}</button
        >{/if}
    </Dialog.Footer>
  </Dialog.Content>
</Dialog.Root>

<style>
  .search {
    display: flex;
    align-items: center;
    gap: var(--crm-space-2);
  }
  .matches {
    max-height: 320px;
    overflow: auto;
  }
  .match {
    display: flex;
    flex-direction: column;
    width: 100%;
    text-align: left;
    padding: var(--crm-space-3);
    border: 0;
    border-bottom: 1px solid var(--v2-line);
    background: transparent;
    cursor: pointer;
    gap: var(--crm-space-1);
  }
  .match:hover {
    background: var(--v2-line-soft);
  }
  .match span,
  .records span,
  .records small {
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
  }
  .records {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    gap: 14px;
    align-items: center;
    padding: 14px;
    background: var(--v2-line-soft);
    border-radius: var(--crm-radius-md);
  }
  .records > div {
    display: flex;
    flex-direction: column;
    gap: 5px;
    overflow-wrap: anywhere;
  }
  .comparison {
    max-height: 40vh;
    overflow: auto;
  }
  fieldset {
    border: 0;
    border-bottom: 1px solid var(--v2-line);
    margin: 0 0 var(--crm-space-3);
    padding: 0 0 var(--crm-space-3);
    min-width: 0;
  }
  legend {
    font-weight: 600;
    font-size: var(--crm-text-sm);
    margin-bottom: 6px;
  }
  .values {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
  }
  .values label {
    display: flex;
    gap: var(--crm-space-2);
    align-items: flex-start;
    padding: 10px;
    border: 1px solid var(--v2-line);
    border-radius: var(--crm-radius-sm);
    cursor: pointer;
    overflow-wrap: anywhere;
    min-width: 0;
  }
  .values label.chosen {
    border-color: var(--v2-slate);
    background: var(--v2-line-soft);
  }
  .values small {
    display: block;
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
    margin-bottom: var(--crm-space-1);
  }
  .consequences {
    font-size: var(--crm-text-xs);
    line-height: 1.6;
    color: var(--v2-slate);
  }
  .confirmation {
    display: flex;
    align-items: center;
    gap: var(--crm-space-2);
    font-size: var(--crm-text-sm);
  }
</style>
