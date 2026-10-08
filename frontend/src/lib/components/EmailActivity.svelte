<script>
  import EmailComposer from './EmailComposer.svelte';
  import { onDestroy } from 'svelte';
  import { ArrowDownLeft, ArrowUpRight, ExternalLink } from '@lucide/svelte';
  import { useI18n } from '$lib/i18n/context.js';
  import { splitEmailBody } from '$lib/v2/email-presentation.js';
  const { ui, exactTime } = useI18n();
  /** @type {{id:string,href?:string|null,mail?:any,onConversation?:(thread:string)=>void,kind?:string,recordId?:string,onchanged?:()=>void}} */
  let { id, href, mail = null, onConversation, kind, recordId, onchanged } = $props();
  let compose = $state('');
  let email = $state(/** @type {any} */ (null));
  let busy = $state(false),
    error = $state('');
  let controller;
  let content = $derived(splitEmailBody(email?.body || ''));
  onDestroy(() => controller?.abort());
  async function load() {
    if (email || busy) return;
    controller = new AbortController();
    busy = true;
    error = '';
    try {
      const response = await fetch(`/api/google-mail/${id}`, { signal: controller.signal });
      if (!response.ok) throw new Error('Email unavailable or access denied.');
      email = await response.json();
    } catch (err) {
      if (err.name !== 'AbortError') error = 'Could not load email.';
    } finally {
      busy = false;
    }
  }
</script>

<details
  class="email-message"
  ontoggle={(event) => {
    if (event.currentTarget.open) void load();
  }}
>
  <summary>
    {#if mail}
      <span class="email-heading">
        <span class="direction">
          {#if mail.direction === 'sent'}<ArrowUpRight size={16} />{ui('Sent')}{:else}<ArrowDownLeft
              size={16}
            />{ui('Received')}{/if}
        </span>
        <time datetime={mail.at}>{exactTime(mail.at)}</time>
      </span>
      <strong>{mail.subject || ui('(No subject)')}</strong>
      <span class="participants"
        >{mail.sender} → {(mail.recipients ?? []).join(', ') || ui('Undisclosed recipients')}</span
      >
    {:else}{ui('Read email')}{/if}
  </summary>
  <div class="message-content" aria-busy={busy}>
    {#if busy}<p role="status">{ui('Loading email…')}</p>{/if}
    {#if error}<p class="v2-error" role="alert">{ui(error)}</p>
      <button class="v2-btn v2-btn-sm" type="button" onclick={load}>{ui('Try again')}</button>{/if}
    {#if email}
      <dl class="envelope">
        <dt>{ui('From:')}</dt>
        <dd>{email.sender}</dd>
        <dt>{ui('To:')}</dt>
        <dd>{email.recipients.join(', ') || ui('Undisclosed recipients')}</dd>
        {#if email.cc?.length}<dt>CC</dt>
          <dd>{email.cc.join(', ')}</dd>{/if}
      </dl>
      <div class="email-body">{content.text || ui('(Empty message)')}</div>
      {#if content.quoted}<details class="quoted">
          <summary>{ui('Show quoted text and signature')}</summary>
          <div class="email-body">{content.quoted}</div>
        </details>{/if}
    {/if}
    <div class="email-actions">
      {#if email && kind && recordId}
        {#each ['reply', 'forward', 'comment'] as mode (mode)}
          <button type="button" class="v2-btn v2-btn-sm" onclick={() => (compose = mode)}
            >{ui(
              mode === 'reply' ? 'Reply' : mode === 'forward' ? 'Forward' : 'Internal comment'
            )}</button
          >
        {/each}
      {/if}
      {#if onConversation && mail?.thread_id}<button
          type="button"
          class="v2-btn v2-btn-sm"
          onclick={() => onConversation(mail.thread_id)}>{ui('View conversation')}</button
        >{/if}
      {#if href}<a {href} target="_blank" rel="noopener noreferrer"
          >{ui('Open in Gmail')} <ExternalLink size={13} /></a
        >{/if}
    </div>
  </div>
</details>

{#if compose && kind && recordId}
  <EmailComposer
    {kind}
    {recordId}
    mode={compose}
    canSend={email?.can_send ?? false}
    account={email?.account || ''}
    message={{ ...mail, ...email, id }}
    onclose={() => (compose = '')}
    ondone={onchanged}
  />
{/if}

<style>
  .email-message {
    border: 1px solid var(--v2-line);
    border-radius: var(--crm-radius-md);
    background: var(--v2-card);
    min-width: 0;
  }
  summary {
    cursor: pointer;
    padding: var(--crm-space-3) var(--crm-space-4);
    overflow-wrap: anywhere;
  }
  summary:focus-visible {
    outline: 2px solid var(--v2-ink);
    outline-offset: 2px;
  }
  summary strong,
  .participants {
    display: block;
    margin-top: var(--crm-space-2);
  }
  .email-heading,
  .direction,
  .email-actions {
    display: flex;
    align-items: center;
    gap: var(--crm-space-2);
    flex-wrap: wrap;
  }
  .email-heading {
    justify-content: space-between;
  }
  .direction {
    font-weight: 600;
  }
  time,
  .participants,
  .envelope {
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
  }
  .message-content {
    padding: 0 var(--crm-space-4) var(--crm-space-4);
  }
  .envelope {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    gap: var(--crm-space-2);
  }
  dd {
    margin: 0;
    overflow-wrap: anywhere;
  }
  .email-body {
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    line-height: 1.65;
    font-size: var(--crm-text-sm);
  }
  .quoted {
    margin-top: var(--crm-space-3);
    color: var(--v2-slate);
  }
  .quoted summary {
    padding: var(--crm-space-2) 0;
    font-size: var(--crm-text-xs);
  }
  .email-actions {
    margin-top: var(--crm-space-4);
    justify-content: space-between;
  }
  .email-actions a {
    display: inline-flex;
    align-items: center;
    gap: var(--crm-space-2);
    text-decoration: underline;
    font-size: var(--crm-text-xs);
  }
</style>
