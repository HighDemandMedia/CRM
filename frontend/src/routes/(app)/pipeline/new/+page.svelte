<script>
  import DealForm from '$lib/components/deals/DealForm.svelte';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import { resolve } from '$app/paths';
  /** @type {{data:any,form:any}} */
  let { data, form } = $props();
</script>

<PageHeader title="New deal"
  >{#snippet crumb()}<a href={resolve('/pipeline')}>Deals</a>{/snippet}</PageHeader
>
<div class="v2-scroll v2-pad"><DealForm {data} result={form} /></div>
