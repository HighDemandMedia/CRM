<script>
  import { resolve, base } from '$app/paths';
  import '../../../app.css';
  import '$lib/v2/styles/v2.css';
  import { authForm } from '$lib/utils/auth-form.js';
  import { ArrowLeft, Check } from '@lucide/svelte';
  import imgGoogle from '$lib/assets/images/google.svg';
  let { data = {}, form } = $props();
  let busy = $state(false);
  let recoveryBusy = $state(false);
  let transportError = $state('');
  let recoveryTransportError = $state('');
  const isRecovery = $derived(Boolean(data['recovery'] || form?.recovery));
</script>

<svelte:head>
  <title>{isRecovery ? 'Recover access' : 'Sign in'} · High Demand Media CRM</title>
</svelte:head>
<div class="v2-root v2-auth">
  <div class="v2-auth-box">
    <a href={resolve('/')} class="v2-auth-brand">
      <img src={`${base}/brand/hdm-symbol.png`} alt="" /><b>High Demand Media CRM</b>
    </a>
    <div class="v2-auth-card">
      {#if isRecovery}
        <a href={resolve('/login')} class="back-link"><ArrowLeft size={16} />Back to sign in</a>
        <div class="v2-auth-head">
          <h1>{form?.success ? 'Check your email' : 'Forgot your password?'}</h1>
          <p>
            {form?.success
              ? 'Your next step is in your inbox.'
              : 'Enter your email to receive a secure sign-in link.'}
          </p>
        </div>
        {#if form?.success}
          <div class="recovery-confirmation" role="status">
            <Check size={18} />
            <p>
              If an account exists for <strong>{form.email}</strong>, we’ll send a link to recover
              access.
            </p>
          </div>
          <p class="recovery-guidance">After signing in, choose a new password in Profile.</p>
          <a href={resolve('/login')} class="v2-btn v2-btn-primary v2-btn-block">Back to sign in</a>
          <a href={`${resolve('/login')}?recover=1`} class="recovery-retry" data-sveltekit-reload
            >Use a different email</a
          >
        {:else}
          <form
            method="POST"
            action="?/recovery"
            use:authForm={{
              setBusy: (value) => (recoveryBusy = value),
              setError: (value) => (recoveryTransportError = value)
            }}
          >
            <fieldset disabled={recoveryBusy}>
              <label for="recovery-email"
                >Email
                <input
                  id="recovery-email"
                  class="v2-input"
                  type="email"
                  name="email"
                  required
                  autocomplete="email"
                  placeholder="you@company.com"
                  value={form?.email || ''}
                />
              </label>
              {#if recoveryTransportError || form?.error}<p class="v2-error" role="alert">
                  {recoveryTransportError || form.error}
                </p>{/if}
              <button class="v2-btn v2-btn-primary v2-btn-block"
                >{recoveryBusy ? 'Sending…' : 'Send recovery link'}</button
              >
            </fieldset>
          </form>
        {/if}
      {:else}
        <div class="v2-auth-head">
          <h1>Welcome back</h1>
          <p>Sign in to your CRM.</p>
        </div>
        <form
          method="POST"
          action="?/password"
          use:authForm={{
            setBusy: (value) => (busy = value),
            setError: (value) => (transportError = value)
          }}
        >
          <fieldset disabled={busy}>
            <label for="login-email"
              >Email
              <input
                id="login-email"
                class="v2-input"
                name="email"
                type="email"
                required
                autocomplete="username"
                placeholder="you@company.com"
                value={form?.email || ''}
              />
            </label>
            <div class="password-field">
              <div class="password-label">
                <label for="login-password">Password</label><a
                  href={`${resolve('/login')}?recover=1`}>Forgot password?</a
                >
              </div>
              <input
                id="login-password"
                class="v2-input"
                name="password"
                type="password"
                required
                maxlength="128"
                autocomplete="current-password"
              />
            </div>
            {#if transportError || form?.error || data['error']}<p class="v2-error" role="alert">
                {transportError ||
                  form?.error ||
                  'Sign-in could not be completed. Please try again.'}
              </p>{/if}
            <button class="v2-btn v2-btn-primary v2-btn-block"
              >{busy ? 'Signing in…' : 'Sign in'}</button
            >
          </fieldset>
        </form>
        {#if data['google_url']}
          <div class="v2-auth-divider">or</div>
          <a href={data['google_url']} rel="external" class="v2-btn v2-btn-block"
            ><img src={imgGoogle} alt="" class="v2-auth-gicon" />Continue with Google</a
          >
        {/if}
      {/if}
    </div>
  </div>
</div>

<style>
  form,
  fieldset {
    display: grid;
    gap: 20px;
  }
  fieldset {
    border: 0;
    padding: 0;
    margin: 0;
    min-width: 0;
  }
  label,
  .password-field {
    display: grid;
    gap: 8px;
    font-size: 13px;
  }
  .password-label {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 12px;
  }
  .password-label a,
  .back-link,
  .recovery-retry {
    font-size: 12px;
    color: var(--v2-slate);
  }
  .password-label a:hover,
  .back-link:hover,
  .recovery-retry:hover {
    text-decoration: underline;
  }
  .back-link {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 28px;
  }
  .recovery-confirmation {
    display: flex;
    gap: 10px;
    align-items: flex-start;
    padding: 16px;
    border-radius: 10px;
    background: var(--v2-paper);
    font-size: 13px;
    line-height: 1.6;
  }
  .recovery-confirmation :global(svg) {
    flex-shrink: 0;
    margin-top: 2px;
  }
  .recovery-confirmation p {
    margin: 0;
    overflow-wrap: anywhere;
  }
  .recovery-guidance {
    font-size: 13px;
    line-height: 1.6;
    color: var(--v2-slate);
    margin: 16px 0 24px;
  }
  .recovery-retry {
    display: block;
    text-align: center;
    margin-top: 18px;
  }
</style>
