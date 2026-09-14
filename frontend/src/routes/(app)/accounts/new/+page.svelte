<script>
  import CompanyForm from '$lib/components/companies/CompanyForm.svelte';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import { resolve } from '$app/paths';
  /** @type {{data:any,form:any}} */
  let { data, form } = $props();
</script>

<PageHeader title="New company" center
  >{#snippet crumb()}<a href={resolve('/accounts')}>Companies</a>{/snippet}</PageHeader
>
<div class="v2-scroll v2-pad"><CompanyForm {data} result={form} editing={false} /></div>
