<script>
  import Notice from '$lib/components/Notice.svelte';
  import { untrack, onDestroy } from 'svelte';
  import { SvelteURLSearchParams } from 'svelte/reactivity';
  import { resolve } from '$app/paths';
  import { ArrowLeft, ListFilter } from '@lucide/svelte';
  import { useI18n } from '$lib/i18n/context.js';
  import EmailComposer from './EmailComposer.svelte';
  import EmailActivity from './EmailActivity.svelte';
  const { ui } = useI18n();
  /** @type {{kind:'contact'|'company',id:string,contacts?:any[],initialThread?:string,initialRequest?:number,composeRequest?:number,recipient?:string,active?:boolean,liveStatus?:any}} */
  let {
    kind,
    id,
    contacts = [],
    initialThread = '',
    initialRequest = 0,
    composeRequest = 0,
    recipient = '',
    active = true,
    liveStatus = null
  } = $props();
  let composing = $state(false);
  let thread = $state(''),
    search = $state(''),
    direction = $state('all'),
    contact = $state(''),
    dateFrom = $state(''),
    dateTo = $state('');
  let appliedSearch = $state('');
  let appliedDateFrom = '',
    appliedDateTo = '';
  let items = $state(/** @type {any[]} */ ([]));
  let connection = $state(/** @type {any} */ (null));
  let next = $state(/** @type {number|null} */ (null));
  let busy = $state(false),
    error = $state('');
  let appliedRevision = '';
  let attemptedStatus;
  let refreshing = $state(false);
  $effect(() => {
    if (liveStatus?.connection) connection = liveStatus.connection;
    if (
      active &&
      liveStatus?.revision &&
      liveStatus.revision !== appliedRevision &&
      liveStatus !== attemptedStatus &&
      !busy &&
      !refreshing
    ) {
      const revision = liveStatus.revision;
      untrack(() => {
        attemptedStatus = liveStatus;
        void load(false, true).then((success) => {
          if (success) appliedRevision = revision;
        });
      });
    }
  });
  let searchTimer;
  let controller,
    requestVersion = 0;
  const endpoint = $derived(`/api/record-mail/${kind}/${id}`);
  let handledComposeRequest = 0;
  $effect(() => {
    // Wait for mailbox permissions before opening the existing composer.
    if (active && composeRequest > handledComposeRequest && connection) {
      handledComposeRequest = composeRequest;
      if (connection.status === 'connected') composing = true;
    }
  });
  $effect(() => {
    const selected = initialThread;
    initialRequest;
    untrack(() => {
      thread = selected;
      void load();
    });
  });
  let lastLoaded = 0;
  $effect(() => {
    if (active)
      untrack(() => {
        if (error || (lastLoaded && Date.now() - lastLoaded > 60000)) void load();
      });
  });
  onDestroy(() => {
    requestVersion++;
    clearTimeout(searchTimer);
    controller?.abort();
  });
  async function load(more = false, quiet = false) {
    controller?.abort();
    controller = new AbortController();
    const version = ++requestVersion;
    if (quiet) refreshing = true;
    else busy = true;
    error = '';
    const loadedCount = items.length;
    if (!more && !quiet) {
      items = [];
      next = null;
    }
    const query = new SvelteURLSearchParams({ direction, q: appliedSearch, view: 'messages' });
    if (appliedDateFrom) query.set('date_from', appliedDateFrom);
    if (appliedDateTo) query.set('date_to', appliedDateTo);
    if (thread) query.set('thread', thread);
    if (contact) query.set('contact', contact);
    if (more && next !== null) query.set('offset', String(next));
    try {
      const response = await fetch(`${endpoint}?${query}`, { signal: controller.signal });
      if (!response.ok) throw new Error();
      const result = await response.json();
      if (version !== requestVersion) return;
      // Refresh all pages already loaded without clearing rows or collapsing messages.
      while (quiet && result.next_offset !== null && result.results.length < loadedCount) {
        query.set('offset', String(result.next_offset));
        const page = await fetch(`${endpoint}?${query}`, { signal: controller.signal });
        if (!page.ok) throw new Error();
        const extra = await page.json();
        if (version !== requestVersion) return;
        result.results.push(...extra.results);
        result.next_offset = extra.next_offset;
      }
      const combined = more ? [...items, ...result.results] : result.results;
      items = [...new Map(combined.map((item) => [item.id, item])).values()];
      lastLoaded = Date.now();
      connection = result.connection;
      next = result.next_offset;
      return true;
    } catch (err) {
      if (!quiet && version === requestVersion && err.name !== 'AbortError')
        error = 'Could not load emails. Please try again.';
    } finally {
      if (version === requestVersion) {
        busy = false;
        refreshing = false;
      }
    }
  }
  function filter(event) {
    event.preventDefault();
    clearTimeout(searchTimer);
    appliedSearch = search.trim();
    void load();
  }
  function datesChanged(event) {
    if (!event.currentTarget.form.reportValidity()) return;
    appliedDateFrom = dateFrom;
    appliedDateTo = dateTo;
    appliedSearch = search.trim();
    void load();
  }
  function clearFilters() {
    direction = 'all';
    contact = dateFrom = dateTo = appliedDateFrom = appliedDateTo = '';
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
  {#if connection && connection.status !== 'connected'}
    <a class="v2-btn v2-btn-sm" href={resolve('/profile?tab=integrations')}>
      {ui(connection.status === 'reconnect' ? 'Reconnect Gmail' : 'Connect Gmail')}
    </a>
  {/if}
  {#if connection?.error}<p class="v2-error" role="status">{ui(connection.error)}</p>{/if}
  {#if thread}
    <button type="button" class="v2-btn v2-btn-sm" onclick={() => openThread('')}
      ><ArrowLeft size={15} />{ui('All emails')}</button
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
          ><ListFilter size={15} />{ui(
            'Filters'
          )}{#if direction !== 'all' || contact || dateFrom || dateTo}<span
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
          <label
            >{ui('Start date')}<input
              class="v2-input"
              type="date"
              bind:value={dateFrom}
              max={dateTo || '9999-12-31'}
              onchange={datesChanged}
            /></label
          >
          <label
            >{ui('End date')}<input
              class="v2-input"
              type="date"
              bind:value={dateTo}
              min={dateFrom || '0001-01-01'}
              onchange={datesChanged}
            /></label
          >
          {#if direction !== 'all' || contact || dateFrom || dateTo}<button
              type="button"
              class="v2-btn v2-btn-sm"
              onclick={clearFilters}>{ui('Clear filters')}</button
            >{/if}
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
  {#if error}<Notice message={ui(error)} />
    <button
      class="v2-btn v2-btn-sm"
      type="button"
      onclick={() => load(items.length > 0 && next !== null)}>{ui('Try again')}</button
    >{/if}
  <div class="mail-list" aria-busy={busy}>
    {#each items as item (item.id)}
      <div class="mail-entry">
        <EmailActivity
          id={item.id}
          href={item.href}
          mail={item}
          {kind}
          recordId={id}
          onConversation={thread ? undefined : openThread}
          onchanged={() => void load()}
        />
        {#if kind === 'company' && item.contacts?.length}<div class="linked-contacts">
            {#each item.contacts as person (person.id)}<a href={resolve(`/contacts/${person.id}`)}
                >{person.name}</a
              >{/each}
          </div>{/if}
      </div>
    {:else}
      {#if !busy && !error}<p class="empty-mail">
          {ui(
            connection?.status === 'connected'
              ? 'No emails match this record and these filters.'
              : 'Connect Gmail to see your emails here.'
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
    max-height: 60vh;
    overflow-y: auto;
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
  .mail-entry {
    min-width: 0;
  }
  .linked-contacts {
    display: flex;
    gap: var(--crm-space-3);
    flex-wrap: wrap;
    padding: var(--crm-space-2) var(--crm-space-3) 0;
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
