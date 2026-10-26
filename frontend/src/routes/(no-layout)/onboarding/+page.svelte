<script>
  import '../../../app.css';
  import '$lib/v2/styles/v2.css';
  import { base, resolve } from '$app/paths';
  import { enhance } from '$app/forms';
  import { useI18n } from '$lib/i18n/context.js';
  import ErrorNotice from '$lib/components/ErrorNotice.svelte';
  import { CURRENCY_CODES } from '$lib/constants/filters.js';
  import CountrySelect from '$lib/components/CountrySelect.svelte';
  const { ui } = useI18n();
  let { data, form } = $props();
  let busy = $state(false);
  let submitError = $state('');
  let organizationStep = $derived(data.step === 'organization');
  let steps = $derived(
    data.includesOrganization ? ['Your profile', 'Your organization'] : ['Your profile']
  );
  let values = $derived(
    form?.values ||
      (organizationStep
        ? data.organization
        : {
            name: data.profile?.user_details?.name || '',
            ui_language: data.profile?.ui_language || 'en',
            timezone: data.profile?.timezone || data.profile?.organization_timezone || 'UTC'
          })
  );
  const save = () => {
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
        {#each steps as step, index (step)}
          <li aria-current={(organizationStep ? 1 : 0) === index ? 'step' : undefined}>
            <span>{index + 1}</span>{ui(step)}
          </li>
        {/each}
      </ol>
      <div class="v2-auth-head">
        <h1>{ui(organizationStep ? 'Set up your organization' : 'Welcome to HDM CRM')}</h1>
        <p>
          {ui(
            organizationStep
              ? 'Confirm the basics for your team.'
              : 'Confirm your details to get started.'
          )}
        </p>
      </div>
      {#if organizationStep}<a class="setup-back" href={resolve('/onboarding?step=profile')}
          >← {ui('Back to your profile')}</a
        >{/if}
      <form method="POST" use:enhance={save}>
        <input type="hidden" name="step" value={data.step} />
        <fieldset disabled={busy}>
          <label for="setup-name">{ui(organizationStep ? 'Organization name' : 'Full name')}</label>
          <input
            id="setup-name"
            class="v2-input"
            name="name"
            value={values.name || ''}
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
              value={values.default_currency || 'USD'}
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
              value={values.default_country || ''}
            />
          {:else}
            <label for="setup-language">{ui('CRM language')}</label>
            <select
              id="setup-language"
              name="ui_language"
              class="v2-input"
              value={values.ui_language || 'en'}
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
            value={values.timezone || 'UTC'}
            required
            aria-invalid={!!form?.errors?.timezone}
            aria-describedby={form?.errors?.timezone ? 'timezone-error' : undefined}
          >
            {#each data.timezones as zone (zone.name)}<option value={zone.name}>{zone.label}</option
              >{/each}
          </select>
          {#if form?.errors?.timezone}<p class="field-error" id="timezone-error">
              {ui(form.errors.timezone)}
            </p>{/if}
          {#if form?.message || submitError}<ErrorNotice
              message={ui(submitError || form.message)}
            />{/if}
          <button type="submit" class="v2-btn v2-btn-primary v2-btn-block"
            >{ui(
              busy
                ? 'Saving…'
                : organizationStep || !data.includesOrganization
                  ? 'Open CRM'
                  : 'Continue'
            )}</button
          >
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
    max-width: 36rem;
    min-width: 0;
  }
  .setup-progress {
    display: flex;
    flex-wrap: wrap;
    gap: var(--crm-space-4);
    padding: 0;
    margin: 0 0 var(--crm-space-6);
    list-style: none;
    font-size: var(--crm-text-sm);
  }
  .setup-progress li {
    display: flex;
    gap: var(--crm-space-2);
    align-items: center;
    color: var(--crm-text-muted);
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
  .setup-back {
    display: inline-block;
    margin-bottom: var(--crm-space-4);
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
  button {
    margin-top: var(--crm-space-4);
  }
  .field-error {
    margin: 0;
    color: var(--crm-danger);
    font-size: var(--crm-text-sm);
  }
</style>
