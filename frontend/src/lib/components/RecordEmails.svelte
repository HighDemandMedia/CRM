<script>
  import { onMount, onDestroy } from 'svelte';
  import { SvelteURLSearchParams } from 'svelte/reactivity';
  import { resolve } from '$app/paths';
  import { Mail, ArrowLeft, ListFilter } from '@lucide/svelte';
  import { useI18n } from '$lib/i18n/context.js';
  import EmailComposer from './EmailComposer.svelte';
  import EmailActivity from './EmailActivity.svelte';
  const { ui, exactTime } = useI18n();
  /** @type {{kind:'contact'|'company',id:string,contacts?:any[],initialThread?:string,recipient?:string}} */
  let { kind, id, contacts = [], initialThread = '', recipient = '' } = $props();
  let composing = $state(false);
  let thread = $state(''),
    search = $state(''),
    direction = $state('all'),
    contact = $state('');
  let appliedSearch = $state('');
  let items = $state(/** @type {any[]} */ ([]));
  let connection = $state(/** @type {any} */ (null));
  let next = $state(/** @type {number|null} */ (null));
  let busy = $state(false),
    error = $state('');
  let searchTimer;
  let controller,
    requestVersion = 0;
  const endpoint = $derived(`/api/record-mail/${kind}/${id}`);
  onMount(() => {
    thread = initialThread;
    void load();
  });
  onDestroy(() => {
    requestVersion++;
    clearTimeout(searchTimer);
    controller?.abort();
  });
  async function load(more = false) {
    controller?.abort();
    controller = new AbortController();
    const version = ++requestVersion;
    busy = true;
    error = '';
    if (!more) {
      items = [];
      next = null;
    }
    const query = new SvelteURLSearchParams({ direction, q: appliedSearch });
    if (thread) query.set('thread', thread);
    if (contact) query.set('contact', contact);
    if (more && next !== null) query.set('offset', String(next));
    try {
      const response = await fetch(`${endpoint}?${query}`, { signal: controller.signal });
      if (!response.ok) throw new Error();
      const result = await response.json();
      if (version !== requestVersion) return;
      const combined = more ? [...items, ...result.results] : result.results;
      items = [
        ...new Map(combined.map((item) => [thread ? item.id : item.thread_id, item])).values()
      ];
      connection = result.connection;
      next = result.next_offset;
    } catch (err) {
      if (version === requestVersion && err.name !== 'AbortError')
        error = 'Could not load emails. Please try again.';
    } finally {
      if (version === requestVersion) busy = false;
    }
  }
  function filter(event) {
    event.preventDefault();
    clearTimeout(searchTimer);
    appliedSearch = search.trim();
    void load();
  }
  function openThread(value) {
    thread = value;
    void load();
  }
  function searchChanged() {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      appliedSearch = search.trim();
      void load();
    }, 350);
  }
</script>

<section class="record-emails" aria-label={ui('Emails')}>
  <div class="mail-status">
    <div>
      <strong><Mail size={16} /> {connection?.email || ui('Gmail')}</strong>
      <p>{ui('Only you can see your connected mailbox.')}</p>
      {#if connection?.last_sync}<p>{ui('Last sync:')} {exactTime(connection.last_sync)}</p>{/if}
    </div>
    {#if connection?.status === 'connected'}<button
        type="button"
        class="v2-btn v2-btn-primary v2-btn-sm"
        onclick={() => (composing = true)}>{ui('New email')}</button
      >{/if}
    {#if connection && connection.status !== 'connected'}
      <a class="v2-btn v2-btn-sm" href={resolve('/profile?tab=integrations')}
        >{ui(connection.status === 'reconnect' ? 'Reconnect Gmail' : 'Connect Gmail')}</a
      >
    {/if}
  </div>
  {#if connection?.error}<p class="v2-error" role="status">{ui(connection.error)}</p>{/if}
  {#if thread}
    <button type="button" class="v2-btn v2-btn-sm" onclick={() => openThread('')}
      ><ArrowLeft size={15} />{ui('All conversations')}</button
    >
    <p class="v2-sub">{ui('Messages shown oldest first.')}</p>
  {:else}
    <form class="mail-filters" onsubmit={filter}>
      <input
        class="v2-input mail-search"
        aria-label={ui('Search emails')}
        bind:value={search}
        oninput={searchChanged}
        maxlength="200"
        type="search"
        placeholder={ui('Search emails')}
      />
      <details class="mail-filter-menu">
        <summary class="v2-btn v2-btn-sm"
          ><ListFilter size={15} />{ui('Filters')}{#if direction !== 'all' || contact}<span
              aria-label={ui('Active filters')}>•</span
            >{/if}</summary
        >
        <div class="filter-options">
          <label
            >{ui('Direction')}<select
              class="v2-input"
              bind:value={direction}
              onchange={() => {
                appliedSearch = search.trim();
                void load();
              }}
            >
              <option value="all">{ui('All emails')}</option><option value="received"
                >{ui('Received')}</option
              ><option value="sent">{ui('Sent')}</option>
            </select></label
          >
          {#if kind === 'company'}<label
              >{ui('Contact')}<select
                class="v2-input"
                bind:value={contact}
                onchange={() => {
                  appliedSearch = search.trim();
                  void load();
                }}
              >
                <option value="">{ui('All contacts')}</option
                >{#each contacts as person (person.id)}<option value={person.id}
                    >{[person.first_name, person.last_name].filter(Boolean).join(' ') ||
                      person.name ||
                      person.email}</option
                  >{/each}
              </select></label
            >{/if}
        </div>
      </details>
    </form>
  {/if}
  {#if error}<p class="v2-error" role="alert">{ui(error)}</p>
    <button
      class="v2-btn v2-btn-sm"
      type="button"
      onclick={() => load(items.length > 0 && next !== null)}>{ui('Try again')}</button
    >{/if}
  <div class="mail-list" aria-busy={busy}>
    {#each items as item (thread ? item.id : item.thread_id)}
      {#if thread}<EmailActivity
          id={item.id}
          href={item.href}
          mail={item}
          {kind}
          recordId={id}
          onchanged={() => void load()}
        />
      {:else}<article class="conversation">
          <button
            type="button"
            class="conversation-open"
            onclick={() => openThread(item.thread_id)}
          >
            <span class="conversation-meta"
              ><span>{ui(item.direction === 'sent' ? 'Sent' : 'Received')}</span><time
                datetime={item.at}>{exactTime(item.at)}</time
              ></span
            >
            <strong>{item.subject || ui('(No subject)')}</strong>
            <span class="participants"
              >{item.sender} → {item.recipients.join(', ') || ui('Undisclosed recipients')}</span
            >
            <span class="conversation-meta"
              >{ui(item.message_count === 1 ? '1 message' : '{count} messages', {
                count: item.message_count
              })} · {ui('View conversation')}</span
            >
          </button>
          {#if kind === 'company' && item.contacts?.length}<div class="linked-contacts">
              {#each item.contacts as person (person.id)}<a href={resolve(`/contacts/${person.id}`)}
                  >{person.name}</a
                >{/each}
            </div>{/if}
        </article>{/if}
    {:else}
      {#if !busy && !error}<p class="empty-mail">
          {ui(
            connection?.status === 'connected'
              ? 'No conversations match this record and these filters.'
              : 'Connect Gmail to see your conversations here.'
          )}
        </p>{/if}
    {/each}
  </div>
  {#if busy}<p class="v2-sub" role="status">{ui('Loading emails…')}</p>{/if}
  {#if next !== null}<button type="button" class="v2-btn" onclick={() => load(true)} disabled={busy}
      >{ui('Load more')}</button
    >{/if}
</section>

{#if composing}<EmailComposer
    {kind}
    recordId={id}
    mode="send"
    canSend={connection?.can_send ?? false}
    account={connection?.email || ''}
    {recipient}
    onclose={() => (composing = false)}
    ondone={() => void load()}
  />{/if}

<style>
  .record-emails,
  .mail-list {
    display: grid;
    gap: var(--crm-space-3);
    min-width: 0;
  }
  .mail-status {
    display: flex;
    justify-content: space-between;
    gap: var(--crm-space-3);
    flex-wrap: wrap;
    padding-bottom: var(--crm-space-3);
    border-bottom: 1px solid var(--v2-line);
  }
  .mail-status strong {
    display: flex;
    align-items: center;
    gap: var(--crm-space-2);
    flex-wrap: wrap;
  }
  .mail-status p,
  .conversation-meta,
  .participants {
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
  }
  .mail-status p {
    margin: var(--crm-space-2) 0 0;
  }
  .mail-filters {
    display: flex;
    align-items: end;
    gap: var(--crm-space-2);
    flex-wrap: wrap;
  }
  label {
    flex: 1 1 8rem;
    min-width: 0;
    font-size: var(--crm-text-xs);
    display: grid;
    gap: var(--crm-space-2);
  }
  .mail-search {
    flex: 1 1 10rem;
  }
  .mail-filter-menu {
    position: relative;
  }
  .mail-filter-menu summary {
    list-style: none;
    cursor: pointer;
  }
  .mail-filter-menu summary::-webkit-details-marker {
    display: none;
  }
  .filter-options {
    position: absolute;
    right: 0;
    top: calc(100% + var(--crm-space-2));
    z-index: 5;
    width: min(16rem, 75vw);
    padding: var(--crm-space-3);
    display: grid;
    gap: var(--crm-space-3);
    background: var(--v2-card);
    border: 1px solid var(--v2-line);
    border-radius: var(--crm-radius-md);
  }
  .mail-filters > .mail-search {
    width: auto;
  }
  .v2-input {
    width: 100%;
    min-width: 0;
  }
  .conversation {
    border: 1px solid var(--v2-line);
    border-radius: var(--crm-radius-md);
    background: var(--v2-card);
    overflow: hidden;
  }
  .conversation-open {
    padding: var(--crm-space-4);
    display: grid;
    gap: var(--crm-space-2);
    width: 100%;
    text-align: left;
    background: none;
    border: none;
    font: inherit;
    color: var(--v2-ink);
    cursor: pointer;
    overflow-wrap: anywhere;
  }
  .conversation-open:hover {
    background: var(--v2-bg);
  }
  .conversation-open:focus-visible {
    outline: 2px solid var(--v2-ink);
    outline-offset: -3px;
  }
  .conversation-meta {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    gap: var(--crm-space-2);
  }
  .linked-contacts {
    display: flex;
    gap: var(--crm-space-3);
    flex-wrap: wrap;
    padding: 0 var(--crm-space-4) var(--crm-space-3);
    font-size: var(--crm-text-xs);
  }
  .linked-contacts a {
    text-decoration: underline;
  }
  .empty-mail {
    padding: var(--crm-space-5) 0;
    color: var(--v2-slate);
    font-size: var(--crm-text-sm);
  }
</style>
