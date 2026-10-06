<script>
  import { useI18n } from '$lib/i18n/context.js';
  const { ui, shortDate } = useI18n();

  import { untrack } from 'svelte';
  import { enhance } from '$app/forms';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import { countryOptions } from '$lib/constants/countries.js';
  import { CURRENCY_CODES } from '$lib/constants/filters.js';

  /** @type {{data:any, form:any}} */
  let { data, form } = $props();
  let org = $derived(data.org);
  let busy = $state(false);
  const sections = [
    {
      title: 'Organization details',
      fields: [
        ['name', 'Organization name', 'text'],
        ['company_name', 'Legal name', 'text'],
        ['email', 'Email', 'email'],
        ['phone', 'Phone', 'tel'],
        ['website', 'Website', 'url'],
        ['tax_id', 'Tax ID', 'text']
      ]
    },
    {
      title: 'Address',
      fields: [
        ['address_line', 'Street address', 'text'],
        ['city', 'City', 'text'],
        ['state', 'State / Province', 'text'],
        ['postcode', 'Zip / Postal code', 'text']
      ]
    }
  ];
  function initialValues() {
    return Object.fromEntries(
      [
        ...sections.flatMap((section) => section.fields.map((field) => field[0])),
        'country',
        'default_country',
        'default_currency',
        'timezone'
      ].map((key) => [key, org[key] || ''])
    );
  }
  let draft = $state(untrack(initialValues));
  function reset() {
    draft = initialValues();
  }
  $effect(() => {
    org;
    reset();
  });
  let dirty = $derived(Object.entries(draft).some(([key, value]) => value !== (org[key] || '')));
  const save = ({ formData }) => {
    for (const [key, value] of Object.entries(draft))
      if (value === (org[key] || '')) formData.delete(key);
    busy = true;
    return async ({ update }) => {
      try {
        await update({ reset: false });
      } finally {
        busy = false;
      }
    };
  };
</script>

<div class="organization-shell">
  <PageHeader title={data.onboarding ? ui('Welcome to your organization') : ui('Organization')}
    >{#snippet sub()}{data.onboarding
        ? ui('Complete your company details and confirm your currency, country and time zone.')
        : ui('Organization information and regional defaults')}{/snippet}</PageHeader
  >
  <div class="v2-scroll">
    <div class="organization-content">
      <form method="POST" action="?/save" use:enhance={save}>
        {#if data.onboarding}<input type="hidden" name="onboarding" value="1" />{/if}
        <fieldset disabled={!data.can_edit || busy}>
          {#each sections as section}
            <section>
              <h2>{section.title}</h2>
              <div class="fields">
                {#each section.fields as [key, label, type]}
                  <label
                    >{label}{key === 'name' ? ' *' : ''}<input
                      class="v2-input"
                      name={key}
                      {type}
                      bind:value={draft[key]}
                      required={key === 'name'}
                    /></label
                  >
                {/each}
                {#if section.title === 'Address'}
                  <label
                    >{ui('Country')}<select
                      class="v2-input"
                      name="country"
                      bind:value={draft.country}
                      ><option value="">{ui('Select country')}</option
                      >{#each countryOptions(draft.country) as country}<option value={country.value}
                          >{country.label}</option
                        >{/each}</select
                    ></label
                  >
                {/if}
              </div>
            </section>
          {/each}
          <section>
            <h2>{ui('Regional defaults')}</h2>
            <div class="fields">
              <label
                >{ui('Currency')}<select
                  class="v2-input"
                  name="default_currency"
                  bind:value={draft.default_currency}
                  >{#each CURRENCY_CODES.filter((c) => c.value) as currency}<option
                      value={currency.value}>{currency.label}</option
                    >{/each}</select
                ></label
              >
              <label
                >{ui('Default country')}<select
                  class="v2-input"
                  name="default_country"
                  bind:value={draft.default_country}
                  ><option value="">{ui('Select country')}</option
                  >{#each countryOptions(draft.default_country) as country}<option
                      value={country.value}>{country.label}</option
                    >{/each}</select
                ></label
              >
              <label class="wide"
                >{ui('Time zone')}<select
                  class="v2-input"
                  name="timezone"
                  bind:value={draft.timezone}
                  >{#each data.timezones as timezone}<option value={timezone.name}
                      >{timezone.label}</option
                    >{/each}</select
                ></label
              >
            </div>
          </section>
        </fieldset>
        {#if data.can_edit}<div class="actions">
            <button class="v2-btn v2-btn-primary" disabled={busy || (!dirty && !data.onboarding)}
              >{busy
                ? ui('Saving…')
                : data.onboarding
                  ? ui('Save and open CRM')
                  : ui('Save changes')}</button
            ><button class="v2-btn" type="button" disabled={busy || !dirty} onclick={reset}
              >{ui('Cancel')}</button
            >
          </div>{/if}
        {#if form?.message}<p class="error" role="alert">
            {ui(form.message)}
          </p>{:else if form?.saved}<p class="success" role="status">
            {ui('Organization details saved.')}
          </p>{/if}
      </form>
      <dl class="metadata">
        <div>
          <dt>{ui('Organization ID')}</dt>
          <dd>{org.id}</dd>
        </div>
        <div>
          <dt>{ui('Created')}</dt>
          <dd>{shortDate(org.created_at)}</dd>
        </div>
        <div>
          <dt>{ui('Members')}</dt>
          <dd>{org.member_count}</dd>
        </div>
      </dl>
    </div>
  </div>
</div>

<style>
  .organization-shell {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    background: var(--v2-bg, var(--crm-surface));
  }
  .organization-content {
    padding: 30px var(--crm-space-8);
    max-width: 820px;
  }
  form {
    max-width: 640px;
  }
  fieldset {
    border: 0;
    padding: 0;
    margin: 0;
    min-width: 0;
  }
  section + section {
    margin-top: 30px;
    padding-top: var(--crm-space-6);
    border-top: 1px solid var(--v2-line-soft);
  }
  h2 {
    margin: 0 0 var(--crm-space-6);
    font-size: var(--crm-text-base);
    font-weight: 600;
  }
  .fields {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--crm-space-6);
  }
  label {
    display: grid;
    gap: 9px;
    font-size: var(--crm-text-sm);
    font-weight: 500;
    min-width: 0;
  }
  .v2-input {
    width: 100%;
    min-height: 42px;
    border-radius: var(--crm-radius-md);
  }
  .wide {
    grid-column: 1/-1;
  }
  .actions {
    display: flex;
    gap: var(--crm-space-2);
    margin-top: 28px;
    padding-top: var(--crm-space-5);
    border-top: 1px solid var(--v2-line-soft);
  }
  .metadata {
    display: flex;
    flex-wrap: wrap;
    gap: var(--crm-space-5);
    padding-top: var(--crm-space-6);
    margin-top: 28px;
    border-top: 1px solid var(--v2-line-soft);
    color: var(--v2-slate);
    font-size: var(--crm-text-xs);
  }
  dt {
    margin-bottom: 6px;
  }
  dd {
    margin: 0;
    overflow-wrap: anywhere;
  }
  .error {
    color: var(--v2-rust);
    font-size: var(--crm-text-xs);
  }
  .success {
    color: var(--v2-moss);
    font-size: var(--crm-text-xs);
  }
  @media (max-width: 600px) {
    .organization-content {
      padding: var(--crm-space-5) var(--crm-space-4);
    }
    .fields {
      grid-template-columns: 1fr;
    }
  }
</style>
