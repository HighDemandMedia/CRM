<script>
  import Notice from '$lib/components/Notice.svelte';
  import { toast } from 'svelte-sonner';
  import { resolve } from '$app/paths';
  import { onMount } from 'svelte';
  import { invalidateAll } from '$app/navigation';
  import { Dialog } from 'bits-ui';
  import X from '@lucide/svelte/icons/x';
  import Maximize from '@lucide/svelte/icons/maximize-2';
  import Minimize from '@lucide/svelte/icons/minimize-2';
  import Paperclip from '@lucide/svelte/icons/paperclip';
  import EmailEditor from './EmailEditor.svelte';
  import { mailAttachmentError, mailFileSize } from '$lib/v2/mail-composition.js';
  import { useI18n } from '$lib/i18n/context.js';
  import { replyRecipients } from '$lib/v2/email-presentation.js';
  import EmailBody from './EmailBody.svelte';
  const { ui } = useI18n();
  /** @type {{kind:string,recordId:string,mode:string,message?:any,recipient?:string,canSend?:boolean,account?:string,onclose:()=>void,ondone?:()=>void}} */
  let {
    kind,
    recordId,
    mode,
    message = null,
    recipient = '',
    canSend = true,
    account = '',
    onclose,
    ondone
  } = $props();
  let open = $state(true),
    busy = $state(false),
    error = $state(''),
    locked = $state(false);
  let to = $state(''),
    cc = $state(''),
    bcc = $state(''),
    bodyHtml = $state(''),
    subject = $state(''),
    body = $state('');
  let requestId = '';
  let showCc = $state(false);
  let showBcc = $state(false);
  let expanded = $state(false);
  let initialized = $state(false);
  let discard = $state(false);
  let dirty = $state(false);
  let files = $state(/** @type {File[]} */ ([]));
  let fileInput = $state();
  let toInput = $state();
  const disabled = $derived(busy || locked || (mode !== 'comment' && !canSend));
  function close() {
    if (busy) return;
    if (dirty && !discard && !locked) {
      discard = true;
      return;
    }
    open = false;
    onclose();
  }
  function addFiles(event) {
    const selected = [...files, ...Array.from(event.currentTarget.files || [])];
    const issue = mailAttachmentError(selected);
    if (issue) error = issue;
    else {
      files = selected;
      error = '';
      dirty = true;
    }
    event.currentTarget.value = '';
  }
  const isReply = $derived(mode === 'reply' || mode === 'reply-all');
  const title = $derived(
    mode === 'comment'
      ? 'Internal comment'
      : mode === 'reply-all'
        ? 'Reply all'
        : mode === 'reply'
          ? 'Reply'
          : mode === 'forward'
            ? 'Forward'
            : 'New email'
  );
  onMount(() => {
    requestId = crypto.randomUUID();
    if (isReply) {
      const recipients = replyRecipients({ ...message, account }, mode === 'reply-all');
      to = recipients.to.join(', ');
      cc = recipients.cc.join(', ');
      showCc = Boolean(cc);
    } else to = mode === 'send' ? recipient : '';
    subject = isReply ? message.subject : mode === 'forward' ? `Fwd: ${message.subject || ''}` : '';
    if (mode === 'forward')
      body = `\n\n---------- Forwarded message ----------\nFrom: ${message.sender}\nTo: ${message.recipients.join(', ')}\nSubject: ${message.subject || ''}\n\n${message.body || ''}`;
    initialized = true;
  });
  function addresses(value) {
    return value
      .split(/[,;]+/)
      .map((v) => v.trim())
      .filter(Boolean);
  }
  async function submit(event) {
    event.preventDefault();
    if (busy || locked || (mode !== 'comment' && !canSend)) return;
    if (body.length > (mode === 'comment' ? 8000 : 100000)) {
      error = 'Message is too long.';
      return;
    }
    busy = true;
    error = '';
    const payload = {
      action: isReply ? 'reply' : mode,
      request_id: requestId,
      message: message?.id,
      to: addresses(to),
      cc: addresses(cc),
      bcc: addresses(bcc),
      subject,
      body,
      ...(mode !== 'comment' && bodyHtml ? { body_html: bodyHtml } : {})
    };
    const form = new FormData();
    form.set('payload', JSON.stringify(payload));
    files.forEach((file) => form.append('attachments', file));
    try {
      const response = await fetch(`/api/record-mail/${kind}/${recordId}/actions`, {
        method: 'POST',
        ...(files.length ? {} : { headers: { 'Content-Type': 'application/json' } }),
        body: files.length ? form : JSON.stringify(payload)
      });
      const result = await response.json();
      if (!response.ok) {
        locked = mode !== 'comment' && [409, 503].includes(response.status);
        error = result.error || 'Could not save changes.';
        return;
      }
      // Closing occurs only after acknowledgement. A refresh failure must not offer to resend.
      open = false;
      onclose();
      ondone?.();
      toast.success(ui(mode === 'comment' ? 'Comment saved.' : 'Email sent.'));
      void invalidateAll().catch(() => toast.info(ui('Reload the page to update activity.')));
    } catch {
      locked = true;
      error =
        mode === 'comment'
          ? 'Could not confirm the comment. Check Notes before trying again.'
          : 'Sending could not be confirmed. Check Gmail Sent before trying again.';
    } finally {
      busy = false;
    }
  }
</script>

<Dialog.Root
  bind:open
  onOpenChange={(value) => {
    if (!value) {
      open = true;
      close();
    }
  }}
>
  <Dialog.Portal>
    <Dialog.Overlay class="composer-backdrop" />
    <Dialog.Content
      class={`email-composer ${expanded ? 'is-expanded' : ''}`}
      onOpenAutoFocus={(event) => {
        event.preventDefault();
        toInput?.focus();
      }}
      onInteractOutside={(event) => event.preventDefault()}
      onEscapeKeydown={(event) => {
        event.preventDefault();
        close();
      }}
    >
      <header class="composer-header">
        <Dialog.Title class="composer-title">{ui(title)}</Dialog.Title>
        <div class="header-actions">
          <button
            type="button"
            class="icon-button"
            aria-label={ui(expanded ? 'Compact view' : 'Expand')}
            title={ui(expanded ? 'Compact view' : 'Expand')}
            onclick={() => (expanded = !expanded)}
          >
            {#if expanded}<Minimize size={16} />{:else}<Maximize size={16} />{/if}
          </button>
          <button
            type="button"
            class="icon-button"
            disabled={busy}
            onclick={close}
            aria-label={ui('Close')}
            title={ui('Close')}><X size={18} /></button
          >
        </div>
      </header>
      <Dialog.Description class="composer-from">
        {#if mode === 'comment'}{ui('Visible to the team with access to this record.')}
        {:else}<span>{ui('From:')}</span> {account}{/if}
      </Dialog.Description>
      <form
        class="compose-form"
        onsubmit={submit}
        oninput={() => {
          dirty = true;
          discard = false;
        }}
      >
        <div class="compose-scroll">
          {#if mode !== 'comment' && !canSend}<p class="compose-status" role="status">
              {ui('Reconnect Gmail in Profile → Integrations to enable sending.')}
              <a href={resolve('/profile?tab=integrations')}>{ui('Integrations')}</a>
            </p>{/if}
          <fieldset {disabled}>
            {#if mode !== 'comment'}
              <div class="recipient-row">
                <label class="field-row"
                  ><span>{ui('To:')}</span><input
                    bind:this={toInput}
                    bind:value={to}
                    required
                    autocomplete="off"
                    placeholder="name@example.com"
                  /></label
                >
                {#if !showCc}<button
                    class="text-button"
                    type="button"
                    onclick={() => (showCc = true)}
                    aria-label={ui('Add CC')}>CC</button
                  >{/if}
                {#if !showBcc}<button
                    class="text-button"
                    type="button"
                    onclick={() => (showBcc = true)}
                    aria-label={ui('Add BCC')}>{ui('BCC')}</button
                  >{/if}
              </div>
              {#if showCc}<label class="field-row"
                  ><span>CC</span><input bind:value={cc} autocomplete="off" /></label
                >{/if}
              {#if showBcc}<label class="field-row"
                  ><span>{ui('BCC')}</span><input bind:value={bcc} autocomplete="off" /></label
                >{/if}
              <label class="field-row"
                ><span>{ui('Subject')}</span><input
                  bind:value={subject}
                  readonly={isReply}
                  maxlength="998"
                /></label
              >
              {#if initialized}<EmailEditor
                  initialText={body}
                  focusMessage={isReply}
                  {disabled}
                  onchange={(text, html, edited) => {
                    body = text;
                    bodyHtml = html;
                    if (edited) {
                      dirty = true;
                      discard = false;
                    }
                  }}
                />{/if}
            {:else}
              <p class="compose-status">
                {ui('Subject')}: {message?.subject || ui('(No subject)')}
              </p>
              <textarea
                class="v2-input comment-body"
                aria-label={ui('Internal comment')}
                bind:value={body}
                required
                rows="5"
                maxlength="8000"></textarea>
            {/if}
          </fieldset>
          {#if isReply && message?.body}<details class="original-message">
              <summary>{ui('Original message')}</summary><EmailBody text={message.body} />
            </details>{/if}
          {#if files.length}
            <ul class="attachment-list" aria-label={ui('Attachments')}>
              {#each files as file, index (index)}<li>
                  <Paperclip size={14} /><span class="file-name" title={file.name}>{file.name}</span
                  ><span>{mailFileSize(file.size)}</span>
                  <button
                    class="icon-button"
                    type="button"
                    {disabled}
                    aria-label={`${ui('Remove')} ${file.name}`}
                    onclick={() => {
                      files = files.filter((_, i) => i !== index);
                      dirty = true;
                    }}><X size={14} /></button
                  >
                </li>{/each}
            </ul>
          {/if}
          {#if error}<Notice message={ui(error)} />{/if}
          {#if discard}<div class="discard-prompt" role="alert">
              <span>{ui('Discard this draft?')}</span>
              <button type="button" class="v2-btn v2-btn-sm" onclick={() => (discard = false)}
                >{ui('Keep editing')}</button
              >
              <button type="button" class="v2-btn v2-btn-sm" onclick={close}>{ui('Discard')}</button
              >
            </div>{/if}
        </div>
        <footer class="compose-actions">
          <button
            class="v2-btn v2-btn-primary v2-btn-sm"
            type="submit"
            disabled={disabled || !body.trim()}
          >
            {ui(busy ? 'Sending…' : mode === 'comment' ? 'Save comment' : 'Send email')}
          </button>
          {#if mode !== 'comment'}
            <input
              bind:this={fileInput}
              type="file"
              multiple
              hidden
              {disabled}
              onchange={addFiles}
            />
            <button
              class="icon-button"
              type="button"
              {disabled}
              title={ui('Attach files')}
              aria-label={ui('Attach files')}
              onclick={() => fileInput?.click()}><Paperclip size={18} /></button
            >
            <span class="attachment-limit">{ui('10 MB total')}</span>
          {/if}
        </footer>
      </form>
    </Dialog.Content>
  </Dialog.Portal>
</Dialog.Root>

<style>
  :global(.composer-backdrop) {
    position: fixed;
    inset: 0;
    z-index: 59;
    background: transparent;
  }
  :global(.email-composer) {
    position: fixed;
    z-index: 60;
    right: 1.25rem;
    bottom: 0;
    width: min(36rem, calc(100vw - 2.5rem));
    max-height: calc(100dvh - 2rem);
    display: flex;
    flex-direction: column;
    background: var(--crm-surface);
    color: var(--crm-text);
    border: 1px solid var(--v2-line);
    border-radius: var(--crm-radius-lg) var(--crm-radius-lg) 0 0;
    box-shadow: var(--crm-shadow-lg);
    overflow: hidden;
  }
  :global(.email-composer.is-expanded) {
    width: min(52rem, calc(100vw - 2.5rem));
  }
  .composer-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0.75rem 0.5rem 1rem;
    background: var(--crm-canvas);
  }
  :global(.composer-title) {
    font-size: var(--crm-text-base);
    font-weight: 600;
    margin: 0;
  }
  .header-actions {
    display: flex;
    gap: 0.25rem;
  }
  :global(.composer-from) {
    padding: 0.5rem 1rem;
    margin: 0;
    color: var(--v2-slate);
    font-size: var(--crm-text-xs);
    border-bottom: 1px solid var(--v2-line-soft);
    overflow-wrap: anywhere;
  }
  :global(.composer-from span) {
    margin-right: 0.5rem;
  }
  .compose-form {
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
  .compose-scroll {
    overflow-y: auto;
    overscroll-behavior: contain;
    min-height: 0;
  }
  fieldset {
    border: 0;
    margin: 0;
    padding: 0;
    min-width: 0;
  }
  .field-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.375rem 1rem;
    min-width: 0;
    border-bottom: 1px solid var(--v2-line-soft);
    font-size: var(--crm-text-sm);
  }
  .field-row span {
    flex: 0 0 3.5rem;
  }
  .field-row input {
    flex: 1;
    width: 0;
    min-width: 0;
    min-height: 2rem;
    background: transparent;
    border: 0;
    border-radius: 0.25rem;
    padding: 0.25rem;
  }
  .field-row input:focus-visible {
    outline: 2px solid var(--crm-link);
    outline-offset: 1px;
  }
  .recipient-row {
    display: flex;
    border-bottom: 1px solid var(--v2-line-soft);
    padding-right: 0.75rem;
    gap: 0.25rem;
  }
  .recipient-row .field-row {
    flex: 1;
    border: 0;
    padding-right: 0;
  }
  .text-button {
    font-size: var(--crm-text-xs);
    font-weight: 600;
    padding: 0.25rem;
    color: var(--crm-link);
  }
  .icon-button {
    width: 2rem;
    height: 2rem;
    display: inline-grid;
    place-items: center;
    flex-shrink: 0;
    border-radius: 0.25rem;
  }
  .icon-button:hover {
    background: var(--crm-canvas);
  }
  .icon-button:focus-visible,
  .text-button:focus-visible {
    outline: 2px solid var(--crm-link);
  }
  button:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }
  .comment-body {
    width: calc(100% - 2rem);
    margin: 0 1rem 0.75rem;
  }
  .original-message {
    color: var(--v2-slate);
    margin: 0.5rem 1rem;
  }
  .original-message summary {
    cursor: pointer;
    font-size: var(--crm-text-xs);
  }
  .attachment-list {
    display: grid;
    gap: 0.25rem;
    margin: 0.5rem 1rem;
    padding: 0;
    list-style: none;
  }
  .attachment-list li {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    border: 1px solid var(--v2-line-soft);
    border-radius: 0.25rem;
    padding: 0.125rem 0.375rem;
    font-size: var(--crm-text-xs);
  }
  .file-name {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .compose-status {
    margin: 0.75rem 1rem;
    font-size: var(--crm-text-sm);
  }
  .compose-actions {
    display: flex;
    gap: 0.5rem;
    align-items: center;
    padding: 0.75rem 1rem;
    border-top: 1px solid var(--v2-line-soft);
  }
  .attachment-limit {
    color: var(--v2-slate);
    font-size: var(--crm-text-xs);
  }
  .discard-prompt {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin: 0.75rem 1rem;
    font-size: var(--crm-text-sm);
  }
</style>
