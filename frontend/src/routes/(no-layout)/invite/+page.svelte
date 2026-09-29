<script>
  import '../../../app.css';
  import '$lib/v2/styles/v2.css';
  import { resolve } from '$app/paths';
  import { enhance } from '$app/forms';
  let { data, form } = $props();
  let busy = $state(false);
</script>

<svelte:head
  ><title>Invitation · High Demand Media CRM</title><meta
    name="referrer"
    content="no-referrer"
  /></svelte:head
>
<div class="v2-root v2-auth">
  <div class="v2-auth-box">
    <div class="v2-auth-card">
      <h1>Join your team</h1>
      {#if !data.hasInvitation}<p>Open the invitation link from your email.</p>
      {:else if data.error}<p role="alert" class="v2-error">{data.error}</p>
        {#if data.signedIn}<a href={resolve('/logout')}>Sign in with a different account</a>{/if}
      {:else if !data.signedIn}<h2>{data.invitation?.organization}</h2>
        <p>
          You already have a CRM account with {data.invitation?.email}. Sign in to join this
          organization.
        </p>
        <a class="v2-btn v2-btn-primary" href={resolve('/login')}>Sign in</a>
        <p>
          Need to set or recover your password? <a href={`${resolve('/login')}?recover=1`}
            >Get a secure sign-in link</a
          >.
        </p>
      {:else}<h2>{data.invitation?.name}</h2>
        <p>{data.invitation?.email} · {data.invitation?.role === 'ADMIN' ? 'Admin' : 'Member'}</p>
        <p>
          Accept this invitation to join the organization. Your other memberships remain unchanged.
        </p>
        {#if form?.error}<p role="alert" class="v2-error">{form.error}</p>{/if}
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
            >{busy ? 'Joining…' : 'Accept invitation'}</button
          >
        </form>
      {/if}
    </div>
  </div>
</div>
