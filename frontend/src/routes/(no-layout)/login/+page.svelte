<script>
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();

  import { resolve, base } from '$app/paths';
  import '../../../app.css';
  import '$lib/v2/styles/v2.css';
  import { authForm } from '$lib/utils/auth-form.js';
  import { ArrowLeft, Check, Eye, EyeOff } from '@lucide/svelte';
  import imgGoogle from '$lib/assets/images/google.svg';
  let { data = {}, form } = $props();
  let busy = $state(false);
  let recoveryBusy = $state(false);
  let transportError = $state('');
  let recoveryTransportError = $state('');
  let showPassword = $state(false);
  let capsLock = $state(false);
  const showSignIn = $derived(Boolean(data['signin'] || form || data['error']));
  const isRecovery = $derived(Boolean(data['recovery'] || form?.recovery));
  const signInError = $derived(
    transportError ||
      form?.error ||
      (data['error'] ? 'Sign-in could not be completed. Please try again.' : '')
  );
  function checkCapsLock(event) {
    capsLock = event.getModifierState('CapsLock');
  }
</script>

<svelte:head>
  <title
    >{isRecovery
      ? ui('Recover access')
      : showSignIn
        ? ui('Sign in')
        : ui('Your workspace for what’s next')} · High Demand Media CRM</title
  >
</svelte:head>
<main
  class="v2-root v2-auth login-page"
  class:presentation={!showSignIn && !isRecovery}
  aria-labelledby="login-title"
>
  <div class="v2-auth-box">
    <a href={resolve('/')} class="v2-auth-brand">
      <img
        class="v2-brand-mark"
        src={`${base}/brand/hdm-symbol.png`}
        alt=""
        width="228"
        height="155"
      /><b>High Demand Media CRM</b>
    </a>
    {#if !showSignIn && !isRecovery}
      <section class="welcome-layout">
        <div class="welcome-story">
          <p class="welcome-eyebrow">HIGH DEMAND MEDIA · CRM</p>
          <h1 id="login-title">{ui('Keep relationships moving forward.')}</h1>
          <p class="welcome-description">
            {ui('Your contacts, deals and next steps. One focused workspace for your team.')}
          </p>
          <ul class="welcome-features">
            <li><Check size={18} />{ui('Keep every contact in context')}</li>
            <li><Check size={18} />{ui('Follow deals from first conversation to close')}</li>
            <li><Check size={18} />{ui('Plan your day with tasks and appointments')}</li>
          </ul>
        </div>
        <div class="v2-auth-card welcome-access">
          <span class="access-label">{ui('INVITATION ONLY')}</span>
          <h2>{ui('Your next step starts here.')}</h2>
          <p>{ui('Already part of the CRM? Open your workspace.')}</p>
          <a href={resolve('/login?signin=1')} class="v2-btn v2-btn-primary v2-btn-block"
            >{ui('Sign in')}</a
          >
          <div class="access-request">
            <h3>{ui('Interested in joining?')}</h3>
            <p>
              {ui(
                'Request exclusive access from High Demand Media. Approved organizations receive a personal invitation.'
              )}
            </p>
            <a
              href="mailto:info@highdemandmedia.com?subject=Request%20exclusive%20access%20to%20High%20Demand%20Media%20CRM"
              class="request-link"
              >{ui('Request exclusive access')} <span aria-hidden="true">↗</span></a
            >
            <small>{ui('Opens your email app · info@highdemandmedia.com')}</small>
          </div>
        </div>
      </section>
    {:else}
      <div class="v2-auth-card">
        {#if isRecovery}
          <a href={resolve('/login?signin=1')} class="back-link"
            ><ArrowLeft size={16} />{ui('Back to sign in')}</a
          >
          <div class="v2-auth-head">
            <h1 id="login-title">
              {form?.success ? ui('Check your email') : ui('Recover access')}
            </h1>
            <p>
              {form?.success
                ? ui('Your next step is in your inbox.')
                : ui('We’ll email you a sign-in link. Then you can set a new password in Profile.')}
            </p>
          </div>
          {#if form?.success}
            <div class="recovery-confirmation" role="status">
              <Check size={18} />
              <p>
                {ui('If an account exists for')} <strong>{form.email}</strong>{ui(
                  ', we’ll send a link to recover access.'
                )}
              </p>
            </div>
            <p class="recovery-guidance">
              {ui('After signing in, choose a new password in Profile.')}
            </p>
            <a href={resolve('/login?signin=1')} class="v2-btn v2-btn-primary v2-btn-block"
              >{ui('Back to sign in')}</a
            >
            <a href={resolve('/login?recover=1')} class="recovery-retry" data-sveltekit-reload
              >{ui('Use a different email')}</a
            >
          {:else}
            <form
              method="POST"
              action="?/recovery"
              aria-busy={recoveryBusy}
              use:authForm={{
                setBusy: (value) => (recoveryBusy = value),
                setError: (value) => (recoveryTransportError = value)
              }}
            >
              <fieldset disabled={recoveryBusy}>
                <label for="recovery-email"
                  >{ui('Email')}
                  <input
                    id="recovery-email"
                    class="v2-input"
                    type="email"
                    name="email"
                    required
                    autocomplete="email"
                    autocapitalize="none"
                    spellcheck="false"
                    aria-describedby={recoveryTransportError || form?.error
                      ? 'recovery-error'
                      : undefined}
                    placeholder="you@company.com"
                    value={form?.email || ''}
                  />
                </label>
                {#if recoveryTransportError || form?.error}<p
                    id="recovery-error"
                    class="v2-error auth-error"
                    role="alert"
                  >
                    {recoveryTransportError || form.error}
                  </p>{/if}
                <button type="submit" class="v2-btn v2-btn-primary v2-btn-block"
                  >{recoveryBusy ? ui('Sending…') : ui('Send recovery link')}</button
                >
              </fieldset>
            </form>
          {/if}
        {:else}
          <a href={resolve('/login')} class="back-link"><ArrowLeft size={16} />{ui('Back')}</a>
          <div class="v2-auth-head">
            <h1 id="login-title">{ui('Sign in')}</h1>
            <p>{ui('Welcome back. Use the email associated with your account.')}</p>
          </div>
          <form
            method="POST"
            action="?/password"
            aria-busy={busy}
            use:authForm={{
              setBusy: (value) => (busy = value),
              setError: (value) => (transportError = value)
            }}
          >
            <fieldset disabled={busy}>
              <label for="login-email"
                >{ui('Email')}
                <input
                  id="login-email"
                  class="v2-input"
                  name="email"
                  type="email"
                  required
                  autocomplete="username"
                  autocapitalize="none"
                  spellcheck="false"
                  aria-describedby={signInError ? 'signin-error' : undefined}
                  placeholder="you@company.com"
                  value={form?.email || ''}
                />
              </label>
              <div class="password-field">
                <div class="password-label">
                  <label for="login-password">{ui('Password')}</label><a
                    href={resolve('/login?recover=1')}>{ui('Forgot password?')}</a
                  >
                </div>
                <div class="password-control">
                  <input
                    id="login-password"
                    class="v2-input"
                    name="password"
                    type={showPassword ? 'text' : 'password'}
                    required
                    maxlength="128"
                    autocomplete="current-password"
                    autocapitalize="none"
                    spellcheck="false"
                    aria-describedby={[
                      capsLock ? 'caps-lock' : '',
                      signInError ? 'signin-error' : ''
                    ]
                      .filter(Boolean)
                      .join(' ') || undefined}
                    onkeydown={checkCapsLock}
                    onkeyup={checkCapsLock}
                    onblur={() => (capsLock = false)}
                  /><button
                    type="button"
                    class="password-toggle"
                    aria-label={showPassword ? ui('Hide password') : ui('Show password')}
                    aria-controls="login-password"
                    onclick={() => (showPassword = !showPassword)}
                  >
                    {#if showPassword}<EyeOff size={18} />{:else}<Eye size={18} />{/if}
                    <span>{showPassword ? ui('Hide') : ui('Show')}</span>
                  </button>
                </div>
                {#if capsLock}<p id="caps-lock" class="caps-lock" role="status">
                    {ui('Caps Lock is on.')}
                  </p>{/if}
              </div>
              {#if signInError}<p id="signin-error" class="v2-error auth-error" role="alert">
                  {signInError}
                </p>{/if}
              <button type="submit" class="v2-btn v2-btn-primary v2-btn-block"
                >{busy ? ui('Signing in…') : ui('Sign in')}</button
              >
            </fieldset>
          </form>
          {#if data['google_url']}
            <div class="v2-auth-divider">{ui('or')}</div>
            <a href={data['google_url']} rel="external" class="v2-btn v2-btn-block"
              ><img src={imgGoogle} alt="" class="v2-auth-gicon" />{ui('Continue with Google')}</a
            >
          {/if}
        {/if}
      </div>
    {/if}
    {#if showSignIn && !isRecovery}<p class="access-help">
        {ui('New here? Open the invitation sent to your email.')}
      </p>{/if}
    <p class="v2-sr-only" role="status">
      {busy
        ? ui('Signing in. Please wait.')
        : recoveryBusy
          ? ui('Sending your recovery link.')
          : ''}
    </p>
  </div>
</main>

<style>
  .login-page.presentation .v2-auth-box {
    max-width: 72rem;
    width: 100%;
  }
  .welcome-layout {
    display: grid;
    grid-template-columns: 1.2fr 1fr;
    gap: clamp(2rem, 6vw, 5rem);
    align-items: center;
  }
  .welcome-story {
    padding-block: var(--crm-space-8);
  }
  .welcome-eyebrow,
  .access-label {
    font-size: var(--crm-text-xs);
    font-weight: 700;
    letter-spacing: 0.1em;
    color: var(--crm-link);
  }
  .login-page .welcome-story h1 {
    font-size: clamp(2.25rem, 4vw, 3.75rem);
    letter-spacing: -0.04em;
    line-height: 1.08;
    max-width: 12ch;
    margin: var(--crm-space-5) 0;
  }
  .welcome-description {
    font-size: var(--crm-text-lg);
    color: var(--crm-text-muted);
    line-height: 1.6;
    max-width: 38ch;
  }
  .welcome-features {
    display: grid;
    gap: var(--crm-space-4);
    margin: var(--crm-space-8) 0 0;
    padding: 0;
    list-style: none;
  }
  .welcome-features li {
    display: flex;
    align-items: center;
    gap: var(--crm-space-3);
    font-size: var(--crm-text-sm);
  }
  .welcome-features :global(svg) {
    flex-shrink: 0;
    color: var(--crm-link);
  }
  .welcome-access h2 {
    font-size: var(--crm-text-2xl);
    line-height: 1.25;
    margin: var(--crm-space-4) 0;
  }
  .welcome-access p {
    color: var(--crm-text-muted);
    font-size: var(--crm-text-sm);
    line-height: 1.6;
    margin-bottom: var(--crm-space-6);
  }
  .access-request {
    margin-top: var(--crm-space-8);
    padding-top: var(--crm-space-6);
    border-top: 1px solid var(--crm-border);
  }
  .access-request h3 {
    font-size: var(--crm-text-base);
    margin: 0 0 var(--crm-space-2);
  }
  .request-link {
    color: var(--crm-link);
    font-weight: 600;
    display: inline-flex;
    gap: var(--crm-space-2);
    padding-block: var(--crm-space-2);
  }
  .request-link:hover {
    text-decoration: underline;
  }
  .access-request small {
    display: block;
    color: var(--crm-text-muted);
    font-size: var(--crm-text-xs);
    line-height: 1.6;
    overflow-wrap: anywhere;
  }
  @media (max-width: 760px) {
    .welcome-layout {
      grid-template-columns: 1fr;
      gap: var(--crm-space-6);
    }
    .welcome-story {
      padding-block: 0;
    }
    .login-page .welcome-story h1 {
      max-width: 18ch;
    }
  }

  .login-page .v2-auth-box {
    max-width: 30rem;
  }
  .login-page .v2-auth-card {
    padding: clamp(1.25rem, 4vw, 2rem);
    border-radius: var(--crm-radius-xl);
    box-shadow: var(--crm-shadow-md);
  }
  .login-page .v2-auth-head {
    text-align: left;
    margin-bottom: var(--crm-space-8);
  }
  .login-page h1 {
    font-size: var(--crm-text-2xl);
    line-height: var(--crm-leading-title);
  }
  .login-page .v2-input {
    min-height: 3rem;
    font-size: var(--crm-text-base);
  }
  .login-page .v2-btn-block {
    min-height: 3rem;
  }
  .password-control {
    position: relative;
  }
  .password-control input {
    width: 100%;
    padding-right: 6rem;
  }
  .password-toggle {
    position: absolute;
    inset-block: 2px;
    right: 2px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: var(--crm-space-2);
    min-width: 5.5rem;
    padding-inline: var(--crm-space-2);
    border-radius: var(--crm-radius-sm);
    color: var(--crm-text-muted);
    font-size: var(--crm-text-xs);
    cursor: pointer;
  }
  .password-toggle:hover:not(:disabled) {
    background: var(--crm-surface-hover);
    color: var(--crm-text);
  }
  .auth-error {
    padding: var(--crm-space-3);
    background: var(--crm-danger-bg);
    border-radius: var(--crm-radius-sm);
    overflow-wrap: anywhere;
  }
  .caps-lock {
    color: var(--crm-warning);
    font-size: var(--crm-text-xs);
    margin: 0;
  }
  .access-help {
    text-align: center;
    font-size: var(--crm-text-xs);
    line-height: var(--crm-leading);
    color: var(--crm-text-muted);
    margin: var(--crm-space-6) var(--crm-space-3) 0;
  }
  @media (max-width: 480px), (max-height: 680px) {
    .login-page {
      justify-content: flex-start;
      padding: var(--crm-space-6) var(--crm-space-4);
    }
  }
  form,
  fieldset {
    display: grid;
    gap: var(--crm-space-5);
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
    gap: var(--crm-space-2);
    font-size: var(--crm-text-sm);
  }
  .password-label {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: var(--crm-space-3);
    flex-wrap: wrap;
  }
  .password-label a,
  .back-link,
  .recovery-retry {
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
  }
  .password-label a {
    padding-block: var(--crm-space-2);
    color: var(--crm-link);
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
    padding: var(--crm-space-4);
    border-radius: var(--crm-radius-md);
    background: var(--v2-paper);
    font-size: var(--crm-text-sm);
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
    font-size: var(--crm-text-sm);
    line-height: 1.6;
    color: var(--v2-slate);
    margin: var(--crm-space-4) 0 var(--crm-space-6);
  }
  .recovery-retry {
    display: block;
    text-align: center;
    margin-top: 18px;
  }
</style>
