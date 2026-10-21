<script>
  import Notice from './Notice.svelte';
  /** @type {{ message: string }} */
  let { message } = $props();
</script>

{#if message}<Notice {message} />{/if}
