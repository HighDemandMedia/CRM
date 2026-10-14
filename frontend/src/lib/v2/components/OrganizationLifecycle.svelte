<script>
  import { enhance } from '$app/forms';
  import { useI18n } from '$lib/i18n/context.js';
  import ErrorNotice from '$lib/components/ErrorNotice.svelte';
  import * as Dialog from '$lib/components/ui/dialog/index.js';

  const { ui, exactTime } = useI18n();
  /** @type {{org: any, form?: any}} */
  let { org, form = null } = $props();
  let open = $state(false);
  let confirmation = $state('');
  let busy = $state(false);
  let message = $state('');
  let action = $state('close');
  let lifecycle = $derived(org.lifecycle);
  let closing = $derived(lifecycle?.read_only);
  let available = $derived(closing ? lifecycle?.can_reactivate : lifecycle?.enabled);
</script>

{#if lifecycle?.can_manage}
  <Dialog.Root
    bind:open
    onOpenChange={(value) => {
      if (!value && busy) open = true;
    }}
  >
    <section aria-labelledby="lifecycle-title">
      <div class="lifecycle-summary">
        <h2 id="lifecycle-title">{ui('Organization access')}</h2>
        {#if closing}
          <p>{ui('Read-only until')} <strong>{exactTime(lifecycle.deletion_due_at)}</strong>.</p>
        {/if}
      </div>
      <Dialog.Trigger
        class="v2-btn lifecycle-trigger"
        disabled={!available}
        onclick={() => {
          action = closing ? 'reactivate' : 'close';
          confirmation = '';
          message = '';
        }}
      >
        {ui(closing ? 'Cancel closure and reactivate' : 'Close organization')}
      </Dialog.Trigger>
    </section>
    {#if form?.lifecycleSaved}
      <p role="status">{ui('Organization access updated.')}</p>
    {/if}
    <Dialog.Content
      class="max-h-[90dvh] overflow-y-auto sm:max-w-[520px]"
      showCloseButton={!busy}
      portalProps={{}}
    >
      <Dialog.Header class="text-left">
        <Dialog.Title class="pr-6">
          {ui(action === 'close' ? 'Close this organization?' : 'Reactivate this organization?')}
        </Dialog.Title>
        <Dialog.Description class="">
          {ui(
            action === 'close'
              ? 'Members will have 30 days to view and export records. You can cancel before the deadline.'
              : 'This cancels the closure and restores access. Google accounts must reconnect.'
          )}
        </Dialog.Description>
      </Dialog.Header>
      <form
        method="POST"
        action="?/lifecycle"
        use:enhance={() => {
          busy = true;
          message = '';
          return async ({ result, update }) => {
            try {
              await update({ reset: false });
              if (result.type === 'success') {
                busy = false;
                open = false;
                confirmation = '';
              } else if (result.type === 'failure') {
                message = String(result.data?.message || 'Could not update organization access.');
              }
            } finally {
              busy = false;
            }
          };
        }}
      >
        <input type="hidden" name="action" value={action} />
        <label for="lifecycle-confirm">
          {ui('Type')} <strong>{org.name}</strong>
          {ui('to confirm')}
        </label>
        <input
          id="lifecycle-confirm"
          class="v2-input"
          name="confirmation"
          bind:value={confirmation}
          required
          autocomplete="off"
          spellcheck="false"
          disabled={busy}
        />
        {#if message}<ErrorNotice message={ui(message)} />{/if}
        <div class="lifecycle-actions" aria-busy={busy}>
          <button
            class="v2-btn v2-btn-primary"
            type="submit"
            disabled={busy || confirmation !== org.name || !available}
          >
            {ui(
              busy ? 'Saving…' : action === 'close' ? 'Confirm closure' : 'Reactivate organization'
            )}
          </button>
          <button class="v2-btn" type="button" disabled={busy} onclick={() => (open = false)}>
            {ui('Cancel')}
          </button>
        </div>
      </form>
    </Dialog.Content>
  </Dialog.Root>
{/if}

<style>
  section {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: var(--crm-space-4);
    margin-top: var(--crm-space-6);
    padding: var(--crm-space-5);
    border: 1px solid var(--v2-line-soft);
    border-radius: var(--crm-radius-md);
  }
  .lifecycle-summary {
    min-width: 0;
  }
  h2 {
    margin: 0;
    font-size: var(--crm-text-base);
  }
  p {
    margin: var(--crm-space-2) 0 0;
    font-size: var(--crm-text-sm);
    color: var(--v2-slate);
  }
  form {
    display: grid;
    gap: var(--crm-space-3);
    padding-top: var(--crm-space-4);
    border-top: 1px solid var(--v2-line-soft);
  }
  label {
    font-size: var(--crm-text-sm);
    overflow-wrap: anywhere;
  }
  input {
    min-width: 0;
    width: 100%;
  }
  .lifecycle-actions {
    display: flex;
    flex-wrap: wrap;
    gap: var(--crm-space-3);
    margin-top: var(--crm-space-3);
  }
  button,
  :global(.lifecycle-trigger) {
    white-space: normal;
    min-height: 2.75rem;
  }
  :global(.lifecycle-trigger) {
    color: var(--crm-danger);
  }
</style>
