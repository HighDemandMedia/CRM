<script>
  import { page } from '$app/state';
  import { can } from '$lib/v2/permissions.js';
  import { Plus, Ellipsis } from '@lucide/svelte';
  import { resolve } from '$app/paths';
  import { deserialize } from '$app/forms';
  import { invalidateAll } from '$app/navigation';
  import { money, shortDate } from '$lib/v2/format.js';
  import { statusLabel, priorityLabel } from '$lib/components/tickets/options.js';
  import { STAGE_LABEL } from '$lib/v2/enums.js';
  /** @type {{contactId:string,kind:'company'|'deal'|'contact'|'ticket',items:any[],detailed?:boolean,summary?:import('svelte').Snippet,parentKind?:'contact'|'company'|'deal'}} */
  let { contactId, kind, items, detailed = false, summary, parentKind = 'contact' } = $props();
  const label = $derived(
    kind === 'company'
      ? 'Companies'
      : kind === 'deal'
        ? 'Deals'
        : kind === 'ticket'
          ? 'Tickets'
          : 'Contacts'
  );
  const editable = $derived(
    kind !== 'ticket' &&
      can(
        page.data.permissions,
        { contact: 'contacts', company: 'companies', deal: 'deals' }[parentKind],
        'associations'
      )
  );
  let adding = $state(false),
    search = $state(''),
    results = $state(/** @type {any[]} */ ([])),
    loading = $state(false),
    busy = $state(false),
    error = $state('');
  let menu = $state('');
  $effect(() => {
    if (!editable || !adding) return;
    const query = new URLSearchParams({ kind, search });
    const controller = new AbortController();
    loading = true;
    error = '';
    const timer = setTimeout(async () => {
      try {
        const response = await fetch(
          `${parentKind === 'contact' ? resolve(`/contacts/${contactId}/associations`) : resolve(`/record-associations/${parentKind}/${contactId}`)}?${query}`,
          {
            signal: controller.signal
          }
        );
        if (!response.ok) throw new Error();
        const data = await response.json();
        if (!controller.signal.aborted) results = data.results;
      } catch {
        if (!controller.signal.aborted) error = 'Could not load records.';
      } finally {
        if (!controller.signal.aborted) loading = false;
      }
    }, 200);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  });
  async function change(operation, target) {
    if (!editable || busy) return;
    busy = true;
    error = '';
    menu = '';
    try {
      const body = new FormData();
      body.set('operation', operation);
      body.set('target', target);
      body.set('kind', kind);
      const response = await fetch('?/association', {
        method: 'POST',
        body,
        headers: { 'x-sveltekit-action': 'true' }
      });
      const result = deserialize(await response.text());
      if (result.type !== 'success') {
        error =
          result.type === 'failure'
            ? String(result.data?.message || 'Could not update association.')
            : 'Could not update association.';
        return;
      }
      adding = false;
      search = '';
      await invalidateAll();
    } catch {
      error = 'Could not update association.';
    } finally {
      busy = false;
    }
  }
</script>

<section class="relations" aria-label={`Associated ${label.toLowerCase()}`}>
  <header class="association-heading">
    <h2>{label} <span>{items.length}</span></h2>
    {#if editable}<button
        class="add association-icon"
        type="button"
        disabled={busy}
        aria-label={`Add ${kind} association`}
        onclick={() => {
          adding = !adding;
          menu = '';
        }}><Plus size={16} /></button
      >{:else if parentKind !== 'deal'}
      <a
        class="add association-icon"
        aria-label="Create ticket"
        title="Create ticket"
        href={`${resolve('/tickets/new')}?${parentKind === 'company' ? 'account' : 'contact'}=${encodeURIComponent(contactId)}`}
        ><Plus size={16} /></a
      >
    {/if}
  </header>
  {#if summary}<div class="association-summary">{@render summary()}</div>{/if}
  {#if editable && adding}<div class="search-box">
      <input
        class="v2-input"
        aria-label={`Search ${label.toLowerCase()}`}
        placeholder={`Search ${label.toLowerCase()}…`}
        bind:value={search}
        disabled={busy}
      />
      <div class="results">
        {#if loading}<p>Searching…</p>{:else}{#each results as item}<button
              type="button"
              disabled={busy}
              onclick={() => change('add', item.id)}>{item.name}<span>+</span></button
            >{:else}<p>No available records.</p>{/each}{/if}
      </div>
    </div>{/if}
  {#each items as item (item.id)}<div class="record">
      <a
        href={kind === 'company'
          ? resolve(`/accounts/${item.id}`)
          : kind === 'deal'
            ? resolve(`/pipeline/${item.id}`)
            : kind === 'ticket'
              ? resolve(`/tickets/${item.id}`)
              : resolve(`/contacts/${item.id}`)}
        ><strong>{item.name}</strong>{#if detailed && kind === 'contact'}<small
            >{[item.email, item.phone].filter(Boolean).join(' · ') || 'No contact details'}</small
          >{/if}{#if detailed && kind === 'deal'}<span class="deal-details"
            ><span><small>Amount</small>{money(item.amount, item.currency)}</span><span
              ><small>Stage</small>{STAGE_LABEL[item.stage] ?? item.stage}</span
            ><span><small>Close date</small>{item.closed_on ? shortDate(item.closed_on) : '—'}</span
            ></span
          >{:else if kind === 'deal'}<small
            >{STAGE_LABEL[item.stage] ?? item.stage} · {money(item.amount, item.currency)}</small
          >{:else if kind === 'ticket'}<small
            >{statusLabel(item.status)}{#if item.priority}
              · {priorityLabel(item.priority)}{/if}</small
          >{/if}</a
      >
      {#if editable}<div
          class="record-actions"
          onfocusout={(e) => {
            if (!e.currentTarget.contains(/** @type {Node|null} */ (e.relatedTarget))) menu = '';
          }}
        >
          <button
            class="more association-icon"
            type="button"
            aria-label={`Actions for ${item.name}`}
            aria-expanded={menu === item.id}
            disabled={busy}
            onclick={() => (menu = menu === item.id ? '' : item.id)}><Ellipsis size={16} /></button
          >{#if menu === item.id}<button
              class="remove"
              type="button"
              disabled={busy}
              onclick={() => change('remove', item.id)}>Remove association</button
            >{/if}
        </div>{/if}
    </div>{:else}<p class="empty">
      No associated {label.toLowerCase()}.
    </p>{/each}
  {#if error}<p class="error" role="alert">{error}</p>{/if}
</section>

<style>
  .deal-details {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px 16px;
    margin-top: 6px;
    font-size: 12px;
  }
  .deal-details small {
    margin: 0 0 3px;
  }
  @media (max-width: 500px) {
    .deal-details {
      grid-template-columns: 1fr;
    }
  }
  .association-summary {
    margin: 0 0 12px;
  }
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 6px;
  }
  h2 {
    font-size: 14px;
    font-weight: 600;
    margin: 0;
  }
  h2 span {
    font-size: 11px;
    font-weight: 400;
    color: var(--v2-slate);
    margin-left: 5px;
  }
  .add,
  .more {
    border: 1px solid var(--v2-line);
    background: white;
    border-radius: 6px;
    cursor: pointer;
    min-width: 28px;
    height: 28px;
    font-size: 20px;
    color: var(--v2-ink);
  }
  .record {
    display: flex;
    align-items: center;
    gap: 8px;
    background: var(--v2-paper);
    border: 1px solid transparent;
    border-radius: 7px;
    padding: 10px;
    margin-top: 6px;
  }
  .record a {
    flex: 1;
    min-width: 0;
    text-decoration: none;
    color: var(--v2-ink);
  }
  strong {
    display: block;
    font-size: 13px;
    overflow-wrap: anywhere;
  }
  small {
    display: block;
    font-size: 11px;
    color: var(--v2-slate);
    margin-top: 5px;
  }
  .record-actions {
    position: relative;
  }
  .more {
    border: 0;
    background: transparent;
    line-height: 1;
  }
  .remove {
    position: absolute;
    right: 0;
    top: 30px;
    z-index: 5;
    white-space: nowrap;
    background: white;
    border: 1px solid var(--v2-line);
    border-radius: 6px;
    padding: 10px;
    color: #b42318;
    box-shadow: 0 4px 12px #0002;
    cursor: pointer;
  }
  .empty,
  .error,
  .results p {
    font-size: 12px;
    margin: 8px 0;
    color: var(--v2-slate);
  }
  .error {
    color: #b42318;
  }
  .search-box {
    margin-bottom: 10px;
  }
  .results {
    max-height: 180px;
    overflow: auto;
  }
  .results button {
    display: flex;
    justify-content: space-between;
    gap: 8px;
    width: 100%;
    text-align: left;
    background: white;
    border: 0;
    border-bottom: 1px solid var(--v2-line);
    padding: 9px 5px;
    font: inherit;
    font-size: 12px;
    cursor: pointer;
  }
  .record:hover {
    border-color: var(--v2-line);
  }
</style>
