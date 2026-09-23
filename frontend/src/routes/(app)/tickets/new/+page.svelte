<script>
  import { creationEnhance } from '$lib/components/creation/enhance.js';
  const enhance = creationEnhance();
  import { untrack } from 'svelte';
  import { resolve } from '$app/paths';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import TicketFields from '$lib/components/tickets/TicketFields.svelte';
  let { data, form } = $props();
  let values = $state(
    untrack(() => ({
      name: '',
      description: '',
      status: 'New',
      priority: 'Normal',
      category: 'General',
      source: 'Internal',
      due_at: '',
      waiting_reason: '',
      account: data.defaults.account ?? '',
      contacts: data.defaults.contacts ?? [],
      deal: '',
      assigned_to: '',
      ...form?.values
    }))
  );
  let busy = $state(false);
</script>

<PageHeader title="New ticket" />
<div class="v2-scroll v2-pad">
  <form
    class="ticket-form"
    method="POST"
    action="?/create"
    use:enhance={() => {
      busy = true;
      return async ({ update }) => {
        await update({ reset: false });
        busy = false;
      };
    }}
  >
    {#if form?.error}<p role="alert" class="v2-error">{form.error}</p>{/if}
    <TicketFields bind:values options={data} />
    <div class="actions">
      <button class="v2-btn v2-btn-primary" disabled={busy}
        >{busy ? 'Saving…' : 'Create ticket'}</button
      ><a class="v2-btn" href={resolve('/tickets')}>Cancel</a>
    </div>
  </form>
</div>

<style>
  .ticket-form {
    max-width: 660px;
    margin: 0 auto;
    background: var(--v2-bg);
    padding: 24px;
    border-radius: 12px;
  }
  .actions {
    display: flex;
    gap: 8px;
    margin-top: 24px;
  }
</style>
