<script>
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();

  import { page } from '$app/state';
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { asInternalPath } from '$lib/utils/paths.js';
  import Pill from './Pill.svelte';
  import { settingsGroups } from '$lib/v2/settings-access.js';
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

  const icons = {
    profile: CircleUser,
    notifications: Bell,
    organization: Building2,
    team: Users,
    roles: ShieldCheck,
    properties: ListFilter,
    creation_forms: FileText,
    pipelines: Columns3,
    tags: Tag,
    forms: FileText
  };
  let groups = $derived(
    settingsGroups(page.data.permissions).map((group) => ({
      ...group,
      items: group.items.map((item) => ({ ...item, icon: icons[item.key] }))
    }))
  );
  const active = (href) => page.url.pathname === href || page.url.pathname.startsWith(`${href}/`);
  let selected = $derived(
    groups.flatMap((group) => group.items).find((item) => active(item.href))?.href || ''
  );
</script>

<aside class="preferences-sidebar">
  <div class="preferences-heading">
    <h2>{ui('Profile & Preferences')}</h2>
    <a href={resolve('/')} aria-label={ui('Back to CRM')} title={ui('Back to CRM')}
      ><ArrowLeft size={16} /></a
    >
  </div>
  <nav aria-label={ui('Profile and preferences')}>
    {#each groups as group (group.label)}
      <details
        open={['Personal', 'Organization & access', 'CRM configuration'].includes(group.label) ||
          group.items.some((item) => active(item.href))}
      >
        <summary>{ui(group.label)}<ChevronDown size={12} /></summary>
        {#each group.items as item (item.key)}
          <a
            href={resolve(asInternalPath(item.href))}
            aria-current={active(item.href) ? 'page' : undefined}
            ><item.icon size={16} /><span class="preference-label">{ui(item.label)}</span>
            {#if item.access === 'read'}<Pill>{ui('Read only')}</Pill>{/if}
            {#if item.beta}<Pill>Beta</Pill>{/if}
          </a>
        {/each}
      </details>
    {/each}
  </nav>
  <label class="mobile-preferences"
    >{ui('Section')}
    <select
      class="v2-input"
      value={selected}
      onchange={(event) => goto(resolve(asInternalPath(event.currentTarget.value)))}
    >
      {#if !selected}<option value="" disabled>{ui('Choose a section')}</option>{/if}
      {#each groups as group (group.label)}<optgroup label={ui(group.label)}
          >{#each group.items as item (item.key)}<option value={item.href}
              >{ui(item.label)}{item.access === 'read' ? ` · ${ui('Read only')}` : ''}{item.beta
                ? ' · Beta'
                : ''}</option
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
    background: var(--crm-canvas);
  }
  .preferences-heading {
    display: flex;
    align-items: center;
    gap: var(--crm-space-2);
    padding: 0 6px var(--crm-space-6);
  }
  h2 {
    font-size: var(--crm-text-sm);
    line-height: 1.4;
    font-weight: 650;
    margin: 0;
    flex: 1;
  }
  .preferences-heading a {
    padding: 5px;
    color: var(--v2-slate);
    border-radius: var(--crm-radius-sm);
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
    margin: 0 var(--crm-space-2) var(--crm-space-2);
    font-size: var(--crm-text-xs);
    font-weight: 600;
    color: var(--v2-slate);
    text-transform: uppercase;
    letter-spacing: 0.07em;
  }
  nav a {
    display: flex;
    align-items: center;
    gap: 9px;
    border-radius: var(--crm-radius-md);
    padding: 10px 9px;
    font-size: var(--crm-text-xs);
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
    background: var(--crm-surface-secondary);
  }
  nav a[aria-current='page'] {
    background: var(--crm-action-bg);
    color: var(--crm-primary-text);
    font-weight: 650;
  }
  nav a[aria-current='page']:hover {
    background: var(--crm-action-hover-bg);
  }
  nav a[aria-current='page']:active {
    background: var(--crm-action-active-bg);
  }
  summary:focus-visible,
  a:focus-visible,
  select:focus-visible {
    outline: 2px solid var(--crm-focus);
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
      padding: 10px var(--crm-space-4);
      border-right: 0;
      border-bottom: 1px solid var(--v2-line);
      overflow: visible;
    }
    .preferences-heading {
      padding: 0 0 var(--crm-space-2);
    }
    nav {
      display: none;
    }
    .mobile-preferences {
      display: flex;
      align-items: center;
      gap: var(--crm-space-3);
      font-size: var(--crm-text-xs);
    }
    select {
      flex: 1;
      min-width: 0;
      padding: var(--crm-space-2);
      border: 1px solid var(--v2-line);
      border-radius: var(--crm-radius-sm);
      background: var(--crm-surface);
      color: var(--v2-ink);
      font: inherit;
    }
  }
</style>
