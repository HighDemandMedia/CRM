<script>
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();

  import NotificationBell from '$lib/v2/components/NotificationBell.svelte';
  import { afterNavigate } from '$app/navigation';
  import { onMount } from 'svelte';
  import { ChevronDown } from '@lucide/svelte';
  import { resolve, base } from '$app/paths';
  import { asInternalPath } from '$lib/utils/paths.js';
  import { page } from '$app/state';
  import {
    Sun,
    ChartNoAxesCombined,
    CalendarDays,
    Columns3,
    Building2,
    Users,
    CircleCheck,
    LifeBuoy,
    CircleUser,
    CircleHelp,
    Search,
    LogOut
  } from '@lucide/svelte';
  import { t } from '$lib/terminology.js';

  /**
   * One flat tree, grouped by what the person is doing rather than by which
   * Django app owns the model. Every label matches the route it lands on and
   * the page title it lands on; "Deals" opens the /pipeline route.
   *
   * v1 had /leads listed twice, as "Pipeline" and as "Leads", and a "Deals"
   * entry pointing at /opportunities while /deals 404'd.
   *
   * `termKey` marks the handful of entity destinations a vertical pack may
   * relabel (see `$lib/terminology.js`). The string in `label` below is only
   * ever the fallback an org with no pack, or no override for that key,
   * still renders; the derived `groups` below is what actually resolves it
   * against `terminology`. No other label branches on the org at all.
   *
   * @type {{
   *   user?: { name?: string, email?: string },
   *   accountId?: string,
   *   collapsed?: boolean,
   *   counts?: Record<string, number> | Promise<Record<string, number>>,
   *   org?: { name: string },
   *   role?: string,
   *   isSuperAdmin?: boolean,
   *   terminology?: Record<string, string> | null,
   *   onsearch?: () => void
   * }}
   */
  let {
    user = {},
    accountId = '',
    collapsed = false,
    counts = {},
    org = { name: 'High Demand Media CRM' },
    role = 'USER',
    isSuperAdmin = false,
    terminology = undefined,
    onsearch = () => {}
  } = $props();

  const uid = $props.id();
  let accountPanel = $state(/** @type {HTMLDivElement | undefined} */ (undefined));
  let panelLeft = $state(8);
  let panelBottom = $state(72);
  let accountOpen = $state(false);
  let displayName = $derived(user.name || user.email?.split('@')[0] || 'Your profile');
  afterNavigate(() => accountPanel?.hidePopover());
  let organizations = $state([]);
  let organizationLoading = $state(false);
  let organizationError = $state('');
  let selectedOrganization = $state('');
  let switchingOrganization = $state(false);
  async function loadOrganizations() {
    organizationLoading = true;
    organizationError = '';
    selectedOrganization = accountId;
    try {
      const response = await fetch(`${base}/api/organizations`, { cache: 'no-store' });
      if (!response.ok) throw new Error();
      const result = await response.json();
      organizations = result.organizations;
    } catch {
      organizationError = 'Could not load organizations.';
    } finally {
      organizationLoading = false;
    }
  }
  function positionAccount(event) {
    if (!accountOpen) void loadOrganizations();
    const rect = event.currentTarget.getBoundingClientRect();
    panelLeft = Math.max(8, Math.min(rect.left, window.innerWidth - 348));
    panelBottom = window.innerHeight - rect.top + 8;
  }

  let folded = $state(/** @type {string[]} */ ([]));
  onMount(() => {
    try {
      const saved = JSON.parse(localStorage.getItem('crm.nav.groups') || '[]');
      if (Array.isArray(saved)) folded = saved.filter((x) => typeof x === 'string');
    } catch {
      /* Keep navigation usable when browser storage is unavailable. */
    }
  });
  function toggleGroup(label) {
    folded = folded.includes(label) ? folded.filter((x) => x !== label) : [...folded, label];
    try {
      localStorage.setItem('crm.nav.groups', JSON.stringify(folded));
    } catch {
      /* Keep navigation usable when browser storage is unavailable. */
    }
  }
  /** @type {{label: string, items: {href: string, label: string, icon: typeof Sun, exact?: boolean, termKey?: string, count?: string}[]}[]} */
  const GROUPS = [
    {
      label: 'Sell',
      items: [
        { href: '/', label: 'Today', icon: Sun, exact: true },
        { href: '/contacts', label: 'Contacts', icon: Users, termKey: 'contact.plural' },
        { href: '/accounts', label: 'Companies', icon: Building2, termKey: 'account.plural' },
        {
          href: '/pipeline',
          label: 'Deals',
          icon: Columns3,
          termKey: 'opportunity.plural'
        },
        { href: '/calendar', label: 'Calendar', icon: CalendarDays },
        { href: '/reports', label: 'Reports', icon: ChartNoAxesCombined }
      ]
    },
    {
      label: 'Serve',
      items: [
        { href: '/tasks', label: 'Tasks', icon: CircleCheck },
        // Approvals and Analytics live under Tickets as section tabs. They are
        // not separate destinations, so they do not get separate nav entries,
        // one level of navigation, and the tab strip carries the rest.
        { href: '/tickets', label: 'Tickets', icon: LifeBuoy }
      ]
    }
  ];

  // Resolve organization-specific labels for the main CRM destinations.
  let groups = $derived(
    GROUPS.map((group) => ({
      ...group,
      items: group.items
        .filter((item) => {
          const module = {
            '/contacts': 'contacts',
            '/accounts': 'companies',
            '/pipeline': 'deals',
            '/tasks': 'tasks',
            '/tickets': 'tickets',
            '/calendar': 'calendar',
            '/reports': 'reports'
          }[item.href];
          return (
            !module ||
            (!!page.data.permissions?.rules?.[module]?.view &&
              page.data.permissions.rules[module].view !== 'none')
          );
        })
        .map((item) =>
          item.termKey
            ? { ...item, label: t(terminology, item.termKey, ui(item.label)) }
            : { ...item, label: ui(item.label) }
        )
    })).filter((group) => group.items.length > 0)
  );

  const isActive = (href, exact) =>
    exact ? page.url.pathname === href : page.url.pathname.startsWith(href);
</script>

<nav class="v2-nav" class:collapsed aria-label={ui('Main')}>
  <div class="nav-scroll">
    <a
      class="v2-org brand-home"
      href={resolve('/')}
      aria-label="High Demand Media — Today"
      title={ui('Today')}
    >
      <img
        class="v2-brand-mark brand-symbol"
        src={`${base}/brand/hdm-symbol.png`}
        alt="High Demand Media"
        width="228"
        height="155"
      />
      <b>High Demand<br />Media</b>
    </a>
    {#key accountId + (user.email || '')}<NotificationBell {collapsed} />{/key}

    <button
      class="v2-link v2-nav-search"
      type="button"
      onclick={onsearch}
      aria-label={ui('Search')}
      title={collapsed ? ui('Search') : undefined}
    >
      <Search />
      <span class="nav-text">{ui('Search')}</span>
      <span class="v2-count">⌘K</span>
    </button>

    <!--
    No entry appears here without a route behind it. v1's "Deals" pointed at
    /opportunities while /deals 404'd; an Inbox link with nothing behind it
    would be the same mistake.
  -->
    {#each groups as group (group.label)}
      {#if collapsed}<div class="nav-divider"></div>{:else}<button
          class="v2-nav-group v2-label group-toggle"
          type="button"
          aria-expanded={!folded.includes(group.label)}
          onclick={() => toggleGroup(group.label)}
          >{ui(group.label)}<ChevronDown
            size={12}
            style={folded.includes(group.label) ? 'transform:rotate(-90deg)' : ''}
          /></button
        >{/if}
      {#if collapsed || !folded.includes(group.label)}
        {#each group.items as item (item.href)}
          <a
            class="v2-link"
            href={resolve(asInternalPath(item.href))}
            aria-label={item.label}
            title={collapsed ? item.label : undefined}
            aria-current={isActive(item.href, item.exact) ? 'page' : undefined}
          >
            <item.icon />
            <span class="nav-text">{item.label}</span>

            {#if 'count' in item && item.count}
              {#await counts then readyCounts}
                {#if readyCounts[item.count]}<span class="v2-count">{readyCounts[item.count]}</span
                  >{/if}
              {/await}
            {/if}
          </a>
        {/each}
      {/if}
    {/each}
  </div>
  <div class="account-footer">
    <a
      class="v2-link"
      href={resolve('/help')}
      aria-label={ui('Help')}
      title={collapsed ? ui('Help') : undefined}
      aria-current={isActive('/help', false) ? 'page' : undefined}
    >
      <CircleHelp /><span class="nav-text">{ui('Help')}</span>
    </a>
    <button
      type="button"
      class="account-trigger"
      popovertarget={`${uid}-account`}
      aria-label={ui('Organization menu')}
      aria-expanded={accountOpen}
      title={collapsed ? displayName : undefined}
      onclick={positionAccount}
    >
      <span class="account-avatar"><CircleUser size={26} /></span>
      <span class="account-trigger-text"
        ><strong>{displayName}</strong><small>{org.name}</small></span
      >
      {#if !collapsed}<ChevronDown size={15} />{/if}
    </button>
  </div>
  <div
    id={`${uid}-account`}
    bind:this={accountPanel}
    popover="auto"
    class="account-panel"
    style:left={`${panelLeft}px`}
    style:bottom={`${panelBottom}px`}
    ontoggle={(event) => (accountOpen = event.newState === 'open')}
  >
    <div class="account-identity">
      <span class="account-avatar"><CircleUser size={32} /></span>
      <div><strong>{displayName}</strong><span>{user.email}</span></div>
    </div>
    <a
      class="account-action"
      href={resolve('/profile')}
      onclick={() => accountPanel?.hidePopover()}
    >
      <CircleUser size={17} />
      {ui('Profile & Preferences')}
    </a>
    <form
      class="account-details"
      method="POST"
      action={resolve('/settings/organization?/switchOrg')}
      onsubmit={() => (switchingOrganization = true)}
    >
      {#if organizations.length > 1}
        <label for={`${uid}-organization`}>{ui('Organization')}</label>
      {:else}
        <span>{ui('Organization')}</span>
      {/if}
      <div class="organization-name">
        {#if organizations.length > 1}
          <input type="hidden" name="org_id" value={selectedOrganization || accountId} />
          <select
            id={`${uid}-organization`}
            value={selectedOrganization || accountId}
            disabled={organizationLoading || switchingOrganization}
            onchange={(event) => {
              selectedOrganization = event.currentTarget.value;
              if (selectedOrganization && selectedOrganization !== accountId) {
                const form = event.currentTarget.form;
                const input = form?.elements.namedItem('org_id');
                if (input instanceof HTMLInputElement) input.value = selectedOrganization;
                form?.requestSubmit();
              }
            }}
          >
            {#if !organizations.some((organization) => organization.id === accountId)}<option
                value={accountId}>{org.name}</option
              >{/if}
            {#each organizations as organization (organization.id)}<option value={organization.id}
                >{organization.name}</option
              >{/each}
          </select>
          <ChevronDown size={14} aria-hidden="true" />
        {:else}
          <strong class="current-organization">{org.name}</strong>
        {/if}
      </div>
      {#if accountId}<span class="account-id">ID: {accountId}</span>{/if}
      <span
        >{page.data.isPlatformOwner
          ? ui('Platform owner')
          : isSuperAdmin
            ? ui('Super Admin')
            : role === 'ADMIN'
              ? ui('Admin')
              : ui('Member')}</span
      >
      {#if switchingOrganization}<small role="status">{ui('Switching organization…')}</small>{/if}
      {#if organizationError}<p class="organization-error" role="alert">{organizationError}</p>
        <button class="account-action" type="button" onclick={loadOrganizations}
          >{ui('Try again')}</button
        >{/if}
    </form>
    <div class="account-signout">
      <a class="account-action" href={resolve('/logout')} data-sveltekit-reload
        ><LogOut size={17} />{ui('Sign out')}</a
      >
    </div>
  </div>
</nav>

<style>
  .nav-scroll {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    overflow-x: hidden;
  }
  .account-footer {
    flex-shrink: 0;
    border-top: 1px solid var(--crm-nav-border);
    padding-top: 10px;
    margin-top: var(--crm-space-2);
  }
  .account-trigger {
    display: flex;
    gap: 9px;
    align-items: center;
    width: 100%;
    padding: var(--crm-space-2) 5px;
    border: 0;
    border-radius: var(--crm-radius-md);
    background: transparent;
    color: inherit;
    font: inherit;
    text-align: left;
    cursor: pointer;
  }
  .account-trigger:hover,
  .account-trigger[aria-expanded='true'] {
    background: var(--crm-nav-hover);
  }
  .account-trigger-text {
    flex: 1;
    min-width: 0;
  }
  .account-trigger-text strong,
  .account-trigger-text small {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .account-trigger-text strong {
    font-size: var(--crm-text-xs);
  }
  .account-trigger-text small {
    font-size: var(--crm-text-xs);
    color: var(--crm-nav-muted);
    margin-top: 3px;
  }
  .account-avatar {
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .collapsed .account-trigger {
    justify-content: center;
  }
  .collapsed .account-trigger-text {
    display: none;
  }
  .account-panel {
    position: fixed;
    top: auto;
    right: auto;
    margin: 0;
    width: 332px;
    max-width: calc(100vw - 16px);
    max-height: min(580px, calc(100dvh - 100px));
    overflow-y: auto;
    box-sizing: border-box;
    padding: 10px;
    border: 1px solid var(--crm-border);
    border-radius: var(--crm-radius-lg);
    background: var(--crm-surface);
    color: var(--crm-text);
    box-shadow: var(--crm-shadow-lg);
    font-family: inherit;
  }
  .account-identity {
    display: flex;
    gap: var(--crm-space-3);
    padding: var(--crm-space-3) 10px;
    align-items: center;
  }
  .account-identity div {
    min-width: 0;
  }
  .account-identity strong {
    display: block;
    font-size: var(--crm-text-sm);
    overflow-wrap: anywhere;
  }
  .account-identity span:not(.account-avatar) {
    display: block;
    color: var(--crm-text-muted);
    font-size: var(--crm-text-xs);
    overflow-wrap: anywhere;
    margin-top: var(--crm-space-1);
  }
  .account-action {
    display: flex;
    align-items: center;
    gap: 9px;
    padding: 11px 10px;
    border-radius: var(--crm-radius-md);
    color: inherit;
    text-decoration: none;
    font-size: var(--crm-text-sm);
    font-weight: 550;
  }
  .account-action:hover {
    background: var(--crm-surface-secondary);
  }
  .account-action:focus-visible,
  .account-trigger:focus-visible {
    outline: 2px solid var(--crm-nav-text);
    outline-offset: 2px;
  }
  .account-details {
    display: flex;
    flex-direction: column;
    gap: 5px;
    padding: 14px 10px;
    margin: var(--crm-space-2) 0;
    border-block: 1px solid var(--crm-border);
    font-size: var(--crm-text-xs);
    color: var(--crm-text-muted);
  }
  .account-details label {
    font-size: var(--crm-text-xs);
  }
  .account-id {
    overflow-wrap: anywhere;
    font-size: var(--crm-text-xs);
  }
  .organization-name {
    position: relative;
    display: flex;
    align-items: center;
  }
  .current-organization {
    color: var(--crm-text);
    font-size: var(--crm-text-sm);
    font-weight: 600;
    overflow-wrap: anywhere;
    padding-block: 7px;
  }
  .organization-name select {
    appearance: none;
    width: 100%;
    min-width: 0;
    min-height: var(--crm-control-height);
    padding: var(--crm-control-padding-y) var(--crm-select-padding-end) var(--crm-control-padding-y)
      var(--crm-space-3);
    border: 0;
    border-radius: var(--crm-radius-sm);
    background: transparent;
    color: var(--crm-text);
    font: inherit;
    font-size: var(--crm-text-sm);
    font-weight: 600;
    cursor: pointer;
    text-overflow: ellipsis;
  }
  .organization-name select:hover {
    background: var(--crm-surface-secondary);
  }
  .organization-name select:focus-visible {
    outline: 2px solid var(--crm-nav-text);
    outline-offset: 2px;
  }
  .organization-name select:disabled {
    cursor: wait;
    opacity: 0.65;
  }
  .organization-name :global(svg) {
    position: absolute;
    right: var(--crm-control-padding-x);
    pointer-events: none;
  }
  .organization-error {
    color: var(--v2-rust);
    font-size: var(--crm-text-xs);
    margin: 0;
  }
  .account-signout {
    border-top: 1px solid var(--crm-border);
    padding-top: 6px;
    margin-top: 6px;
  }
  .brand-home {
    color: inherit;
    text-decoration: none;
  }
  .brand-home:focus-visible {
    outline: 2px solid currentColor;
    outline-offset: 3px;
    border-radius: var(--crm-radius-sm);
  }
  .group-toggle {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border: 0;
    background: none;
    cursor: pointer;
    font-family: inherit;
  }
  .nav-divider {
    margin: var(--crm-space-2) 6px;
    border-top: 1px solid var(--crm-nav-border);
  }

  .v2-nav {
    overflow: hidden;
    background: var(--crm-nav-bg);
    color: var(--crm-nav-text);
    border-right-color: var(--crm-nav-border);
  }
  .v2-org {
    flex-shrink: 0;
  }
  .brand-symbol {
    width: 3.25rem;
  }
  .v2-link {
    color: var(--crm-nav-text);
  }
  .v2-link :global(svg) {
    color: var(--crm-nav-muted);
  }
  .v2-link:hover,
  .v2-link[aria-current='page'] {
    background: var(--crm-nav-hover);
    color: var(--crm-nav-text);
  }
  .v2-link[aria-current='page'] {
    background: var(--crm-action-bg);
    color: var(--crm-primary-text);
    font-weight: 700;
  }
  .v2-link[aria-current='page']:hover {
    background: var(--crm-action-hover-bg);
  }
  .v2-link[aria-current='page']:active {
    background: var(--crm-action-active-bg);
  }
  .v2-nav :focus-visible {
    outline: 2px solid var(--crm-nav-text);
    outline-offset: 2px;
  }
  .v2-link[aria-current='page'] :global(svg) {
    color: var(--crm-primary-text);
  }
  .v2-nav-group {
    color: var(--crm-nav-muted);
  }
  .v2-link .v2-count {
    color: var(--crm-nav-muted);
  }
  .collapsed .brand-symbol {
    width: 2.25rem;
  }

  .collapsed {
    width: 64px;
    padding: 13px var(--crm-space-2);
  }
  .collapsed .v2-org {
    justify-content: center;
    padding: 5px 0 13px;
  }
  .collapsed .v2-org b,
  .collapsed .nav-text,
  .collapsed .v2-count {
    display: none;
  }
  .collapsed .v2-link {
    position: relative;
    justify-content: center;
    min-height: 34px;
    flex-shrink: 0;
    padding: var(--crm-space-2);
  }

  /* Search opens an overlay rather than navigating, so it is a button. It
     borrows .v2-link for everything else. A control that sits in a list of
     links should not look like the odd one out. */
  .v2-nav-search {
    width: 100%;
    background: none;
    border: 0;
    font-family: inherit;
    font-size: inherit;
    text-align: left;
    cursor: pointer;
  }
</style>
