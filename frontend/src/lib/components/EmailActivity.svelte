<script>
  import Notice from '$lib/components/Notice.svelte';
  import EmailComposer from './EmailComposer.svelte';
  import EmailBody from './EmailBody.svelte';
  import { onDestroy } from 'svelte';
  import {
    ArrowDownLeft,
    ArrowUpRight,
    ExternalLink,
    Reply,
    ReplyAll,
    Forward,
    MessageSquare,
    ChevronRight
  } from '@lucide/svelte';
  import { useI18n } from '$lib/i18n/context.js';
  import { splitEmailBody, replyRecipients } from '$lib/v2/email-presentation.js';
  const { ui, exactTime } = useI18n();
  /** @type {{id:string,href?:string|null,mail?:any,onConversation?:(thread:string)=>void,kind?:string,recordId?:string,onchanged?:()=>void}} */
  let { id, href, mail = null, onConversation, kind, recordId, onchanged } = $props();
  let compose = $state('');
  let email = $state(/** @type {any} */ (null));
  let busy = $state(false),
    error = $state('');
  let controller;
  let content = $derived(splitEmailBody(email?.body || ''));
  let hasReplyAll = $derived(
    email &&
      (() => {
        const { to, cc } = replyRecipients(email, true);
        return to.length + cc.length > 1;
      })()
  );
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
          <span class="toggle-marker"><ChevronRight size={14} /></span>
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
    {#if error}<Notice message={ui(error)} />
      <button class="v2-btn v2-btn-sm" type="button" onclick={load}>{ui('Try again')}</button>{/if}
    {#if email}
      <details class="message-details">
        <summary>{ui('Message details')}</summary>
        <dl class="envelope">
          <dt>{ui('From:')}</dt>
          <dd>{email.sender}</dd>
          <dt>{ui('To:')}</dt>
          <dd>{email.recipients.join(', ') || ui('Undisclosed recipients')}</dd>
          {#if email.cc?.length}<dt>CC</dt>
            <dd>{email.cc.join(', ')}</dd>{/if}
        </dl>
      </details>
      <EmailBody text={content.text || ui('(Empty message)')} />
      {#if content.quoted}<details class="quoted">
          <summary>{ui('Show quoted text and signature')}</summary>
          <EmailBody text={content.quoted} />
        </details>{/if}
    {/if}
    <div class="email-actions">
      {#if email && kind && recordId}
        <div class="message-reply-actions">
          <button type="button" class="v2-btn v2-btn-sm" onclick={() => (compose = 'reply')}
            ><Reply size={16} />{ui('Reply')}</button
          >
          {#if hasReplyAll}<button
              type="button"
              class="v2-btn v2-btn-sm"
              onclick={() => (compose = 'reply-all')}
              ><ReplyAll size={16} />{ui('Reply all')}</button
            >{/if}
          <button type="button" class="v2-btn v2-btn-sm" onclick={() => (compose = 'forward')}
            ><Forward size={16} />{ui('Forward')}</button
          >
          <button type="button" class="v2-btn v2-btn-sm" onclick={() => (compose = 'comment')}
            ><MessageSquare size={16} />{ui('Internal comment')}</button
          >
        </div>
      {/if}
      {#if onConversation && mail?.thread_id}<button
          type="button"
          class="v2-btn v2-btn-sm"
          onclick={() => onConversation(mail.thread_id)}>{ui('View conversation')}</button
        >{/if}
      {#if href}<a {href} target="_blank" rel="external noopener noreferrer"
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
    padding: var(--crm-space-2) var(--crm-space-3);
    overflow-wrap: anywhere;
  }
  summary:focus-visible {
    outline: 2px solid var(--v2-ink);
    outline-offset: 2px;
  }
  .email-message > summary {
    list-style: none;
  }
  .email-message > summary::-webkit-details-marker {
    display: none;
  }
  .toggle-marker {
    display: inline-flex;
  }
  .email-message[open] .toggle-marker {
    transform: rotate(90deg);
  }
  summary strong,
  .participants {
    display: block;
    margin-top: var(--crm-space-1);
  }
  .email-heading,
  .direction,
  .message-reply-actions,
  .email-actions {
    display: flex;
    align-items: center;
    gap: var(--crm-space-2);
    flex-wrap: wrap;
  }
  .email-heading {
    justify-content: space-between;
    font-size: var(--crm-text-xs);
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
    padding: 0 var(--crm-space-3) var(--crm-space-3);
  }
  .envelope {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    gap: var(--crm-space-1) var(--crm-space-2);
    margin-block: var(--crm-space-2);
  }
  dd {
    margin: 0;
    overflow-wrap: anywhere;
  }
  .quoted {
    margin-top: var(--crm-space-2);
    color: var(--v2-slate);
  }
  .quoted summary,
  .message-details summary {
    padding: var(--crm-space-1) 0;
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
  }
  .message-details {
    margin-bottom: var(--crm-space-2);
  }
  .email-actions {
    margin-top: var(--crm-space-2);
    padding-top: var(--crm-space-2);
    border-top: 1px solid var(--v2-line-soft);
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
