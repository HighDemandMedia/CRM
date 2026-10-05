<script>
  import { page } from '$app/state';
  import { resolve } from '$app/paths';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import { BookOpen, MessageCircle } from '@lucide/svelte';
  let knowledge = $derived(page.url.pathname.startsWith('/help/knowledge'));
</script>

<PageHeader title="Help"
  >{#snippet sub()}Guidance and support from High Demand Media{/snippet}</PageHeader
>
<nav class="help-tabs" aria-label="Help sections">
  <a href={resolve('/help')} aria-current={!knowledge ? 'page' : undefined}
    ><MessageCircle size={16} />Contact support</a
  >
  <a href={resolve('/help/knowledge')} aria-current={knowledge ? 'page' : undefined}
    ><BookOpen size={16} />Knowledge base</a
  >
</nav>

<style>
  .help-tabs {
    display: flex;
    gap: var(--crm-space-6);
    margin: 0 28px;
    border-bottom: 1px solid var(--v2-line);
    flex-shrink: 0;
  }
  .help-tabs a {
    display: flex;
    align-items: center;
    gap: var(--crm-space-2);
    padding: 14px 0;
    font-size: var(--crm-text-sm);
    color: var(--v2-slate);
    border-bottom: 2px solid transparent;
    text-decoration: none;
  }
  .help-tabs a[aria-current] {
    border-color: var(--v2-ink, var(--crm-text));
    color: var(--v2-ink, var(--crm-text));
    font-weight: 600;
  }
  .help-tabs a:focus-visible {
    outline: 2px solid var(--crm-focus);
    outline-offset: 3px;
  }
  @media (max-width: 600px) {
    .help-tabs {
      margin: 0 var(--crm-space-4);
      gap: 18px;
    }
  }
</style>
