<script>
  import * as Dialog from '$lib/components/ui/dialog/index.js';
  import MailIcon from '@lucide/svelte/icons/mail';
  import CalendarIcon from '@lucide/svelte/icons/calendar-days';
  import { enhance } from '$app/forms';
  import { useI18n } from '$lib/i18n/context.js';
  import { legalLinks } from '$lib/legal.js';

  let {
    service,
    label,
    disabled = false,
    revoke = false,
    onManage = undefined,
    accountEmail = ''
  } = $props();
  const { ui, locale } = useI18n();
  const privacyUrl = $derived(legalLinks(locale()).privacy + '#google');
  let open = $state(false);
  let submitting = $state(false);
  const title = $derived(
    revoke
      ? 'Remove all Google access'
      : service === 'gmail'
        ? 'Connect Gmail'
        : 'Connect Google Calendar'
  );

  const submit = (input) => {
    submitting = true;
    const handler = onManage?.(input);
    return async (result) => {
      try {
        if (handler) await handler(result);
        else await result.update();
        open = false;
      } finally {
        submitting = false;
      }
    };
  };

  function manageForm(form) {
    // OAuth uses a full document redirect to Google; only local management is enhanced.
    if (revoke) return enhance(form, submit);
  }
</script>

<button
  type="button"
  class="v2-btn v2-btn-sm"
  class:v2-btn-primary={!revoke}
  {disabled}
  onclick={() => (open = true)}>{ui(label)}</button
>
<Dialog.Root bind:open>
  <Dialog.Content
    class="google-connection-dialog"
    showCloseButton={!submitting}
    onEscapeKeydown={(event) => {
      if (submitting) event.preventDefault();
    }}
    onInteractOutside={(event) => {
      if (submitting) event.preventDefault();
    }}
  >
    <Dialog.Header>
      <Dialog.Title>{ui(title)}</Dialog.Title>
      <Dialog.Description class={revoke ? undefined : 'sr-only'}
        >{ui(
          revoke
            ? 'Disconnect Gmail and Google Calendar for this Google account.'
            : 'Connect only if you want to use this integration.'
        )}</Dialog.Description
      >
    </Dialog.Header>
    <div class="disclosure">
      {#if revoke}
        {#if accountEmail}<strong class="account-email">{accountEmail}</strong>{/if}
        <p>
          {ui(
            'This revokes HDM permissions for this Google account and may disconnect its other HDM integrations, including in other organizations.'
          )}
        </p>
        <p>
          {ui(
            'Cached Gmail and Calendar data for this account in your current profile will be removed. Your original Google emails, events and CRM records stay intact.'
          )}
        </p>
      {:else}
        <div class="connection-feature">
          <span class="feature-icon" aria-hidden="true">
            {#if service === 'gmail'}<MailIcon size={22} />{:else}<CalendarIcon size={22} />{/if}
          </span>
          <div>
            <h3>{ui(service === 'gmail' ? 'Email conversations' : 'Events and meeting notes')}</h3>
            <p>
              {ui(
                service === 'gmail'
                  ? 'HDM reads and stores emails linked to your CRM contacts, syncing automatically. View conversations and send messages from your private mailbox.'
                  : 'HDM lists calendars, stores events and automatically syncs appointments and meeting notes both ways. Notes are visible to people with access to the Google event.'
              )}
            </p>
          </div>
        </div>
        <div class="privacy-summary">
          <p>
            {ui(
              'Processed by HDM and its hosting providers for this integration. Never used for ads or AI training.'
            )}
          </p>
          <a href={privacyUrl} target="_blank" rel="external noopener noreferrer"
            >{ui('Privacy notice')}</a
          >
        </div>
      {/if}
      {#if revoke}
        <a href={privacyUrl} target="_blank" rel="external noopener noreferrer"
          >{ui('Privacy notice')}</a
        >
      {/if}
    </div>
    <form
      method="POST"
      action={revoke ? '?/googleManage' : '?/googleConnect'}
      use:manageForm
      onsubmit={() => {
        if (!revoke) submitting = true;
      }}
    >
      <input type="hidden" name="service" value={service} />
      {#if revoke}
        <input type="hidden" name="operation" value="revoke" />
        <input type="hidden" name="confirm_revoke" value="yes" />
      {:else}
        <input type="hidden" name="disclosure_accepted" value="yes" />
      {/if}
      <div class="dialog-actions">
        <button type="button" class="v2-btn" disabled={submitting} onclick={() => (open = false)}
          >{ui('Cancel')}</button
        >
        <button type="submit" class="v2-btn v2-btn-primary" disabled={submitting}
          >{ui(
            submitting ? 'Please wait…' : revoke ? 'Remove all Google access' : 'Continue to Google'
          )}</button
        >
      </div>
    </form>
  </Dialog.Content>
</Dialog.Root>

<style>
  :global(.google-connection-dialog) {
    width: min(36rem, calc(100vw - 2rem));
    max-width: calc(100vw - 2rem);
    max-height: calc(100dvh - 2rem);
    overflow: hidden;
    background: var(--crm-surface, #fff);
    grid-template-rows: auto minmax(0, 1fr) auto;
  }
  :global(.google-connection-dialog [data-slot='dialog-header']) {
    padding-inline-end: 1.5rem;
    text-align: start;
  }
  :global(.google-connection-dialog [data-slot='dialog-title']) {
    line-height: 1.3;
  }
  .disclosure {
    overflow-y: auto;
    overscroll-behavior: contain;
    display: grid;
    gap: 0.75rem;
    font-size: 0.875rem;
    line-height: 1.5;
  }
  .account-email {
    overflow-wrap: anywhere;
  }
  .disclosure p {
    margin: 0;
  }
  .disclosure a {
    color: var(--crm-accent, #b91c1c);
    text-decoration: underline;
    width: fit-content;
  }
  .connection-feature {
    display: flex;
    gap: 0.75rem;
    align-items: flex-start;
  }
  .connection-feature > div {
    min-width: 0;
  }
  .feature-icon {
    flex-shrink: 0;
    padding-top: 0.125rem;
  }
  .connection-feature h3 {
    margin: 0 0 0.375rem;
    font-size: 0.9375rem;
    font-weight: 600;
  }
  .privacy-summary {
    padding: 0.875rem;
    border-radius: 0.625rem;
    background: var(--crm-canvas, #f1f2f4);
  }
  .privacy-summary a {
    display: inline-block;
    margin-top: 0.375rem;
  }
  .dialog-actions {
    display: flex;
    justify-content: flex-end;
    flex-wrap: wrap;
    gap: 0.5rem;
  }
</style>
