<script>
  import SearchableSelect from './SearchableSelect.svelte';
  import { countryOptions } from '$lib/constants/countries.js';
  import { useI18n } from '$lib/i18n/context.js';
  const { ui, locale } = useI18n();
  /** @type {{id?:string,name?:string,value?:string,required?:boolean,disabled?:boolean,label?:string}} */
  let {
    id,
    name = 'country',
    value = $bindable(''),
    required = false,
    disabled = false,
    label = 'Country'
  } = $props();
</script>

<SearchableSelect
  {id}
  {name}
  bind:value
  {required}
  {disabled}
  label={ui(label)}
  placeholder={ui('Select country')}
  options={countryOptions(value, locale())}
  autocomplete="country"
/>
