<script>
  import { page } from '$app/state';
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { asInternalPath } from '$lib/utils/paths.js';
  import {
    Bell,
    CircleUser,
    Users,
    ShieldCheck,
    ListFilter,
    Columns3,
    Building2,
    Tag,
    FileText,
    ChevronDown,
    ArrowLeft
  } from '@lucide/svelte';

  const allGroups = [
    {
      label: 'Personal',
      items: [
        { label: 'Profile', href: '/profile', icon: CircleUser },
        { label: 'Notifications', href: '/notifications', icon: Bell }
      ]
    },
    {
      label: 'Organization & access',
      items: [
        { label: 'Organization', href: '/settings/organization', icon: Building2 },
        { label: 'Users & Teams', href: '/team', icon: Users },
        { label: 'Roles & Permissions', href: '/settings/roles', icon: ShieldCheck }
      ]
    },
    {
      label: 'CRM configuration',
      items: [
        { label: 'Properties', href: '/settings/custom-fields', icon: ListFilter },
        { label: 'Pipelines', href: '/settings/pipelines', icon: Columns3 },
        { label: 'Tags', href: '/settings/tags', icon: Tag }
      ]
    },
    {
      label: 'Channels & integrations',
      items: [{ label: 'Web forms', href: '/settings/web-forms', icon: FileText }]
    }
  ];
  const groups = allGroups;
  const active = (href) => page.url.pathname === href || page.url.pathname.startsWith(`${href}/`);
  let selected = $derived(
    groups.flatMap((group) => group.items).find((item) => active(item.href))?.href || ''
  );
</script>

<aside class="preferences-sidebar">
  <div class="preferences-heading">
    <h2>Profile &amp; Preferences</h2>
    <a href={resolve('/')} aria-label="Back to CRM" title="Back to CRM"><ArrowLeft size={16} /></a>
  </div>
  <nav aria-label="Profile and preferences">
    {#each groups as group}
      <details
        open={['Personal', 'Organization & access', 'CRM configuration'].includes(group.label) ||
          group.items.some((item) => active(item.href))}
      >
        <summary>{group.label}<ChevronDown size={12} /></summary>
        {#each group.items as item}
          <a
            href={resolve(asInternalPath(item.href))}
            aria-current={active(item.href) ? 'page' : undefined}
            ><item.icon size={16} /><span class="preference-label">{item.label}</span>
          </a>
        {/each}
      </details>
    {/each}
  </nav>
  <label class="mobile-preferences"
    >Section
    <select
      value={selected}
      onchange={(event) => goto(resolve(asInternalPath(event.currentTarget.value)))}
    >
      {#if !selected}<option value="" disabled>Choose a section</option>{/if}
      {#each groups as group}<optgroup label={group.label}
          >{#each group.items as item}<option value={item.href}>{item.label}</option
            >{/each}</optgroup
        >{/each}
    </select>
  </label>
</aside>

<style>
  .preferences-sidebar {
    flex: 0 0 218px;
    min-height: 0;
    overflow-y: auto;
    padding: 23px 13px;
    border-right: 1px solid var(--v2-line);
    background: #faf9fb;
  }
  .preferences-heading {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 0 6px 22px;
  }
  h2 {
    font-size: 14px;
    line-height: 1.4;
    font-weight: 650;
    margin: 0;
    flex: 1;
  }
  .preferences-heading a {
    padding: 5px;
    color: var(--v2-slate);
    border-radius: 5px;
  }
  details + details {
    margin-top: 18px;
  }
  summary {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
    cursor: pointer;
    list-style: none;
  }
  summary::-webkit-details-marker {
    display: none;
  }
  details:not([open]) summary :global(svg) {
    transform: rotate(-90deg);
  }
  summary {
    margin: 0 8px 8px;
    font-size: 10px;
    font-weight: 600;
    color: var(--v2-slate);
    text-transform: uppercase;
    letter-spacing: 0.07em;
  }
  nav a {
    display: flex;
    align-items: center;
    gap: 9px;
    border-radius: 7px;
    padding: 10px 9px;
    font-size: 12px;
    color: var(--v2-ink);
    text-decoration: none;
    margin-bottom: 3px;
  }
  .preference-label {
    flex: 1;
    min-width: 0;
  }
  nav a :global(svg) {
    flex-shrink: 0;
  }
  nav a:hover,
  .preferences-heading a:hover {
    background: #eeebf0;
  }
  nav a[aria-current='page'] {
    background: #e9e5ed;
    font-weight: 650;
  }
  summary:focus-visible,
  a:focus-visible,
  select:focus-visible {
    outline: 2px solid #81778c;
    outline-offset: 2px;
  }
  .mobile-preferences {
    display: none;
  }
  @media (max-width: 1100px) and (min-width: 768px) {
    .preferences-sidebar {
      flex-basis: 186px;
      padding-inline: 9px;
    }
  }
  @media (max-width: 767px) {
    .preferences-sidebar {
      flex: none;
      padding: 10px 16px;
      border-right: 0;
      border-bottom: 1px solid var(--v2-line);
      overflow: visible;
    }
    .preferences-heading {
      padding: 0 0 8px;
    }
    nav {
      display: none;
    }
    .mobile-preferences {
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 12px;
    }
    select {
      flex: 1;
      min-width: 0;
      padding: 8px;
      border: 1px solid var(--v2-line);
      border-radius: 6px;
      background: white;
      color: var(--v2-ink);
      font: inherit;
    }
  }
</style>
