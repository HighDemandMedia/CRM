<script>
  import '../../../../app.css';
  import LegalDocument from '$lib/components/LegalDocument.svelte';
  let { data } = $props();
</script>

<LegalDocument {data} annex />
