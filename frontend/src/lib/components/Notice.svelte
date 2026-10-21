<script>
  import { CircleCheck, Info, TriangleAlert } from '@lucide/svelte';

  /** @type {{ tone?: 'error' | 'warning' | 'success' | 'info', title?: string,
   * message?: string, layout?: 'inline' | 'page', id?: string,
   * children?: import('svelte').Snippet, actions?: import('svelte').Snippet }} */
  let {
    tone = 'error',
    title = '',
    message = '',
    layout = 'inline',
    id,
    children,
    actions
  } = $props();
  const Icon = $derived(tone === 'success' ? CircleCheck : tone === 'info' ? Info : TriangleAlert);
</script>

<div
  class="crm-notice"
  class:page={layout === 'page'}
  data-tone={tone}
  role={layout === 'inline'
    ? tone === 'error' || tone === 'warning'
      ? 'alert'
      : 'status'
    : undefined}
  {id}
>
  <span class="notice-icon" aria-hidden="true"><Icon size={layout === 'page' ? 26 : 18} /></span>
  <div class="notice-content">
    {#if title}
      {#if layout === 'page'}<h1>{title}</h1>{:else}<h2>{title}</h2>{/if}
    {/if}
    {#if message}<p>{message}</p>{/if}
    {@render children?.()}
    {#if actions}<div class="notice-actions">{@render actions()}</div>{/if}
  </div>
</div>

<style>
  .crm-notice {
    --notice-color: var(--crm-danger);
    --notice-bg: var(--crm-danger-bg);
    display: flex;
    align-items: flex-start;
    gap: var(--crm-space-3);
    min-width: 0;
    margin-block: var(--crm-space-3);
    padding: var(--crm-space-3) var(--crm-space-4);
    border: 1px solid color-mix(in srgb, var(--notice-color) 30%, var(--crm-border));
    border-radius: var(--crm-radius-md);
    background: var(--notice-bg);
    color: var(--crm-text);
    font-size: var(--crm-text-sm);
    line-height: 1.5;
    overflow-wrap: anywhere;
  }
  [data-tone='warning'] {
    --notice-color: var(--crm-warning);
    --notice-bg: var(--crm-warning-bg);
  }
  [data-tone='success'] {
    --notice-color: var(--crm-success);
    --notice-bg: var(--crm-success-bg);
  }
  [data-tone='info'] {
    --notice-color: var(--crm-info);
    --notice-bg: var(--crm-info-bg);
  }
  .notice-icon {
    display: flex;
    flex: none;
    color: var(--notice-color);
    padding-top: 0.15rem;
  }
  .notice-content {
    min-width: 0;
    flex: 1;
  }
  h1,
  h2,
  p {
    margin: 0;
  }
  h2 {
    font-size: inherit;
    font-weight: 650;
    margin-bottom: var(--crm-space-1);
  }
  .notice-actions {
    display: flex;
    flex-wrap: wrap;
    gap: var(--crm-space-3);
    margin-top: var(--crm-space-4);
  }
  .page {
    flex-direction: column;
    align-items: center;
    text-align: center;
    margin: 0;
    padding: 0;
    border: 0;
    background: transparent;
  }
  .page .notice-icon {
    padding: var(--crm-space-3);
    border-radius: var(--crm-radius-md);
    background: var(--notice-bg);
  }
  .page .notice-content {
    width: 100%;
  }
  .page h1 {
    font-size: var(--crm-text-xl);
    line-height: 1.3;
    font-weight: 650;
    margin-bottom: var(--crm-space-3);
  }
  .page p {
    color: var(--crm-text-muted);
  }
  .page .notice-actions {
    justify-content: center;
    margin-top: var(--crm-space-5);
  }
  @media (max-width: 480px) {
    .page .notice-actions {
      flex-direction: column;
    }
  }
</style>
