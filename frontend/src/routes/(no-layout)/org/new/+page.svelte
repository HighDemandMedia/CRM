<script>
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();

  import { resolve, base } from '$app/paths';
  import '../../../../app.css';
  import '$lib/v2/styles/v2.css';
  import { enhance } from '$app/forms';
  import { goto } from '$app/navigation';
  import { ArrowLeft, Check, AlertCircle } from '@lucide/svelte';

  let { data, form } = $props();

  let packs = $derived(data?.packs ?? []);
  let timezones = $derived(data?.timezones ?? [{ name: 'UTC', label: 'UTC' }]);

  let isSubmitting = $state(false);

  // Prefilled from the browser, then corrected against the server's list. The
  // two vocabularies differ on aliases, so a detected name that the list does
  // not carry has to fall back rather than be selected: a select whose value
  // matches no option submits its first entry, which would put a new org in
  // Africa/Abidjan without anyone choosing it.
  //
  // Starts at UTC so the server-rendered form is correct without JavaScript;
  // the effect below narrows it to the user's own zone once the browser runs.
  let timezone = $state('UTC');

  $effect(() => {
    const detected = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (detected && timezones.some((z) => z.name === detected)) timezone = detected;
  });

  // Handle form submission success - redirect after showing success message
  $effect(() => {
    if (form?.data && !form.data.invitationWarning) {
      const timer = setTimeout(() => {
        goto(resolve('/org'));
      }, 1500);
      return () => clearTimeout(timer);
    }
  });
</script>

<svelte:head>
  <title>{ui('Create organization · High Demand Media CRM')}</title>
</svelte:head>

<div class="v2-root v2-auth">
  <div class="v2-auth-box">
    <a href={resolve('/')} class="v2-auth-brand">
      <img
        class="v2-brand-mark"
        src={`${base}/brand/hdm-symbol.png`}
        alt=""
        width="228"
        height="155"
      />
      <b>High Demand Media CRM</b>
    </a>

    <div class="v2-auth-card">
      <div class="v2-auth-head">
        <h1>{ui('Create organization')}</h1>
        <p>{ui('Set up a new workspace for your team.')}</p>
      </div>

      <form
        action="/org/new"
        method="POST"
        use:enhance={() => {
          isSubmitting = true;
          return async ({ update }) => {
            await update();
            isSubmitting = false;
          };
        }}
      >
        <div class="v2-field">
          <label for="administrator_email">{ui('Administrator email')}</label>
          <input
            id="administrator_email"
            name="administrator_email"
            type="email"
            class="v2-input"
            placeholder="admin@company.com"
            autocomplete="email"
            disabled={isSubmitting || !!form?.data}
          />
          <p class="v2-sub">
            {ui(
              'We’ll send an invitation to set up their account and manage this organization. Leave blank for your own workspace.'
            )}
          </p>
        </div>
        {#if form?.data?.invitationWarning}<p class="v2-error" role="alert">
            {form.data.invitationWarning}
          </p>
          <a href={resolve('/org')}>{ui('Open organizations')}</a>{/if}
        <div class="v2-field">
          <label for="org_name">{ui('Organization name')}</label>
          <input
            type="text"
            id="org_name"
            name="org_name"
            class="v2-input"
            placeholder={ui('e.g. Acme Inc.')}
            required
            disabled={isSubmitting || !!form?.data}
          />
          <p class="v2-hint">{ui('This becomes your workspace name in High Demand Media CRM.')}</p>
        </div>

        <div class="v2-field">
          <label for="timezone">{ui('Time zone')}</label>
          <select
            id="timezone"
            name="timezone"
            class="v2-input"
            bind:value={timezone}
            disabled={isSubmitting || !!form?.data}
          >
            {#each timezones as zone (zone.name)}
              <option value={zone.name}>{zone.label}</option>
            {/each}
          </select>
          <p class="v2-hint">
            {ui(
              'Sets when a day starts here, so "due today" and "overdue" mean what your team expects. You can change it later in Settings.'
            )}
          </p>
        </div>

        {#if packs.length > 0}
          <fieldset class="v2-field pack-choice">
            <legend>{ui('What kind of business is this?')}</legend>
            <p class="v2-hint" style="margin-top:0">
              {ui(
                'Sets up a starter pipeline, tags and fields for your industry. You can change everything later.'
              )}
            </p>

            <label class="pack-opt">
              <input
                type="radio"
                name="vertical"
                value=""
                checked
                disabled={isSubmitting || !!form?.data}
              />
              <span class="pack-opt-body">
                <b>{ui('Skip for now')}</b>
                <span class="v2-hint" style="margin:0">{ui('Start with a blank workspace.')}</span>
              </span>
            </label>

            {#each packs as pack (pack.id)}
              <label class="pack-opt">
                <input
                  type="radio"
                  name="vertical"
                  value={pack.id}
                  disabled={isSubmitting || !!form?.data}
                />
                <span class="pack-opt-body">
                  <b>{pack.name}</b>
                  {#if pack.description}
                    <span class="v2-hint" style="margin:0">{pack.description}</span>
                  {/if}
                </span>
              </label>
            {/each}
          </fieldset>
        {/if}

        {#if form?.error}
          <div class="v2-auth-note v2-auth-note-bad" style="margin-bottom:14px">
            <AlertCircle />
            <div>
              <b>{ui("Couldn't create organization")}</b>
              <div style="font-weight:400;margin-top:2px">
                {form.error.name || 'Please try again.'}
              </div>
            </div>
          </div>
        {/if}

        {#if form?.data}
          <div class="v2-auth-note v2-auth-note-ok" style="margin-bottom:14px">
            <Check />
            <div>
              <b>{ui('Organization created')}</b>
              <div style="font-weight:400;margin-top:2px">
                {ui('Taking you to your workspaces…')}
              </div>
            </div>
          </div>
        {/if}

        <button
          type="submit"
          class="v2-btn v2-btn-primary v2-btn-block"
          disabled={isSubmitting || !!form?.data}
        >
          {#if isSubmitting}
            <span class="v2-spin"></span>
            <span>{ui('Creating…')}</span>
          {:else if form?.data}
            <Check size={15} />
            <span>{ui('Created')}</span>
          {:else}
            <span>{ui('Create organization')}</span>
          {/if}
        </button>
      </form>
    </div>

    <div class="v2-auth-foot">
      <a href={resolve('/org')} style="display:inline-flex;align-items:center;gap:5px">
        <ArrowLeft size={13} />
        {ui('Back to organizations')}
      </a>
    </div>
  </div>
</div>

<style>
  .pack-choice {
    border: 1px solid var(--v2-line-soft);
    border-radius: var(--crm-radius-md);
    padding: 14px var(--crm-space-4);
  }
  .pack-choice legend {
    font-weight: 600;
    padding: 0 6px;
  }
  .pack-opt {
    display: flex;
    align-items: flex-start;
    gap: 9px;
    padding: 9px 10px;
    border: 1px solid var(--v2-line);
    border-radius: var(--crm-radius-md);
    cursor: pointer;
  }
  .pack-opt + .pack-opt {
    margin-top: 7px;
  }
  .pack-opt:has(input:checked) {
    border-color: var(--crm-link);
    background: var(--v2-ember-soft);
  }
  .pack-opt:has(input:disabled) {
    cursor: not-allowed;
    opacity: 0.65;
  }
  .pack-opt input[type='radio'] {
    margin-top: 2px;
    accent-color: var(--crm-link);
    flex: none;
  }
  .pack-opt-body {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
  }
</style>
