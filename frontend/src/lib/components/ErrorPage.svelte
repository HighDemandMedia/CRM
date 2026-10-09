<script>
  import { useI18n } from '$lib/i18n/context.js';
  import { Button } from '$lib/components/ui/button/index.js';
  import { TriangleAlert, Lock, FileQuestion, RefreshCw, ArrowLeft } from '@lucide/svelte';
  import { pageError } from '$lib/utils/page-error.js';
  const { ui } = useI18n();
  /** @type {{ status?: number }} */
  let { status = 500 } = $props();
  const error = $derived(pageError(status));
  const Icon = $derived(
    error.code === 404 ? FileQuestion : error.code === 403 || error.signIn ? Lock : TriangleAlert
  );
</script>

<section class="crm-error-page" aria-labelledby="page-error-title">
  <div class="error-card">
    <div class="error-icon" aria-hidden="true"><Icon size={28} /></div>
    <p class="error-code">{ui('Error')} {error.code}</p>
    <h1 id="page-error-title">{ui(error.title)}</h1>
    <p class="description">{ui(error.description)}</p>
    <div class="actions">
      {#if error.signIn}
        <Button href="/login">{ui('Sign in')}</Button>
      {:else if error.retry}
        <Button onclick={() => location.reload()}><RefreshCw size={16} />{ui('Try again')}</Button>
      {/if}
      <Button variant={error.retry || error.signIn ? 'outline' : 'default'} href="/">
        <ArrowLeft size={16} />{ui('Back to Today')}
      </Button>
    </div>
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
  .error-icon {
    display: grid;
    place-items: center;
    width: 3.5rem;
    height: 3.5rem;
    margin: 0 auto var(--crm-space-4);
    border-radius: var(--crm-radius-md);
    background: var(--crm-danger-bg);
    color: var(--crm-danger);
  }
  .error-code {
    color: var(--crm-text-muted);
    font-size: var(--crm-text-xs);
    margin: 0 0 var(--crm-space-2);
  }
  h1 {
    color: var(--crm-text);
    font-size: var(--crm-text-xl);
    line-height: 1.3;
    font-weight: 650;
    margin: 0 0 var(--crm-space-3);
  }
  .description {
    color: var(--crm-text-muted);
    font-size: var(--crm-text-sm);
    line-height: 1.6;
    margin: 0;
  }
  .actions {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: var(--crm-space-3);
    margin-top: var(--crm-space-6);
  }
</style>
