<script>
  import '../../../../app.css';
  import '$lib/v2/styles/v2.css';
  import { base, resolve } from '$app/paths';
  import { useI18n } from '$lib/i18n/context.js';
  import { authForm } from '$lib/utils/auth-form.js';
  import LegalLinks from '$lib/components/LegalLinks.svelte';
  const { ui } = useI18n();
  let { data, form } = $props();
  let busy = $state(false);
  let transportError = $state('');
  let showPassword = $state(false);
</script>

<svelte:head
  ><title>{ui('Reset password')} · High Demand Media CRM</title><meta
    name="robots"
    content="noindex"
  /></svelte:head
>
<main class="v2-root v2-auth" aria-labelledby="reset-title">
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
      <div class="v2-auth-head">
        <h1 id="reset-title">{ui(form?.success ? 'Password updated' : 'Reset password')}</h1>
      </div>
      {#if form?.success}
        <p role="status">
          {ui('Sign in with your new password. Your previous sessions have been signed out.')}
        </p>
        <a class="v2-btn v2-btn-primary v2-btn-block" href={resolve('/login')}>{ui('Sign in')}</a>
      {:else if data.ready}
        <form
          method="POST"
          aria-busy={busy}
          use:authForm={{
            setBusy: (value) => (busy = value),
            setError: (value) => (transportError = value)
          }}
        >
          <fieldset disabled={busy}>
            <label for="new-password"
              >{ui('New password')}<input
                class="v2-input"
                id="new-password"
                name="password"
                type={showPassword ? 'text' : 'password'}
                autocomplete="new-password"
                minlength="10"
                maxlength="128"
                required
              /></label
            >
            <label for="confirm-password"
              >{ui('Confirm password')}<input
                class="v2-input"
                id="confirm-password"
                name="password_confirm"
                type={showPassword ? 'text' : 'password'}
                autocomplete="new-password"
                minlength="10"
                maxlength="128"
                required
              /></label
            >
            <label class="show-password"
              ><input type="checkbox" bind:checked={showPassword} />{ui('Show password')}</label
            >
            {#if transportError || form?.error}<p class="v2-error" role="alert">
                {ui(transportError || form.error)}
              </p>{/if}
            <button type="submit" class="v2-btn v2-btn-primary v2-btn-block"
              >{ui(busy ? 'Saving…' : 'Save new password')}</button
            >
          </fieldset>
        </form>
        <a class="reset-link" href={resolve('/login?recover=1')}>{ui('Request a new link')}</a>
      {:else}
        <p role="alert">{ui('This reset link is invalid or expired. Request a new one.')}</p>
        <a class="v2-btn v2-btn-primary v2-btn-block" href={resolve('/login?recover=1')}
          >{ui('Request a new link')}</a
        >
      {/if}
    </div>
    <LegalLinks />
  </div>
</main>

<style>
  .v2-auth-box {
    max-width: 30rem;
  }
  fieldset {
    border: 0;
    padding: 0;
    margin: 0;
    display: grid;
    gap: 1rem;
    min-width: 0;
  }
  label {
    display: grid;
    gap: 0.375rem;
  }
  .show-password {
    display: flex;
    align-items: center;
    gap: 0.625rem;
  }
  .show-password input {
    width: 1.125rem;
    height: 1.125rem;
  }
  .reset-link {
    display: inline-block;
    margin-top: 1rem;
  }
</style>
