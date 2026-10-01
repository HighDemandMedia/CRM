<script>
  import StageTransitionLayer from '$lib/components/pipelines/StageTransitionLayer.svelte';
  import CreateLayer from '$lib/components/creation/CreateLayer.svelte';
  import { Toaster } from 'svelte-sonner';
  import { onMount } from 'svelte';
  import { PanelLeftClose, PanelLeftOpen } from '@lucide/svelte';
  import { resolve, base } from '$app/paths';
  import { asInternalPath } from '$lib/utils/paths.js';
  import '../../app.css';
  import '$lib/v2/styles/v2.css';
  import { page } from '$app/state';
  import { afterNavigate } from '$app/navigation';
  import PreferencesNav from '$lib/v2/components/PreferencesNav.svelte';
  import Sidebar from '$lib/v2/components/Sidebar.svelte';
  import CommandPalette from '$lib/v2/components/CommandPalette.svelte';
  import { Search, Sun, Columns3, LifeBuoy, Receipt, Plus, Menu } from '@lucide/svelte';

  /** @type {{ data: { accountUser: { name?: string, email?: string }, accountId: string, counts: Record<string, number> | Promise<Record<string, number>>, org: { name: string, terminology?: Record<string, string> | null }, role: string, isSuperAdmin?: boolean }, children: import('svelte').Snippet }} */
  let { data, children } = $props();

  let preferencesOpen = $derived(
    ['/profile', '/team', '/settings', '/notifications'].some(
      (path) => page.url.pathname === path || page.url.pathname.startsWith(`${path}/`)
    )
  );

  let paletteOpen = $state(false);
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

  // The sidebar is hidden below 768px, and the tab bar only carries four of the
  // ~16 destinations. This drawer is how a phone reaches the rest of the nav and
  // the footer: profile, notifications, help, sign out. It reuses the same
  // <Sidebar>, so the two can never drift apart. Closes itself on navigation.
  let menuOpen = $state(false);
  afterNavigate(() => (menuOpen = false));

  /** Focus the panel on open so Escape reaches it and keyboard users land inside. */
  function autofocus(/** @type {HTMLElement} */ node) {
    node.focus();
  }

  /**
   * The five things worth a thumb on a phone. Fewer than the sidebar on
   * purpose. A tab bar that scrolls is a menu wearing a tab bar's clothes.
   */
  const TABS = [
    { href: '/', label: 'Today', icon: Sun, exact: true },
    { href: '/pipeline', label: 'Pipeline', icon: Columns3 },
    { href: '/tickets', label: 'Tickets', icon: LifeBuoy },
    { href: '/invoices', label: 'Invoices', icon: Receipt }
  ];

  const isActive = (href, exact) =>
    exact ? page.url.pathname === href : page.url.pathname.startsWith(href);

  function onkeydown(e) {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      paletteOpen = !paletteOpen;
    } else if (e.key === 'Escape' && menuOpen) {
      menuOpen = false;
    }
  }
</script>

<svelte:head>
  <title>High Demand Media CRM</title>
  <meta name="robots" content="noindex" />
</svelte:head>

<svelte:window {onkeydown} />
<Toaster position="top-right" closeButton />

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
      aria-label={navigationHidden ? 'Show navigation' : 'Hide navigation'}
      title={navigationHidden ? 'Show navigation' : 'Hide navigation'}
      aria-expanded={!navigationHidden}
      aria-controls="desktop-navigation-content"
    >
      {#if navigationHidden}<PanelLeftOpen size={16} />{:else}<PanelLeftClose size={16} />{/if}
    </button>
  </div>
  <div class="v2-main">
    <!-- Phone top bar. The sidebar is hidden below 768px; this replaces the
         org mark and the search affordance it carried. -->
    <div class="v2-mobile-top">
      <button
        class="v2-btn v2-btn-quiet"
        type="button"
        onclick={() => (menuOpen = true)}
        aria-label="Open menu"
        aria-expanded={menuOpen}
      >
        <Menu />
      </button>
      <img src={`${base}/brand/hdm-symbol.png`} alt="High Demand Media" width="36" height="25" />
      <h2>{data.org.name}</h2>
      <button
        class="v2-btn v2-btn-quiet"
        type="button"
        style="margin-left:auto"
        onclick={() => (paletteOpen = true)}
        aria-label="Search"
      >
        <Search />
      </button>
    </div>

    <div class="page-workspace">
      {#if preferencesOpen}<PreferencesNav />{/if}
      <div class="route-content" class:with-preferences={preferencesOpen}>{@render children()}</div>
    </div>

    <nav class="v2-tabbar" aria-label="Sections">
      {#each TABS as tab (tab.href)}
        <a
          href={resolve(asInternalPath(tab.href))}
          aria-current={isActive(tab.href, tab.exact) ? 'page' : undefined}
        >
          <tab.icon />
          {tab.label}
        </a>
      {/each}
    </nav>
  </div>

  <!-- Both live inside .v2-root so they inherit the scoped tokens; both are
       position:fixed, so the shell's overflow:hidden does not clip them. -->
  <a class="v2-fab" href={resolve('/pipeline/new')} aria-label="New deal"><Plus size={21} /></a>

  <!-- Mobile navigation drawer. Only openable from the mobile top bar, so it
       never surfaces on desktop; a backdrop click, Escape, or navigating all
       close it. It renders the same <Sidebar> the desktop shows. -->
  {#if menuOpen}
    <div
      class="v2-drawer-scrim"
      role="presentation"
      onclick={(e) => {
        if (e.target === e.currentTarget) menuOpen = false;
      }}
    >
      <div
        class="v2-drawer"
        role="dialog"
        aria-modal="true"
        aria-label="Navigation"
        tabindex="-1"
        use:autofocus
        onkeydown={(e) => {
          if (e.key === 'Escape') {
            e.preventDefault();
            menuOpen = false;
          }
        }}
      >
        <Sidebar
          counts={data.counts}
          org={data.org}
          user={data.accountUser}
          accountId={data.accountId}
          role={data.role}
          isSuperAdmin={data.isSuperAdmin}
          terminology={data.org.terminology}
          onsearch={() => {
            menuOpen = false;
            paletteOpen = true;
          }}
        />
      </div>
    </div>
  {/if}

  <CreateLayer />
  <StageTransitionLayer />
  <CommandPalette open={paletteOpen} onclose={() => (paletteOpen = false)} />
</div>

<style>
  .page-workspace {
    display: flex;
    flex: 1;
    min-height: 0;
    min-width: 0;
    overflow: hidden;
  }
  .route-content {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-width: 0;
    min-height: 0;
    overflow: hidden;
  }
  @media (max-width: 767px) {
    .page-workspace {
      flex-direction: column;
    }
  }

  .with-preferences {
    container: preferences-body / inline-size;
  }
  @container preferences-body (max-width: 700px) {
    .route-content :global(.v2-split),
    .route-content :global(.v2-split-wide) {
      grid-template-columns: 1fr;
    }
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
    border-radius: 6px;
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
  @media (max-width: 767px) {
    .desktop-navigation {
      display: none;
    }
  }
</style>
