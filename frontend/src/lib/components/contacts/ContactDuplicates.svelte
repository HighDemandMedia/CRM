<script>
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();

  import { resolve } from '$app/paths';
  import { tick } from 'svelte';
  import Notice from '$lib/components/Notice.svelte';
  import { contactDuplicateQuery } from './contact-duplicates.js';
  /** @type {{name?:string, email?:string, phone?:string, exclude?:string}} */
  let { name = '', email = '', phone = '', exclude = '' } = $props();
  let matches = $state([]),
    checking = $state(false),
    error = $state('');
  let dismissed = $state(false);
  let actionButton = $state(null);
  async function toggleDismissed() {
    dismissed = !dismissed;
    await tick();
    actionButton?.focus();
  }
  const query = $derived(contactDuplicateQuery({ name, email, phone, exclude }));
  $effect(() => {
    const currentQuery = query;
    matches = [];
    error = '';
    dismissed = false;
    if (!currentQuery) {
      checking = false;
      return;
    }
    const controller = new AbortController();
    checking = true;
    const timer = setTimeout(async () => {
      try {
        const response = await fetch(`/api/contacts/duplicates?${currentQuery}`, {
          signal: controller.signal
        });
        if (!response.ok) throw new Error('Could not check existing contacts.');
        const data = await response.json();
        if (!controller.signal.aborted) matches = data.results || [];
      } catch {
        if (!controller.signal.aborted) error = 'Could not check existing contacts.';
      } finally {
        if (!controller.signal.aborted) checking = false;
      }
    }, 450);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  });
</script>

{#if matches.length}
  <div class="matches">
    {#if dismissed}
      <button
        bind:this={actionButton}
        type="button"
        class="v2-btn v2-btn-quiet v2-btn-sm match-action"
        aria-expanded="false"
        onclick={toggleDismissed}>{ui('Review possible matches')}</button
      >
    {:else}
      <Notice tone="warning" title={ui('This contact may already exist')}>
        <ul class="match-list" aria-label={ui('Possible existing contacts')}>
          {#each matches as contact (contact.id)}
            <li>
              <a data-open-record href={resolve(`/contacts/${contact.id}`)}>
                <span class="match-name"
                  >{contact.name || ui('Contact')}<span class="open">{ui('Open contact →')}</span
                  ></span
                >
                {#if contact.email || contact.phone}
                  <span class="details"
                    >{[contact.email, contact.phone].filter(Boolean).join(' · ')}</span
                  >
                {/if}
                <span class="reasons">
                  {#each contact.reasons as reason (reason)}<span class="reason">{ui(reason)}</span
                    >{/each}
                </span>
              </a>
            </li>
          {/each}
        </ul>
        {#snippet actions()}
          <button
            bind:this={actionButton}
            type="button"
            class="v2-btn v2-btn-sm match-action"
            aria-expanded="true"
            onclick={toggleDismissed}>{ui('This is a different contact')}</button
          >
        {/snippet}
      </Notice>
    {/if}
  </div>
{:else if checking}<p class="lookup-status" role="status">{ui('Checking existing contacts…')}</p>
{:else if error}<p class="lookup-status" role="status">{ui(error)}</p>{/if}

<style>
  .matches {
    grid-column: 1/-1;
    min-width: 0;
  }
  .matches :global(.crm-notice) {
    margin: 0;
    background: color-mix(in srgb, var(--crm-warning-bg) 45%, var(--v2-card));
  }
  .matches :global(.notice-actions) {
    margin-top: var(--crm-space-3);
  }
  .match-action {
    font-size: var(--crm-text-sm);
    white-space: normal;
    text-align: start;
  }
  .match-list {
    display: grid;
    gap: var(--crm-space-2);
    list-style: none;
    margin: var(--crm-space-3) 0 0;
    padding: 0;
  }
  a {
    display: block;
    color: var(--v2-ink);
    text-decoration: none;
    padding: var(--crm-space-3);
    background: var(--v2-card);
    border: 1px solid var(--crm-border);
    border-radius: var(--crm-radius-sm);
  }
  a:hover {
    border-color: var(--crm-warning);
  }
  a:hover .match-name {
    text-decoration: underline;
  }
  .match-name {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: var(--crm-space-1) var(--crm-space-2);
    justify-content: space-between;
    font-weight: 600;
    font-size: var(--crm-text-sm);
    overflow-wrap: anywhere;
  }
  .open {
    font-size: var(--crm-text-xs);
    font-weight: 500;
    white-space: nowrap;
  }
  .details {
    display: block;
    font-size: var(--crm-text-xs);
    overflow-wrap: anywhere;
    margin-top: 3px;
    color: var(--v2-slate);
  }
  .reasons {
    display: flex;
    flex-wrap: wrap;
    gap: var(--crm-space-1);
    margin-top: var(--crm-space-2);
  }
  .reason {
    border-radius: var(--crm-radius-sm);
    padding: 2px 6px;
    background: var(--crm-warning-bg);
    color: var(--crm-warning);
    font-size: var(--crm-text-xs);
  }
  .lookup-status {
    grid-column: 1/-1;
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
    margin: 0;
  }
</style>
