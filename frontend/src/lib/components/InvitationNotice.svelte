<script>
  import Notice from './Notice.svelte';
  import { Button } from '$lib/components/ui/button/index.js';
  import { useI18n } from '$lib/i18n/context.js';
  import { invitationNotice } from '$lib/utils/invitation-notice.js';
  let { issue, retryHref = '/invite' } = $props();
  const { ui } = useI18n();
  const notice = $derived(invitationNotice(issue));
</script>

<Notice layout="page" tone={notice.tone} title={ui(notice.title)} message={ui(notice.message)}>
  {#snippet actions()}
    {#if notice.retry}<Button href={retryHref} data-sveltekit-reload>{ui('Try again')}</Button>{/if}
    <Button href="/login" variant={notice.retry ? 'outline' : 'default'}>{ui('Sign in')}</Button>
  {/snippet}
</Notice>
