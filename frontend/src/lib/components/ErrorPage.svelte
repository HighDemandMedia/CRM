<script>
  import { useI18n } from '$lib/i18n/context.js';
  import { Button } from '$lib/components/ui/button/index.js';
  import { RefreshCw, ArrowLeft } from '@lucide/svelte';
  import Notice from './Notice.svelte';
  import { pageError } from '$lib/utils/page-error.js';
  const { ui } = useI18n();
  /** @type {{ status?: number }} */
  let { status = 500 } = $props();
  const error = $derived(pageError(status));
</script>

<section class="crm-error-page" aria-label={ui(error.title)}>
  <div class="error-card">
    <Notice
      layout="page"
      tone={error.retry ? 'error' : 'warning'}
      title={ui(error.title)}
      message={ui(error.description)}
    >
      {#snippet actions()}
        {#if error.signIn}
          <Button href="/login">{ui('Sign in')}</Button>
        {:else if error.retry}
          <Button onclick={() => location.reload()}><RefreshCw size={16} />{ui('Try again')}</Button
          >
        {/if}
        <Button variant={error.retry || error.signIn ? 'outline' : 'default'} href="/">
          <ArrowLeft size={16} />{ui('Back to Today')}
        </Button>
      {/snippet}
    </Notice>
  </div>
</section>

<style>
  .crm-error-page {
    display: grid;
    place-items: center;
    flex: 1;
    min-height: 60vh;
    padding: var(--crm-space-6);
    overflow: auto;
  }
  .error-card {
    width: 100%;
    max-width: 32rem;
    padding: clamp(1.5rem, 4vw, 2.5rem);
    border: 1px solid var(--crm-border);
    border-radius: var(--crm-radius-lg);
    background: var(--crm-surface);
    box-shadow: var(--crm-shadow-sm);
    text-align: center;
  }
</style>
