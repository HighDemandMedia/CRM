<script>
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();

  import CompanyForm from '$lib/components/companies/CompanyForm.svelte';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import { resolve } from '$app/paths';
  /** @type {{data:any,form:any}} */
  let { data, form } = $props();
</script>

<PageHeader title={ui('New company')} center
  >{#snippet crumb()}<a href={resolve('/accounts')}>{ui('Companies')}</a>{/snippet}</PageHeader
>
<div class="v2-scroll v2-pad"><CompanyForm {data} result={form} editing={false} /></div>
