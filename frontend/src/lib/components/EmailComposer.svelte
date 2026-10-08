<script>
  import { toast } from 'svelte-sonner';
  import { resolve } from '$app/paths';
  import { onMount } from 'svelte';
  import { invalidateAll } from '$app/navigation';
  import * as Dialog from '$lib/components/ui/dialog/index.js';
  import { useI18n } from '$lib/i18n/context.js';
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
    subject = $state(''),
    body = $state('');
  let requestId = '';
  const title = $derived(
    mode === 'comment'
      ? 'Internal comment'
      : mode === 'reply'
        ? 'Reply'
        : mode === 'forward'
          ? 'Forward'
          : 'New email'
  );
  onMount(() => {
    requestId = crypto.randomUUID();
    to =
      mode === 'reply'
        ? message.direction === 'sent'
          ? message.recipients.join(', ')
          : message.reply_to?.length
            ? message.reply_to.join(', ')
            : message.sender
        : mode === 'send'
          ? recipient
          : '';
    subject =
      mode === 'reply'
        ? message.subject
        : mode === 'forward'
          ? `Fwd: ${message.subject || ''}`
          : '';
    if (mode === 'forward')
      body = `\n\n---------- Forwarded message ----------\nFrom: ${message.sender}\nTo: ${message.recipients.join(', ')}\nSubject: ${message.subject || ''}\n\n${message.body || ''}`;
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
    busy = true;
    error = '';
    const payload = {
      action: mode,
      request_id: requestId,
      message: message?.id,
      to: addresses(to),
      cc: addresses(cc),
      subject,
      body
    };
    try {
      const response = await fetch(`/api/record-mail/${kind}/${recordId}/actions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
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
      if (busy) open = true;
      else onclose();
    }
  }}
>
  <Dialog.Content class="max-h-[90dvh] overflow-y-auto sm:max-w-[640px]" portalProps={{}}>
    <Dialog.Header class="">
      <Dialog.Title class="">{ui(title)}</Dialog.Title>
      <Dialog.Description class=""
        >{ui(
          mode === 'comment'
            ? 'Saved in Notes and Activity. Visible to the team with access to this record; the email body stays private.'
            : 'Send from your connected Gmail. Text only; attachments are not included.'
        )}</Dialog.Description
      >
    </Dialog.Header>
    <form class="compose-form" onsubmit={submit}>
      {#if mode !== 'comment'}
        <p class="v2-sub">{ui('From:')} {account}</p>
        {#if !canSend}<p role="status">
            {ui('Reconnect Gmail in Profile → Integrations to enable sending.')}
            <a href={resolve('/profile?tab=integrations')}>{ui('Integrations')}</a>
          </p>{/if}
      {/if}
      <fieldset disabled={busy || locked || (mode !== 'comment' && !canSend)}>
        {#if mode !== 'comment'}
          <label
            >{ui('To:')}<input
              class="v2-input"
              bind:value={to}
              required
              autocomplete="off"
              placeholder="name@example.com"
            /></label
          >
          <label>CC<input class="v2-input" bind:value={cc} autocomplete="off" /></label>
          <p class="v2-sub">{ui('Separate email addresses with commas.')}</p>
          <label
            >{ui('Subject')}<input
              class="v2-input"
              bind:value={subject}
              readonly={mode === 'reply'}
              maxlength="998"
            /></label
          >
        {:else}<p class="v2-sub">{ui('Subject')}: {message?.subject || ui('(No subject)')}</p>{/if}
        <label
          >{ui(mode === 'comment' ? 'Internal comment' : 'Message')}<textarea
            class="v2-input"
            bind:value={body}
            required
            rows="9"
            maxlength={mode === 'comment' ? 8000 : 100000}></textarea></label
        >
      </fieldset>
      {#if error}<p class="v2-error" role="alert">{ui(error)}</p>{/if}
      <div class="compose-actions">
        <button class="v2-btn" type="button" onclick={onclose} disabled={busy}
          >{ui('Cancel')}</button
        >
        <button
          class="v2-btn v2-btn-primary"
          type="submit"
          disabled={busy || locked || !body.trim() || (mode !== 'comment' && !canSend)}
          >{ui(busy ? 'Saving…' : mode === 'comment' ? 'Save comment' : 'Send email')}</button
        >
      </div>
    </form>
  </Dialog.Content>
</Dialog.Root>

<style>
  .compose-form,
  fieldset,
  label {
    display: grid;
    gap: var(--crm-space-3);
    min-width: 0;
  }
  fieldset {
    border: 0;
    padding: 0;
    margin: 0;
  }
  label {
    gap: var(--crm-space-2);
    font-size: var(--crm-text-sm);
  }
  textarea {
    height: auto;
    resize: vertical;
    min-height: 10rem;
  }
  .compose-actions {
    display: flex;
    justify-content: flex-end;
    gap: var(--crm-space-2);
  }
</style>
