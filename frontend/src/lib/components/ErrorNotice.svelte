<script>
  import { TriangleAlert } from '@lucide/svelte';
  /** @type {{ message: string }} */
  let { message } = $props();
</script>

{#if message}
  <div class="crm-error-notice" role="alert">
    <TriangleAlert size={18} aria-hidden="true" />
    <p>{message}</p>
  </div>
{/if}

<style>
  .crm-error-notice {
    display: flex;
    align-items: flex-start;
    gap: var(--crm-space-2);
    padding: var(--crm-space-3) var(--crm-space-4);
    border: 1px solid var(--crm-danger);
    border-radius: var(--crm-radius-md);
    background: var(--crm-danger-bg);
    color: var(--crm-danger);
    font-size: var(--crm-text-sm);
    line-height: 1.5;
    min-width: 0;
  }
  .crm-error-notice :global(svg) {
    flex-shrink: 0;
    margin-top: 0.15rem;
  }
  p {
    margin: 0;
    overflow-wrap: anywhere;
  }
</style>
