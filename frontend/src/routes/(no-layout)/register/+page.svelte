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
  import { onMount } from 'svelte';
  let { data, form } = $props();
  let busy = $state(false);
  const usePassword = $derived(!data.google_available || data.password);
  let timezone = $state('UTC');
  onMount(() => {
    timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
  });
</script>

<svelte:head
  ><title>{ui('Create account · High Demand Media CRM')}</title><meta
    name="referrer"
    content="strict-origin"
  /></svelte:head
>
<div class="v2-root v2-auth">
  <div class="v2-auth-box">
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
      {#if data.issue}<InvitationNotice issue={data.issue} retryHref="/register" />{:else}
        <div class="v2-auth-head">
          <h1>{data.invited ? ui('Set up your account') : ui('Create your account')}</h1>
          <p>{data.invitation?.organization || ui('Access is by invitation.')}</p>
        </div>
        {#if data.error}<Notice message={ui(data.error)} />
        {:else if !data.invited}<p>{ui('Open the invitation link from your email.')}</p>
        {:else if !usePassword}
          <p class="invited-email">{data.invitation?.email}</p>
          <form method="POST" action="?/google" aria-busy={busy} onsubmit={() => (busy = true)}>
            <LegalAcceptance requirements={data.invitation?.legal} />
            {#if form?.error || data.googleError}<Notice
                message={ui(form?.error || data.googleError)}
              />{/if}
            <GoogleSignInButton {busy} />
          </form>
          <div class="v2-auth-divider">{ui('or')}</div>
          <a class="alternative" href={resolve('/register?method=password')}
            >{ui('Create account with email')}</a
          >
        {:else}
          {#if data.google_available}<a class="alternative" href={resolve('/register')}
              >{ui('Back to sign in')}</a
            >{/if}
          <form
            method="POST"
            action="?/password"
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
            <fieldset disabled={busy}>
              <label
                >{ui('Full name')}<input
                  class="v2-input"
                  name="name"
                  required
                  maxlength="255"
                  autocomplete="name"
                  value={form?.values?.name || ''}
                /></label
              >
              <label
                >{ui('Email')}<input
                  class="v2-input"
                  name="email"
                  type="email"
                  required
                  autocomplete="username"
                  readonly={data.invited}
                  value={data.invitation?.email || form?.values?.email || ''}
                /></label
              >
              {#if !data.invited}<label
                  >{ui('Organization name')}<input
                    class="v2-input"
                    name="organization"
                    required
                    maxlength="255"
                    autocomplete="organization"
                    value={form?.values?.organization || ''}
                  /></label
                >{/if}
              <input type="hidden" name="timezone" value={timezone} />
              <label
                >{ui('Password')}<input
                  class="v2-input"
                  name="password"
                  type="password"
                  required
                  minlength="10"
                  maxlength="128"
                  autocomplete="new-password"
                  aria-describedby="password-hint"
                /></label
              >
              <p id="password-hint" class="v2-sub">
                {ui('At least 10 characters. Avoid common passwords.')}
              </p>
              <label
                >{ui('Confirm password')}<input
                  class="v2-input"
                  name="confirm_password"
                  type="password"
                  required
                  minlength="10"
                  maxlength="128"
                  autocomplete="new-password"
                /></label
              >
              <LegalAcceptance requirements={data.invitation?.legal} />
              {#if form?.error}<Notice message={ui(form.error)} />{/if}
              <button class="v2-btn v2-btn-primary v2-btn-block"
                >{busy
                  ? ui('Creating…')
                  : data.invited
                    ? ui('Create password and join')
                    : ui('Create account')}</button
              >
            </fieldset>
          </form>{/if}
      {/if}
    </div>
    <LegalLinks />
    <p class="v2-sub" style="text-align:center;margin-top:16px">
      {ui('Already have an account?')} <a href={resolve('/login')}>{ui('Sign in')}</a>
    </p>
  </div>
</div>

<style>
  .invited-email {
    overflow-wrap: anywhere;
    margin-bottom: var(--crm-space-4);
    color: var(--crm-text-muted);
  }
  .alternative {
    display: block;
    text-align: center;
    padding: var(--crm-space-3);
    color: var(--crm-link);
    font-size: var(--crm-text-sm);
  }

  fieldset {
    border: 0;
    padding: 0;
    margin: 0;
    display: grid;
    gap: var(--crm-space-4);
    min-width: 0;
  }
  label {
    display: grid;
    gap: 6px;
    font-size: var(--crm-text-sm);
  }
  p {
    margin: 0;
  }
</style>
