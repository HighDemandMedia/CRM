<script>
  import SearchableSelect from '$lib/components/SearchableSelect.svelte';
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();

  import { languages } from '$lib/v2/languages.js';
  /** @type {{value?:string}} */
  let { value = $bindable('') } = $props();
</script>

<label
  >{ui('Language')}
  <SearchableSelect
    label={ui('Language')}
    name="language"
    bind:value
    placeholder={ui('Select language')}
    options={languages.map((language) => ({ value: language, label: ui(language) }))}
  />
</label>

<style>
  label {
    display: grid;
    gap: 6px;
  }
</style>
