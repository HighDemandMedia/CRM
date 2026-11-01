<script>
  import InvitationNotice from '$lib/components/InvitationNotice.svelte';
  import Notice from '$lib/components/Notice.svelte';
  import GoogleSignInButton from '$lib/components/GoogleSignInButton.svelte';
  import LegalAcceptance from '$lib/components/LegalAcceptance.svelte';
  import LegalLinks from '$lib/components/LegalLinks.svelte';
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();

  import '../../../app.css';
  import '$lib/v2/styles/v2.css';
  import { base, resolve } from '$app/paths';
  import { enhance } from '$app/forms';
  let { data, form } = $props();
  let busy = $state(false);
</script>

<svelte:head
  ><title>{ui('Invitation · High Demand Media CRM')}</title><meta
    name="referrer"
    content="strict-origin"
  /></svelte:head
>
<div class="v2-root v2-auth">
  <div class="v2-auth-box invitation-box">
    <a href={resolve('/login')} class="v2-auth-brand"
      ><img
        class="v2-brand-mark"
        src={`${base}/brand/hdm-symbol.png`}
        alt=""
        width="228"
        height="155"
      /><b>High Demand Media CRM</b></a
    >
    <div class="v2-auth-card">
      {#if data.issue || form?.issue}
        <InvitationNotice issue={form?.issue || data.issue} />
      {:else}
        <div class="v2-auth-head">
          <h1>{ui('Join your team')}</h1>
          {#if data.invitation?.organization || data.invitation?.name}
            <p class="organization-name">{data.invitation.organization || data.invitation.name}</p>
          {/if}
        </div>
        <div class="invitation-content">
          {#if !data.hasInvitation}<p>{ui('Open the invitation link from your email.')}</p>
          {:else if data.differentAccount}
            <div class="invitation-recipient">
              <span>{ui('This invitation is for')}</span>
              <strong>{data.invitation?.email}</strong>
            </div>
            <p class="invitation-hint">
              {ui('Sign out of the current account to continue with this invitation.')}
            </p>
            <a
              class="v2-btn v2-btn-primary invitation-action"
              href={resolve('/logout')}
              data-sveltekit-reload>{ui('Continue with invited email')}</a
            >
          {:else if data.error}<InvitationNotice issue="invitation_invalid" />
          {:else if !data.signedIn}
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
            <a class="v2-btn" href={resolve('/login?method=password')}>{ui('Sign in with email')}</a
            >
            <p>
              {ui('Need to set or recover your password?')}
              <a href={resolve('/login?recover=1')}>{ui('Reset password')}</a>.
            </p>
          {:else}
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
            {#if form?.error}<Notice message={ui(form.error)} />{/if}
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
      {/if}
    </div>
    <LegalLinks />
  </div>
</div>

<style>
  .invitation-box {
    max-width: 32rem;
  }
  .invitation-content {
    display: grid;
    gap: var(--crm-space-4);
    min-width: 0;
  }
  .invitation-content :global(p) {
    margin: 0;
    line-height: 1.5;
    overflow-wrap: anywhere;
  }
  .invitation-content :global(form) {
    display: grid;
    gap: var(--crm-space-4);
  }
  .invitation-recipient {
    display: grid;
    gap: var(--crm-space-2);
    padding: var(--crm-space-4);
    border-radius: var(--crm-radius-md);
    background: var(--crm-surface-subtle);
  }
  .invitation-recipient span,
  .invitation-hint {
    font-size: var(--crm-text-sm);
    color: var(--crm-text-muted);
  }
  .invitation-recipient strong {
    font-size: var(--crm-text-sm);
    font-weight: 600;
    overflow-wrap: anywhere;
  }
  .organization-name {
    overflow-wrap: anywhere;
  }
  .invitation-action {
    width: 100%;
    white-space: normal;
    text-align: center;
  }
</style>
