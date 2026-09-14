<script>
  import { languages } from '$lib/v2/languages.js';
  /** @type {{value?:string}} */
  let { value = $bindable('') } = $props();
</script>

<label
  >Language
  <select class="v2-input" name="language" bind:value>
    <option value="">Select language</option>
    {#each languages as language}<option value={language}>{language}</option>{/each}
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
