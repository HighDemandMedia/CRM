<script>
  import SearchableSelect from '$lib/components/SearchableSelect.svelte';
  import { untrack } from 'svelte';
  import { useI18n } from '$lib/i18n/context.js';
  import {
    parsePhone,
    normalizedPhone,
    getCountries,
    getCountryCallingCode,
    PHONE_ERROR
  } from '$lib/utils/phone-number.js';
  const { ui, locale } = useI18n();
  /** @type {{id?:string,name?:string,value?:string,required?:boolean,disabled?:boolean}} */
  let { id, name, value = $bindable(''), required = false, disabled = false } = $props();
  let country = $state(/** @type {import('libphonenumber-js').CountryCode} */ ('US'));
  let national = $state('');
  let published = $state(/** @type {string | undefined} */ (undefined));
  let input;
  const countryNames = $derived(new Intl.DisplayNames([locale()], { type: 'region' }));
  const countries = $derived(
    getCountries()
      .map((code) => ({
        code,
        value: code,
        keywords: `${code} ${new Intl.DisplayNames(['en'], { type: 'region' }).of(code)} ${new Intl.DisplayNames(['es'], { type: 'region' }).of(code)}`,
        label: `${countryNames.of(code) || code} (+${getCountryCallingCode(code)})`,
        calling: getCountryCallingCode(code),
        name: countryNames.of(code) || code
      }))
      .sort((a, b) =>
        a.code === 'US' ? -1 : b.code === 'US' ? 1 : a.name.localeCompare(b.name, locale())
      )
  );
  function flag(code) {
    return [...code].map((c) => String.fromCodePoint(127397 + c.charCodeAt(0))).join('');
  }
  $effect(() => {
    const incoming = value || '';
    if (incoming !== untrack(() => published)) {
      const phone = parsePhone(incoming);
      country = phone?.country || 'US';
      national = phone?.isValid() ? phone.formatNational() : incoming;
      published = incoming;
    }
  });
  function publish() {
    if (national.trim().startsWith('+')) {
      const phone = parsePhone(national);
      if (phone?.country) country = phone.country;
    }
    published = normalizedPhone(national, country) || national;
    value = published;
  }
  function blur() {
    const phone = parsePhone(national, country);
    if (phone?.isValid()) national = phone.formatNational();
    publish();
  }
  $effect(() => {
    input?.setCustomValidity(
      national.trim() && !normalizedPhone(national, country) ? ui(PHONE_ERROR) : ''
    );
  });
</script>

<div class="phone-control" data-property-control>
  <div class="country-control">
    <SearchableSelect
      label={ui('Phone country code')}
      options={countries}
      value={country}
      compactLabel={`${flag(country)} +${getCountryCallingCode(country)}`}
      {disabled}
      onchange={(next) => {
        country = /** @type {import('libphonenumber-js').CountryCode} */ (next);
        publish();
      }}
    />
  </div>
  <input
    bind:this={input}
    {id}
    type="tel"
    inputmode="tel"
    autocomplete="tel-national"
    class="v2-input"
    bind:value={national}
    {required}
    {disabled}
    maxlength="40"
    data-property-type="phone"
    data-phone-country={country}
    data-phone-name={name}
    placeholder={ui('Phone number')}
    oninput={(event) => {
      national = event.currentTarget.value;
      publish();
    }}
    onblur={blur}
  />
  <input type="hidden" {name} {value} {disabled} />
</div>

<style>
  .phone-control {
    display: flex;
    align-items: stretch;
    min-width: 0;
    width: 100%;
    border: 1px solid var(--crm-control-border, var(--v2-line));
    border-radius: var(--crm-radius-md, 8px);
    background: var(--v2-card);
  }
  .phone-control:focus-within {
    outline: 2px solid var(--crm-primary, #c82322);
    outline-offset: 2px;
  }
  .country-control {
    position: relative;
    display: flex;
    align-items: center;
    flex: 0 0 98px;
    border-right: 1px solid var(--v2-line);
  }
  .phone-control input.v2-input {
    flex: 1;
    width: 0;
    min-width: 0;
    border: 0;
    background: transparent;
    box-shadow: none;
    outline: none;
  }
</style>
