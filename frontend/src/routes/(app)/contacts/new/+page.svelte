<script>
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();

  import { resolve } from '$app/paths';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import ContactForm from '$lib/components/contacts/ContactForm.svelte';
  import { ChevronRight } from '@lucide/svelte';
  /** @type {{data:any, form:any}} */
  let { data, form } = $props();
</script>

<PageHeader title={ui('New contact')} center>
  {#snippet crumb()}<a href={resolve('/contacts')}>{ui('Contacts')}</a><ChevronRight
      size={12}
    /><span>{ui('New')}</span>{/snippet}
</PageHeader>
<div class="v2-scroll v2-pad" style="padding-top:18px">
  <ContactForm {data} result={form} editing={false} />
</div>
