<script>
  import { enhance } from '$app/forms';
  import { untrack } from 'svelte';
  import { useI18n } from '$lib/i18n/context.js';
  import PortalShell from '$lib/v2/components/PortalShell.svelte';
  import ErrorNotice from '$lib/components/ErrorNotice.svelte';
  const { ui, locale } = useI18n();
  let { data, form } = $props();
  let selected = $state(untrack(() => data.selected || data.invitation?.response || ''));
  let pending = $state(false);
</script>

<svelte:head
  ><title>{ui('Appointment invitation')} · HDM CRM</title><meta
    name="robots"
    content="noindex,nofollow"
  /><meta name="referrer" content="no-referrer" /></svelte:head
>
<PortalShell>
  <section class="invitation">
    {#if data.unavailable}<h1>{ui('Appointment invitation')}</h1>
      <ErrorNotice
        message={ui('This invitation is no longer available. Use the latest invitation.')}
      />
    {:else}
      <p>{data.invitation.organization}</p>
      <h1>{data.invitation.title}</h1>
      <p>
        {new Date(data.invitation.start).toLocaleString(locale(), {
          dateStyle: 'medium',
          timeStyle: 'short',
          hour12: true
        })} – {new Date(data.invitation.end).toLocaleTimeString(locale(), {
          hour: 'numeric',
          minute: '2-digit',
          hour12: true
        })}
      </p>
      {#if form?.saved}<p role="status">{ui('Your response has been saved.')}</p>{/if}
      {#if form?.error}<ErrorNotice message={ui(form.error)} />{/if}
      <form
        method="POST"
        use:enhance={() => {
          pending = true;
          return async ({ update }) => {
            try {
              await update({ reset: false });
            } finally {
              pending = false;
            }
          };
        }}
      >
        <input type="hidden" name="token" value={data.token} />
        <fieldset disabled={pending}>
          <legend class="sr-only">{ui('Confirm response')}</legend>
          {#each [['accepted', 'Accept'], ['tentative', 'Maybe'], ['declined', 'Decline']] as [value, label] (value)}
            <label
              ><input type="radio" name="response" {value} bind:group={selected} required />{ui(
                label
              )}</label
            >
          {/each}
        </fieldset>
        <button class="v2-btn v2-btn-primary" disabled={pending}
          >{ui(pending ? 'Saving…' : 'Confirm response')}</button
        >
      </form>
    {/if}
  </section>
</PortalShell>

<style>
  .invitation {
    max-width: 520px;
    margin: 48px auto;
    padding: 24px;
    background: var(--crm-surface);
    border: 1px solid var(--crm-border);
    border-radius: var(--crm-radius-lg);
    overflow-wrap: anywhere;
  }
  h1 {
    font-size: 24px;
    margin: 12px 0;
  }
  p {
    color: var(--crm-text-muted);
    line-height: 1.5;
  }
  fieldset {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    border: 0;
    padding: 16px 0;
  }
  label {
    display: flex;
    align-items: center;
    gap: 6px;
    min-height: 44px;
  }
  @media (max-width: 480px) {
    .invitation {
      margin: 16px;
      padding: 20px;
    }
  }
</style>
