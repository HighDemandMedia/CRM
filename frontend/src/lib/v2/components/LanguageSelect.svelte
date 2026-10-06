<script>
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();

  import { languages } from '$lib/v2/languages.js';
  /** @type {{value?:string}} */
  let { value = $bindable('') } = $props();
</script>

<label
  >{ui('Language')}
  <select class="v2-input" name="language" bind:value>
    <option value="">{ui('Select language')}</option>
    {#each languages as language}<option value={language}>{ui(language)}</option>{/each}
  </select>
</label>

<style>
  label {
    display: grid;
    gap: 6px;
  }
  select {
    width: 100%;
    min-width: 0;
  }
</style>
