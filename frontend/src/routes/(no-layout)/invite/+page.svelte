<script>
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();

  import '../../../app.css';
  import '$lib/v2/styles/v2.css';
  import { resolve } from '$app/paths';
  import { enhance } from '$app/forms';
  let { data, form } = $props();
  let busy = $state(false);
</script>

<svelte:head
  ><title>{ui('Invitation · High Demand Media CRM')}</title><meta
    name="referrer"
    content="no-referrer"
  /></svelte:head
>
<div class="v2-root v2-auth">
  <div class="v2-auth-box">
    <div class="v2-auth-card">
      <h1>{ui('Join your team')}</h1>
      {#if !data.hasInvitation}<p>{ui('Open the invitation link from your email.')}</p>
      {:else if data.error}<p role="alert" class="v2-error">{data.error}</p>
        {#if data.signedIn}<a href={resolve('/logout')}>{ui('Sign in with a different account')}</a
          >{/if}
      {:else if !data.signedIn}<h2>{data.invitation?.organization}</h2>
        <p>
          {ui('You already have a CRM account with')}
          {data.invitation?.email}{ui('. Sign in to join this organization.')}
        </p>
        <a class="v2-btn v2-btn-primary" href={resolve('/login')}>{ui('Sign in')}</a>
        <p>
          {ui('Need to set or recover your password?')}
          <a href={`${resolve('/login')}?recover=1`}>{ui('Get a secure sign-in link')}</a>.
        </p>
      {:else}<h2>{data.invitation?.name}</h2>
        <p>
          {data.invitation?.email} · {data.invitation?.role === 'ADMIN'
            ? ui('Admin')
            : ui('Member')}
        </p>
        <p>
          {ui(
            'Accept this invitation to join the organization. Your other memberships remain unchanged.'
          )}
        </p>
        {#if form?.error}<p role="alert" class="v2-error">{ui(form.error)}</p>{/if}
        <form
          method="POST"
          action="?/accept"
          use:enhance={() => {
            busy = true;
            return async ({ update }) => {
              try {
                await update();
              } finally {
                busy = false;
              }
            };
          }}
        >
          <button class="v2-btn v2-btn-primary" disabled={busy}
            >{busy ? ui('Joining…') : ui('Accept invitation')}</button
          >
        </form>
      {/if}
    </div>
  </div>
</div>
