<script>
  import GoogleSignInButton from '$lib/components/GoogleSignInButton.svelte';
  import LegalAcceptance from '$lib/components/LegalAcceptance.svelte';
  import LegalLinks from '$lib/components/LegalLinks.svelte';
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
      {:else if data.differentAccount}
        <h2>{data.invitation?.organization}</h2>
        <p>{ui('This invitation is for')} <strong>{data.invitation?.email}</strong>.</p>
        <a class="v2-btn v2-btn-primary" href={resolve('/logout')} data-sveltekit-reload
          >{ui('Continue with the invited account')}</a
        >
      {:else if data.error}<p role="alert" class="v2-error">{ui(data.error)}</p>
        <a class="v2-btn" href={resolve('/invite')} data-sveltekit-reload>{ui('Try again')}</a>
        {#if data.signedIn}<a href={resolve('/logout')}>{ui('Sign in with a different account')}</a
          >{/if}
      {:else if !data.signedIn}<h2>{data.invitation?.organization}</h2>
        <p>
          {ui('You already have a CRM account with')}
          {data.invitation?.email}{ui('. Sign in to join this organization.')}
        </p>
        {#if data.google_available}
          <form method="POST" action={resolve('/login?/google')} onsubmit={() => (busy = true)}>
            <GoogleSignInButton {busy} />
          </form>
          <div class="v2-auth-divider">{ui('or')}</div>
        {/if}
        <a class="v2-btn" href={resolve('/login?method=password')}>{ui('Sign in with email')}</a>
        <p>
          {ui('Need to set or recover your password?')}
          <a href={resolve('/login?recover=1')}>{ui('Reset password')}</a>.
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
          <LegalAcceptance requirements={data.invitation?.legal} />
          <button class="v2-btn v2-btn-primary" disabled={busy}
            >{busy ? ui('Joining…') : ui('Accept invitation')}</button
          >
        </form>
      {/if}
    </div>
    <LegalLinks />
  </div>
</div>
