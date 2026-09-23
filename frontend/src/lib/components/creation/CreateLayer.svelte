<script>
  import { beforeNavigate, preloadData, invalidateAll } from '$app/navigation';
  import { page } from '$app/state';
  import CreatePanel from './CreatePanel.svelte';
  const routes = {
    '/contacts/new': [
      'New contact',
      () => import('../../../routes/(app)/contacts/new/+page.svelte')
    ],
    '/accounts/new': [
      'New company',
      () => import('../../../routes/(app)/accounts/new/+page.svelte')
    ],
    '/pipeline/new': ['New deal', () => import('../../../routes/(app)/pipeline/new/+page.svelte')],
    '/tasks/new': ['New task', () => import('../../../routes/(app)/tasks/new/+page.svelte')],
    '/tickets/new': ['New ticket', () => import('../../../routes/(app)/tickets/new/+page.svelte')]
  };
  const editors = {
    contacts: ['Edit contact', () => import('../../../routes/(app)/contacts/[id]/edit/+page.svelte')],
    accounts: ['Edit company', () => import('../../../routes/(app)/accounts/[id]/edit/+page.svelte')],
    pipeline: ['Edit deal', () => import('../../../routes/(app)/pipeline/[id]/edit/+page.svelte')],
    tasks: ['Edit task', () => import('../../../routes/(app)/tasks/[id]/edit/+page.svelte')],
    tickets: ['Edit ticket', () => import('../../../routes/(app)/tickets/[id]/edit/+page.svelte')]
  };
  let panel = $state(null),
    loading = $state(false),
    message = $state(''),
    error = $state('');
  let sequence = 0;
  function formRoute(path) {
    const key = path.replace(/\/$/, '');
    if (routes[key]) return routes[key];
    const match = key.match(/^\/(contacts|accounts|pipeline|tasks|tickets)\/[0-9a-f-]{36}\/edit$/i);
    if (match && page.url.pathname.replace(/\/$/, '') === `/${match[1]}`)
      return editors[match[1]];
    return null;
  }
  async function open(url) {
    const [title, load] = formRoute(url.pathname);
    const current = ++sequence;
    loading = true;
    error = '';
    message = '';
    try {
      const [result, component] = await Promise.all([preloadData(url.href), load()]);
      if (sequence !== current) return;
      if (result.type !== 'loaded' || result.status >= 400) throw new Error();
      panel = { url: url.href, title, component: component.default, data: result.data };
    } catch {
      if (sequence === current) error = 'Could not open the form. Please try again.';
    } finally {
      if (sequence === current) loading = false;
    }
  }
  beforeNavigate((navigation) => {
    if (navigation.type === 'popstate' || navigation.willUnload) return;
    const target = navigation.to?.url;
    if (!target || target.origin !== page.url.origin || !formRoute(target.pathname))
      return;
    navigation.cancel();
    if (!panel && !loading) void open(target);
  });
  async function created() {
    const editing = panel.title.startsWith('Edit ');
    const title = panel.title.replace(/^(New|Edit) /, '');
    panel = null;
    message = `${title[0].toUpperCase()}${title.slice(1)} ${editing ? 'saved' : 'created'}.`;
    try {
      await invalidateAll();
    } catch {
      error = 'Saved successfully, but the view could not refresh. Reload to see the new record.';
    }
  }
</script>

{#if panel}<CreatePanel {...panel} onclose={() => (panel = null)} oncreated={created} />{/if}
{#if loading || message || error}<div class="notice" role={error ? 'alert' : 'status'}>
    {loading ? 'Opening form…' : error || message}
    {#if !loading}<button
        aria-label="Dismiss notification"
        onclick={() => {
          message = '';
          error = '';
        }}>×</button
      >{/if}
  </div>{/if}

<style>
  .notice {
    position: fixed;
    bottom: 24px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 100;
    background: var(--v2-card);
    color: var(--v2-ink);
    padding: 12px 16px;
    border: 1px solid var(--v2-line);
    border-radius: 9px;
    box-shadow: 0 4px 20px #0001;
    display: flex;
    gap: 16px;
    max-width: 90vw;
  }
  .notice button {
    border: 0;
    background: transparent;
    color: inherit;
    cursor: pointer;
  }
</style>
