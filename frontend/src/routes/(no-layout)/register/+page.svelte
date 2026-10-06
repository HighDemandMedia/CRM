<script>
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();

  import '../../../app.css';
  import '$lib/v2/styles/v2.css';
  import { base, resolve } from '$app/paths';
  import { enhance } from '$app/forms';
  import { onMount } from 'svelte';
  let { data, form } = $props();
  let busy = $state(false);
  let timezone = $state('UTC');
  onMount(() => {
    timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
  });
</script>

<svelte:head
  ><title>{ui('Create account · High Demand Media CRM')}</title><meta
    name="referrer"
    content="no-referrer"
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
      <div class="v2-auth-head">
        <h1>{data.invited ? ui('Set up your account') : ui('Create your account')}</h1>
        <p>
          {data.invited
            ? `Create your password to join ${data.invitation?.organization || 'your organization'}.`
            : ui('Start with your organization and personal login.')}
        </p>
      </div>
      {#if data.error}<p class="v2-error" role="alert">{data.error}</p>{:else}<form
          method="POST"
          use:enhance={() => {
            busy = true;
            return async ({ update }) => {
              await update();
              busy = false;
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
            {#if form?.error}<p class="v2-error" role="alert">{ui(form.error)}</p>{/if}
            <button class="v2-btn v2-btn-primary v2-btn-block"
              >{busy
                ? ui('Creating…')
                : data.invited
                  ? ui('Create password and join')
                  : ui('Create account')}</button
            >
          </fieldset>
        </form>{/if}
    </div>
    <p class="v2-sub" style="text-align:center;margin-top:16px">
      {ui('Already have an account?')} <a href={resolve('/login')}>{ui('Sign in')}</a>
    </p>
  </div>
</div>

<style>
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
