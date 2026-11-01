<script>
  import '../../../app.css';
  import '$lib/v2/styles/v2.css';
  import { base, resolve } from '$app/paths';
  import { enhance } from '$app/forms';
  import { tick, untrack } from 'svelte';
  import { Check, ArrowLeft, ArrowRight, CheckCircle2 } from '@lucide/svelte';
  import { useI18n } from '$lib/i18n/context.js';
  import ErrorNotice from '$lib/components/ErrorNotice.svelte';
  import { CURRENCY_CODES } from '$lib/constants/filters.js';
  import CountrySelect from '$lib/components/CountrySelect.svelte';
  import AppearanceSettings from '$lib/components/AppearanceSettings.svelte';
  import NotificationPreferences from '$lib/v2/components/NotificationPreferences.svelte';
  const { ui } = useI18n();
  let { data, form } = $props();
  let busy = $state(false);
  let preferencesBusy = $state(false);
  let submitError = $state('');
  let organizationStep = $derived(data.step === 'organization');
  let steps = $derived([
    { key: 'profile', label: 'Your profile' },
    { key: 'appearance', label: 'Appearance' },
    { key: 'notifications', label: 'Notifications' },
    ...(data.includesOrganization ? [{ key: 'organization', label: 'Your organization' }] : []),
    { key: 'review', label: 'Review' }
  ]);
  function initialValues() {
    return {
      name: '',
      ui_language: 'en',
      timezone: 'UTC',
      default_currency: 'USD',
      default_country: '',
      ...(form?.values ||
        (data.step === 'organization'
          ? data.organization
          : {
              name: data.profile?.user_details?.name || '',
              ui_language: data.profile?.ui_language || 'en',
              timezone: data.profile?.timezone || data.profile?.organization_timezone || 'UTC'
            }))
    };
  }
  let screen = $state(untrack(() => (data.step === 'organization' ? 'organization' : 'profile')));
  let heading;
  let values = $state(untrack(initialValues));
  $effect(() => {
    screen = data.step === 'organization' ? 'organization' : 'profile';
    values = initialValues();
  });
  let currentIndex = $derived(steps.findIndex((step) => step.key === screen));
  let title = $derived(
    screen === 'review'
      ? 'Ready to finish'
      : screen === 'organization'
        ? 'Set up your organization'
        : screen === 'profile'
          ? 'Your profile'
          : screen === 'appearance'
            ? 'Choose your appearance'
            : 'Choose your notifications'
  );
  async function move(next) {
    screen = next;
    submitError = '';
    await tick();
    heading?.focus();
  }
  const save = ({ cancel }) => {
    if (preferencesBusy) {
      cancel();
      return;
    }
    if (screen !== 'review' && !(screen === 'notifications' && data.includesOrganization)) {
      cancel();
      move(
        screen === 'organization' || screen === 'notifications'
          ? 'review'
          : steps[currentIndex + 1].key
      );
      return;
    }
    busy = true;
    submitError = '';
    return async ({ result, update }) => {
      try {
        if (result.type === 'error') {
          submitError = 'Could not save your setup. Please try again.';
          return;
        }
        await update({ reset: false });
      } catch {
        submitError = 'Could not save your setup. Please try again.';
      } finally {
        busy = false;
      }
    };
  };
</script>

<svelte:head
  ><title>{ui('Welcome to HDM CRM')}</title><meta
    name="robots"
    content="noindex, nofollow"
  /></svelte:head
>

<main class="v2-root v2-auth">
  <div class="v2-auth-box setup-box">
    <div class="v2-auth-brand">
      <img
        class="v2-brand-mark"
        src={`${base}/brand/hdm-symbol.png`}
        alt=""
        width="228"
        height="155"
      />
      <b>High Demand Media CRM</b>
    </div>
    <div class="v2-auth-card">
      <ol class="setup-progress" aria-label={ui('Account setup')}>
        {#each steps as step, index (step.key)}
          <li
            aria-current={currentIndex === index ? 'step' : undefined}
            class:completed={index < currentIndex}
          >
            <span
              >{#if index < currentIndex}<Check size={15} aria-hidden="true" />{:else}{index +
                  1}{/if}</span
            >{ui(step.label)}
          </li>
        {/each}
      </ol>
      <div class="v2-auth-head">
        <h1 bind:this={heading} tabindex="-1">{ui(title)}</h1>
      </div>
      <form method="POST" use:enhance={save}>
        <input type="hidden" name="step" value={data.step} />
        <fieldset disabled={busy || preferencesBusy}>
          {#if screen === 'profile' || screen === 'organization'}
            <label for="setup-name"
              >{ui(organizationStep ? 'Organization name' : 'Full name')}</label
            >
            <input
              id="setup-name"
              class="v2-input"
              name="name"
              bind:value={values.name}
              required
              maxlength="255"
              autocomplete={organizationStep ? 'organization' : 'name'}
              aria-invalid={!!form?.errors?.name}
              aria-describedby={form?.errors?.name ? 'name-error' : undefined}
            />
            {#if form?.errors?.name}<p class="field-error" id="name-error">
                {ui(form.errors.name)}
              </p>{/if}
            {#if organizationStep}
              <label for="setup-currency">{ui('Currency')}</label>
              <select
                id="setup-currency"
                name="default_currency"
                class="v2-input"
                bind:value={values.default_currency}
                required
              >
                {#each CURRENCY_CODES.filter((currency) => currency.value) as currency (currency.value)}<option
                    value={currency.value}>{currency.label}</option
                  >{/each}
              </select>
              <label for="setup-country">{ui('Country')} ({ui('Optional')})</label>
              <CountrySelect
                id="setup-country"
                name="default_country"
                label="Default country"
                bind:value={values.default_country}
              />
            {:else}
              <label for="setup-language">{ui('CRM language')}</label>
              <select
                id="setup-language"
                name="ui_language"
                class="v2-input"
                bind:value={values.ui_language}
                required
              >
                <option value="en">English</option><option value="es">Español</option>
              </select>
            {/if}
            <label for="setup-timezone">{ui('Time zone')}</label>
            <select
              id="setup-timezone"
              name="timezone"
              class="v2-input"
              bind:value={values.timezone}
              required
              aria-invalid={!!form?.errors?.timezone}
              aria-describedby={form?.errors?.timezone ? 'timezone-error' : undefined}
            >
              {#each data.timezones as zone (zone.name)}<option value={zone.name}
                  >{zone.label}</option
                >{/each}
            </select>
            {#if form?.errors?.timezone}<p class="field-error" id="timezone-error">
                {ui(form.errors.timezone)}
              </p>{/if}
          {:else}
            {#each Object.entries(values) as [key, value] (key)}
              <input type="hidden" name={key} value={value || ''} />
            {/each}
          {/if}
          {#if screen === 'appearance'}
            <AppearanceSettings />
          {/if}
          {#if !organizationStep}<div hidden={screen !== 'notifications'}>
              <NotificationPreferences
                settings={data.profile?.notification_settings}
                action={resolve('/notifications?/preferences')}
                compact
                disabled={busy}
                bind:busy={preferencesBusy}
              />
            </div>{/if}
          {#if screen === 'review'}
            <div class="setup-review">
              <CheckCircle2 size={32} aria-hidden="true" />
              <p>{ui('Your preferences are ready. Complete setup to open your workspace.')}</p>
              <dl>
                <dt>{ui(organizationStep ? 'Organization name' : 'Full name')}</dt>
                <dd>{values.name}</dd>
                {#if organizationStep}<dt>{ui('Currency')}</dt>
                  <dd>{values.default_currency}</dd>
                {:else}<dt>{ui('CRM language')}</dt>
                  <dd>{values.ui_language === 'es' ? 'Español' : 'English'}</dd>{/if}
                <dt>{ui('Time zone')}</dt>
                <dd>{values.timezone}</dd>
              </dl>
            </div>
          {/if}
          {#if form?.message || submitError}<ErrorNotice
              message={ui(submitError || form.message)}
            />{/if}
          <div class="setup-actions">
            {#if currentIndex > 0}
              {#if screen === 'organization'}
                <a
                  class="v2-btn"
                  href={resolve('/onboarding?step=profile')}
                  aria-disabled={busy || preferencesBusy}
                  onclick={(event) => {
                    if (busy || preferencesBusy) event.preventDefault();
                  }}><ArrowLeft size={16} />{ui('Back')}</a
                >
              {:else}
                <button
                  type="button"
                  class="v2-btn"
                  onclick={() => move(steps[currentIndex - 1].key)}
                  ><ArrowLeft size={16} />{ui('Back')}</button
                >
              {/if}
            {/if}
            <button type="submit" class="v2-btn v2-btn-primary setup-next">
              {ui(busy ? 'Saving…' : screen === 'review' ? 'Complete setup' : 'Continue')}
              {#if !busy}<ArrowRight size={16} aria-hidden="true" />{/if}
            </button>
          </div>
        </fieldset>
      </form>
    </div>
    <div class="v2-auth-foot">
      <a href={resolve('/logout')} data-sveltekit-reload>{ui('Finish later and sign out')}</a>
    </div>
  </div>
</main>

<style>
  .setup-box {
    width: 100%;
    max-width: 44rem;
    min-width: 0;
  }
  .setup-progress {
    display: flex;
    justify-content: space-between;
    gap: var(--crm-space-2);
    padding: 0;
    margin: 0 0 var(--crm-space-6);
    list-style: none;
    font-size: var(--crm-text-sm);
  }
  .setup-progress li {
    display: flex;
    flex-direction: column;
    gap: var(--crm-space-2);
    align-items: center;
    color: var(--crm-text-muted);
    text-align: center;
    flex: 1;
  }
  .setup-progress li[aria-current] {
    color: var(--crm-text);
    font-weight: 600;
  }
  .setup-progress span {
    border: 1px solid currentColor;
    border-radius: 50%;
    width: 1.75rem;
    height: 1.75rem;
    display: grid;
    place-items: center;
    flex-shrink: 0;
  }
  .setup-progress .completed {
    color: var(--crm-success);
  }
  .setup-progress li[aria-current] span {
    background: var(--crm-surface-selected);
    color: var(--crm-link);
  }
  .setup-actions {
    display: flex;
    gap: var(--crm-space-3);
    margin-top: var(--crm-space-5);
  }
  .setup-next {
    margin-left: auto;
  }
  .setup-review {
    display: grid;
    gap: var(--crm-space-4);
  }
  .setup-review > :global(svg) {
    color: var(--crm-success);
  }
  .setup-review p {
    margin: 0;
    color: var(--crm-text-muted);
  }
  dl {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--crm-space-3);
    margin: 0;
  }
  dt {
    color: var(--crm-text-muted);
  }
  dd {
    margin: 0;
    overflow-wrap: anywhere;
  }
  fieldset {
    border: 0;
    padding: 0;
    margin: 0;
    display: grid;
    gap: var(--crm-space-2);
    min-width: 0;
  }
  label {
    margin-top: var(--crm-space-2);
    font-size: var(--crm-text-sm);
    font-weight: 600;
  }
  input,
  select {
    width: 100%;
    min-width: 0;
  }

  .field-error {
    margin: 0;
    color: var(--crm-danger);
    font-size: var(--crm-text-sm);
  }
</style>
