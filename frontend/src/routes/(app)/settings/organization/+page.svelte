<script>
  import SearchableSelect from '$lib/components/SearchableSelect.svelte';
  import Notice from '$lib/components/Notice.svelte';
  import { useI18n } from '$lib/i18n/context.js';
  const { ui, shortDate } = useI18n();

  import { untrack } from 'svelte';
  import { enhance } from '$app/forms';
  import OrganizationLifecycle from '$lib/v2/components/OrganizationLifecycle.svelte';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import CountrySelect from '$lib/components/CountrySelect.svelte';
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
      if (!data.onboarding && value === (org[key] || '')) formData.delete(key);
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

<div class="organization-shell crm-settings-fields">
  <PageHeader title={data.onboarding ? ui('Welcome to your organization') : ui('Organization')} />
  <div class="v2-scroll">
    <div class="organization-content crm-settings-content crm-preferences-body">
      <form
        class="crm-preferences-card crm-settings-surface"
        method="POST"
        action="?/save"
        use:enhance={save}
      >
        {#if data.onboarding}<input type="hidden" name="onboarding" value="1" />{/if}
        <fieldset disabled={!data.can_edit || busy}>
          {#each sections as section (section)}
            <section>
              <h2 class="crm-settings-section-title">{section.title}</h2>
              <div class="fields">
                {#each section.fields as [key, label, type] (key)}
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
                    >{ui('Country')}<CountrySelect
                      name="country"
                      bind:value={draft.country}
                    /></label
                  >
                {/if}
              </div>
            </section>
          {/each}
          <section>
            <h2 class="crm-settings-section-title">{ui('Regional defaults')}</h2>
            <div class="fields">
              <label
                >{ui('Currency')}<SearchableSelect
                  label={ui('Currency')}
                  name="default_currency"
                  bind:value={draft.default_currency}
                  options={CURRENCY_CODES.filter((c) => c.value)}
                /></label
              >
              <label
                >{ui('Default country')}<CountrySelect
                  name="default_country"
                  label="Default country"
                  bind:value={draft.default_country}
                /></label
              >
              <label class="wide"
                >{ui('Time zone')}<SearchableSelect
                  label={ui('Time zone')}
                  name="timezone"
                  bind:value={draft.timezone}
                  options={data.timezones.map((zone) => ({ value: zone.name, label: zone.label }))}
                /></label
              >
            </div>
          </section>
        </fieldset>
        {#if data.can_edit && (dirty || data.onboarding)}<div class="crm-settings-actions">
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
        {#if form?.message && form?.scope !== 'lifecycle'}<Notice
            message={ui(form.message)}
          />{:else if form?.saved}<Notice
            tone="success"
            message={ui('Organization details saved.')}
          />{/if}
      </form>
      <OrganizationLifecycle {org} {form} />
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
    min-width: 0;
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    background: var(--crm-canvas);
  }
  .organization-content {
    padding: var(--crm-space-5) var(--crm-page-gutter);
  }
  form {
    padding: var(--crm-space-5);
    background: var(--crm-surface);
    border: 1px solid var(--crm-border-soft);
    border-radius: var(--crm-radius-lg);
    box-shadow: var(--crm-panel-shadow);
  }
  fieldset {
    border: 0;
    padding: 0;
    margin: 0;
    min-width: 0;
  }
  section + section {
    margin-top: var(--crm-space-5);
    padding-top: var(--crm-space-4);
  }
  h2 {
    margin: 0 0 var(--crm-space-4);
    font-size: var(--crm-text-base);
    font-weight: 600;
  }
  .fields {
    display: grid;
    grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr);
    gap: var(--crm-space-4);
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
  .metadata {
    display: flex;
    flex-wrap: wrap;
    gap: var(--crm-space-5);
    padding-top: var(--crm-space-5);
    margin-top: var(--crm-space-4);
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
</style>
