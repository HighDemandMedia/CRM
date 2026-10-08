<script>
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();
  /** @type {{notes: import('svelte').Snippet, activity: import('svelte').Snippet, emails?:import('svelte').Snippet, active?:string}} */
  let { notes, activity, emails, active = $bindable('activity') } = $props();
  const id = $props.id();
  let buttons = $state([]);
  const tabs = $derived([
    { key: 'activity', label: 'Activity', content: activity },
    { key: 'notes', label: 'Notes', content: notes },
    ...(emails ? [{ key: 'emails', label: 'Emails', content: emails }] : [])
  ]);
  function navigate(event) {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const current = tabs.findIndex((tab) => tab.key === active);
    const next =
      event.key === 'Home'
        ? 0
        : event.key === 'End'
          ? tabs.length - 1
          : (current + (event.key === 'ArrowLeft' ? -1 : 1) + tabs.length) % tabs.length;
    active = tabs[next].key;
    buttons[next]?.focus();
  }
</script>

<div class="record-tabs">
  <div
    class="tabs"
    role="tablist"
    tabindex="-1"
    aria-label={ui('Record activity')}
    onkeydown={navigate}
  >
    {#each tabs as tab, index (tab.key)}
      <button
        type="button"
        bind:this={buttons[index]}
        role="tab"
        id={`${id}-${tab.key}-tab`}
        aria-controls={`${id}-${tab.key}`}
        aria-selected={active === tab.key}
        tabindex={active === tab.key ? 0 : -1}
        onclick={() => (active = tab.key)}>{ui(tab.label)}</button
      >
    {/each}
  </div>
  {#each tabs as tab (tab.key)}
    <div
      class="panel"
      role="tabpanel"
      id={`${id}-${tab.key}`}
      aria-labelledby={`${id}-${tab.key}-tab`}
      hidden={active !== tab.key}
      tabindex="0"
    >
      {#if tab.key !== 'emails' || active === 'emails'}{@render tab.content()}{/if}
    </div>
  {/each}
</div>

<style>
  .tabs {
    display: flex;
    gap: var(--crm-space-5);
    overflow-x: auto;
    border-bottom: 1px solid var(--v2-line);
    margin-bottom: var(--crm-space-6);
  }
  .tabs button {
    background: none;
    border: 0;
    border-bottom: 3px solid transparent;
    padding: 0 0 var(--crm-space-3);
    min-height: 2.75rem;
    color: var(--v2-slate);
    font: inherit;
    cursor: pointer;
  }
  .tabs button[aria-selected='true'] {
    color: var(--v2-ink);
    border-bottom-color: var(--v2-ink);
    font-weight: 650;
  }
  .panel:focus-visible,
  button:focus-visible {
    outline: 2px solid var(--v2-ink);
    outline-offset: 3px;
  }
</style>
