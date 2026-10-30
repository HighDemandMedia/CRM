<script>
  import NavigationTiming from '$lib/v2/components/NavigationTiming.svelte';
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();

  import StageTransitionLayer from '$lib/components/pipelines/StageTransitionLayer.svelte';
  import CreateLayer from '$lib/components/creation/CreateLayer.svelte';
  import { Toaster } from 'svelte-sonner';
  import { onMount } from 'svelte';
  import { PanelLeftClose, PanelLeftOpen } from '@lucide/svelte';
  import { resolve } from '$app/paths';
  import '../../app.css';
  import '$lib/v2/styles/v2.css';
  import '$lib/v2/styles/preferences.css';
  import { page, navigating } from '$app/state';
  import PreferencesNav from '$lib/v2/components/PreferencesNav.svelte';
  import Sidebar from '$lib/v2/components/Sidebar.svelte';
  import CommandPalette from '$lib/v2/components/CommandPalette.svelte';

  /** @type {{ data: { performanceDiagnostics?: boolean, accountUser: { name?: string, email?: string }, accountId: string, counts: Record<string, number> | Promise<Record<string, number>>, org: { name: string, terminology?: Record<string, string> | null }, role: string, isSuperAdmin?: boolean, platformAccess?: { return_organization: { id: string, name: string } | null } | null, lifecycle?: { read_only: boolean } }, children: import('svelte').Snippet }} */
  let { data, children } = $props();

  let preferencesOpen = $derived(
    ['/profile', '/team', '/settings', '/notifications'].some(
      (path) => page.url.pathname === path || page.url.pathname.startsWith(`${path}/`)
    )
  );

  let paletteOpen = $state(false);
  let returningToAccount = $state(false);
  let navigationHidden = $state(false);
  onMount(() => {
    try {
      navigationHidden = localStorage.getItem('crm-navigation-hidden') === 'true';
    } catch {
      /* Keep navigation usable when browser storage is unavailable. */
    }
  });
  function toggleNavigation() {
    navigationHidden = !navigationHidden;
    try {
      localStorage.setItem('crm-navigation-hidden', String(navigationHidden));
    } catch {
      /* Keep navigation usable when browser storage is unavailable. */
    }
  }
</script>

<svelte:head>
  <title>High Demand Media CRM</title>
  <meta name="robots" content="noindex" />
</svelte:head>

<NavigationTiming enabled={data.performanceDiagnostics} />
<Toaster position="top-right" closeButton />
{#if navigating.to}<div class="navigation-progress" aria-hidden="true"></div>{/if}

<div class="v2-desktop-viewport">
  <div class="v2-root v2-shell">
    <div class="desktop-navigation" class:collapsed={navigationHidden}>
      <div id="desktop-navigation-content">
        <Sidebar
          collapsed={navigationHidden}
          counts={data.counts}
          org={data.org}
          user={data.accountUser}
          accountId={data.accountId}
          role={data.role}
          isSuperAdmin={data.isSuperAdmin}
          terminology={data.org.terminology}
          onsearch={() => (paletteOpen = true)}
        />
      </div>
      <button
        class="navigation-toggle"
        type="button"
        onclick={toggleNavigation}
        aria-label={navigationHidden ? ui('Show navigation') : ui('Hide navigation')}
        title={navigationHidden ? ui('Show navigation') : ui('Hide navigation')}
        aria-expanded={!navigationHidden}
        aria-controls="desktop-navigation-content"
      >
        {#if navigationHidden}<PanelLeftOpen size={16} />{:else}<PanelLeftClose size={16} />{/if}
      </button>
    </div>
    <div class="v2-main">
      {#if data.platformAccess}
        <aside class="support-banner" aria-label={ui('Support view')}>
          <span>{ui('Viewing account: {name}', { name: data.org.name })}</span>
          {#if data.platformAccess.return_organization}
            <form
              method="POST"
              action={resolve('/settings/organization?/switchOrg')}
              onsubmit={() => (returningToAccount = true)}
            >
              <input
                type="hidden"
                name="org_id"
                value={data.platformAccess.return_organization.id}
              />
              <button class="v2-btn" type="submit" disabled={returningToAccount}>
                {returningToAccount ? ui('Switching organization…') : ui('Return to my account')}
              </button>
            </form>
          {/if}
        </aside>
      {/if}
      {#if data.lifecycle?.read_only}
        <div class="closure-banner" role="status">
          {ui('This organization is closing. You can still view and export records.')}
        </div>
      {/if}
      <div class="page-workspace" class:preferences-workspace={preferencesOpen}>
        {#if navigating.to}
          <div class="route-loading-label" role="status">{ui('Loading…')}</div>
        {/if}
        {#if preferencesOpen}<PreferencesNav />{/if}
        <div
          class="route-content"
          aria-busy={!!navigating.to}
          class:with-preferences={preferencesOpen}
          class:crm-pill-controls={preferencesOpen}
        >
          {@render children()}
        </div>
      </div>
    </div>

    <CreateLayer />
    <StageTransitionLayer />
    <CommandPalette open={paletteOpen} onclose={() => (paletteOpen = false)} />
  </div>
</div>

<style>
  .page-workspace {
    position: relative;
  }
  .route-loading-label {
    position: absolute;
    z-index: 30;
    top: 12px;
    left: 50%;
    transform: translateX(-50%);
    padding: 6px 14px;
    border: 1px solid var(--v2-line);
    border-radius: var(--crm-button-radius);
    background: var(--v2-card);
    color: var(--v2-muted);
    font-size: 13px;
    pointer-events: none;
    opacity: 0;
    animation: reveal-loading 100ms 120ms forwards;
  }
  @keyframes reveal-loading {
    to {
      opacity: 1;
    }
  }
  .support-banner {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: var(--crm-space-2) var(--crm-space-4);
    padding: var(--crm-space-2) var(--crm-space-5);
    border-bottom: 2px solid var(--v2-accent, #c82322);
    background: var(--crm-surface);
    color: var(--crm-text-primary);
    font-size: var(--crm-text-sm);
    font-weight: 600;
    flex-shrink: 0;
  }
  .support-banner span {
    min-width: 0;
    overflow-wrap: anywhere;
    flex: 1 1 12rem;
  }
  .support-banner button {
    min-height: 44px;
    white-space: normal;
  }

  .navigation-progress {
    position: fixed;
    inset: 0 0 auto;
    z-index: 100;
    height: 0.1875rem;
    background: var(--v2-accent, #c82322);
    pointer-events: none;
  }

  .closure-banner {
    padding: var(--crm-space-3) var(--crm-space-5);
    border-bottom: 1px solid var(--v2-line-soft);
    background: var(--crm-surface);
    color: var(--crm-text-primary);
    font-size: var(--crm-text-sm);
    flex-shrink: 0;
  }
  .page-workspace {
    display: flex;
    flex: 1;
    min-height: 0;
    min-width: 0;
    overflow: hidden;
  }
  .route-content {
    container: crm-workspace / inline-size;
    display: flex;
    flex-direction: column;
    flex: 1;
    min-width: 0;
    min-height: 0;
    overflow: hidden;
  }

  .with-preferences {
    container: preferences-body / inline-size;
  }

  .desktop-navigation {
    position: relative;
    display: flex;
    flex-shrink: 0;
  }
  .desktop-navigation.collapsed {
    width: 64px;
  }
  .navigation-toggle {
    position: absolute;
    top: 16px;
    right: -12px;
    z-index: 20;
    width: 26px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1px solid var(--v2-line);
    border-radius: var(--crm-radius-sm);
    background: var(--v2-bg, white);
    color: var(--v2-ink);
    cursor: pointer;
  }
  .collapsed .navigation-toggle {
    right: -12px;
  }
  #desktop-navigation-content {
    height: 100%;
  }
  #desktop-navigation-content :global(.v2-nav) {
    height: 100%;
  }
</style>
