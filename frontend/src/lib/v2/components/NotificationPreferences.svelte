<script>
  import { onMount } from 'svelte';
  import { deserialize } from '$app/forms';
  import { useI18n } from '$lib/i18n/context.js';
  import Notice from '$lib/components/Notice.svelte';
  import SearchableSelect from '$lib/components/SearchableSelect.svelte';
  import { Bell, Mail, PanelsTopLeft, PanelTop, Search, ChevronRight } from '@lucide/svelte';

  let { settings } = $props();
  const { ui } = useI18n();
  const channels = [
    { key: 'popup', label: 'Pop-up', icon: PanelTop, hint: 'Alerts inside the CRM.' },
    {
      key: 'browser',
      label: 'Browser',
      icon: PanelsTopLeft,
      hint: 'Desktop alerts while the CRM is open.'
    },
    { key: 'bell', label: 'Bell', icon: Bell, hint: 'Notifications in the bell and history.' },
    { key: 'email', label: 'Email', icon: Mail, hint: 'Notifications sent to your account email.' }
  ];
  let values = $derived(structuredClone(settings?.values || {}));
  let query = $state('');
  let status = $state('all');
  let expanded = $state([]);
  let busy = $state(false);
  let message = $state('');
  let error = $state('');
  let browserAttempted = $state(false);
  let permission = $state('unsupported');
  const topics = $derived(settings?.topics || []);
  const browserSelected = $derived(Object.values(values).some((channels) => channels.browser));
  const visible = $derived(
    topics.filter((topic) => {
      const enabled = Object.values(values[topic.key] || {}).some(Boolean);
      return (
        `${ui(topic.group)} ${ui(topic.label)} ${ui(topic.description)}`
          .toLowerCase()
          .includes(query.trim().toLowerCase()) &&
        (status === 'all' || (status === 'enabled' ? enabled : !enabled))
      );
    })
  );
  const groups = $derived([...new Set(visible.map((topic) => topic.group))]);
  function selection(items, channel) {
    const count = items.filter((topic) => values[topic.key]?.[channel]).length;
    return {
      checked: !!items.length && count === items.length,
      mixed: count > 0 && count < items.length
    };
  }
  async function change(items, channel, checked) {
    if (busy) return;
    const previous = values;
    values = {
      ...values,
      ...Object.fromEntries(
        items.map((topic) => [topic.key, { ...values[topic.key], [channel]: checked }])
      )
    };
    busy = true;
    message = 'Saving…';
    error = '';
    try {
      if (channel === 'browser' && checked) {
        browserAttempted = true;
        refreshPermission();
        // The checkbox is the explicit user gesture; never prompt on page load.
        if (permission === 'default') permission = await Notification.requestPermission();
        if (permission !== 'granted') {
          values = previous;
          message = '';
          return;
        }
      }
      const body = new FormData();
      body.set('notification_preferences', JSON.stringify(values));
      const response = await fetch('?/preferences', {
        method: 'POST',
        body,
        headers: { 'x-sveltekit-action': 'true' },
        keepalive: true
      });
      const result = deserialize(await response.text());
      if (result.type !== 'success') throw new Error('Save failed');
      message = 'Saved';
      window.dispatchEvent(new Event('crm-notification-preferences'));
    } catch {
      values = previous;
      message = '';
      error =
        'Could not confirm the save. Previous selections are shown; reload to check and try again.';
    } finally {
      busy = false;
    }
  }
  function toggle(group) {
    expanded = expanded.includes(group)
      ? expanded.filter((item) => item !== group)
      : [...expanded, group];
  }
  function refreshPermission() {
    permission =
      window.isSecureContext && 'Notification' in window ? Notification.permission : 'unsupported';
  }
  onMount(() => {
    refreshPermission();
    window.addEventListener('focus', refreshPermission);
    return () => window.removeEventListener('focus', refreshPermission);
  });
</script>

<div class="notification-settings" aria-busy={busy}>
  <div class="crm-settings-surface matrix">
    <div class="toolbar crm-control-toolbar">
      <label class="crm-search"
        ><Search size={17} /><input
          type="search"
          bind:value={query}
          aria-label={ui('Search notification topics')}
          placeholder={ui('Search topics…')}
        /></label
      >
      <div class="status-filter">
        <SearchableSelect
          label={ui('Notification status')}
          bind:value={status}
          options={[
            { value: 'all', label: ui('All topics') },
            { value: 'enabled', label: ui('Enabled topics') },
            { value: 'disabled', label: ui('Disabled topics') }
          ]}
        />
      </div>
      <button
        class="v2-btn"
        type="button"
        onclick={() =>
          (expanded = expanded.length ? [] : [...new Set(topics.map((topic) => topic.group))])}
        >{expanded.length ? ui('Collapse all') : ui('Expand all')}</button
      >
    </div>
    <table>
      <caption class="sr-only">{ui('Notification channels by topic')}</caption>
      <thead
        ><tr
          ><th scope="col">{ui('Notification topics')}</th>
          {#each channels as channel (channel.key)}<th scope="col"
              ><span class="channel-title" title={ui(channel.hint)}
                ><channel.icon size={18} />{ui(channel.label)}</span
              >
              <input
                type="checkbox"
                aria-label={ui('Toggle {channel} for all topics', { channel: ui(channel.label) })}
                checked={selection(topics, channel.key).checked}
                indeterminate={selection(topics, channel.key).mixed}
                disabled={busy}
                onchange={(event) => change(topics, channel.key, event.currentTarget.checked)}
              />
            </th>{/each}
        </tr></thead
      >
      <tbody>
        {#each groups as group (group)}
          {@const items = topics.filter((topic) => topic.group === group)}
          {@const open = !!query || expanded.includes(group)}
          <tr class="topic-group"
            ><th scope="row"
              ><button
                type="button"
                class="group-toggle"
                aria-expanded={open}
                onclick={() => toggle(group)}
                ><ChevronRight size={16} class={open ? 'expanded' : ''} />{ui(group)}</button
              ></th
            >
            {#each channels as channel (channel.key)}<td
                ><input
                  type="checkbox"
                  aria-label={`${ui(group)} · ${ui(channel.label)}`}
                  checked={selection(items, channel.key).checked}
                  indeterminate={selection(items, channel.key).mixed}
                  disabled={busy}
                  onchange={(event) => change(items, channel.key, event.currentTarget.checked)}
                /></td
              >{/each}
          </tr>
          {#if open}
            {#each visible.filter((topic) => topic.group === group) as topic (topic.key)}<tr
                class="topic-detail"
                ><th scope="row"
                  ><strong>{ui(topic.label)}</strong><small>{ui(topic.description)}</small></th
                >
                {#each channels as channel (channel.key)}<td
                    ><input
                      type="checkbox"
                      aria-label={`${ui(topic.label)} · ${ui(channel.label)}`}
                      checked={!!values[topic.key]?.[channel.key]}
                      disabled={busy}
                      onchange={(event) =>
                        change([topic], channel.key, event.currentTarget.checked)}
                    /></td
                  >{/each}
              </tr>{/each}
          {/if}
        {/each}
        {#if !groups.length}<tr
            ><td colspan="5" class="no-results">{ui('No matching topics.')}</td></tr
          >{/if}
      </tbody>
    </table>
    {#if browserSelected || browserAttempted}
      <div class="browser-status" role="status">
        <PanelsTopLeft size={17} /><span>
          {#if permission === 'denied'}{ui(
              'Browser alerts are blocked. Allow notifications in your browser’s site settings.'
            )}
          {:else if permission === 'unsupported'}{ui(
              'Browser alerts are not available in this browser.'
            )}
          {:else if permission === 'default'}{ui(
              'Select a Browser checkbox and allow notifications to enable desktop alerts.'
            )}
          {:else}{ui('Browser alerts enabled on this device.')}{/if}
        </span>
      </div>
    {/if}
  </div>
  <div class="save-status" role="status" aria-live="polite">{ui(message)}</div>
  {#if error}<Notice tone="error" message={ui(error)} />{/if}
</div>

<style>
  .notification-settings {
    display: grid;
    gap: 12px;
  }
  .matrix {
    overflow: hidden;
  }
  .toolbar {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 16px;
  }
  .status-filter {
    flex: 0 0 190px;
  }
  .toolbar > button {
    flex: none;
    white-space: nowrap;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: var(--crm-text-sm);
    table-layout: fixed;
  }
  th,
  td {
    padding: 13px 10px;
    border-top: 1px solid var(--crm-border-soft);
  }
  th:first-child {
    width: auto;
    text-align: left;
    padding-left: 20px;
  }
  th:not(:first-child),
  td:not(:first-child) {
    width: 94px;
    text-align: center;
  }
  thead {
    background: var(--crm-surface-secondary);
  }
  thead th {
    font-weight: 550;
  }
  .channel-title {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 5px;
    margin-bottom: 9px;
  }
  input[type='checkbox'] {
    width: 17px;
    height: 17px;
    accent-color: var(--crm-primary);
    cursor: pointer;
    vertical-align: middle;
  }
  input[type='checkbox']:disabled {
    cursor: wait;
  }
  input:focus-visible,
  button:focus-visible {
    outline: 2px solid var(--crm-focus);
    outline-offset: 3px;
  }
  .group-toggle {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 4px 0;
    border: 0;
    background: none;
    color: inherit;
    font: inherit;
    font-weight: 600;
    cursor: pointer;
  }
  .group-toggle :global(.expanded) {
    transform: rotate(90deg);
  }
  .topic-detail {
    background: var(--crm-surface-subtle);
  }
  .topic-detail th:first-child {
    padding-left: 46px;
  }
  .topic-detail strong {
    font-weight: 500;
  }
  small {
    display: block;
    color: var(--crm-text-muted);
    font-weight: 400;
    font-size: var(--crm-text-xs);
    line-height: 1.5;
    margin-top: 4px;
  }
  .browser-status {
    display: flex;
    gap: 10px;
    align-items: center;
    padding: 16px 20px;
    border-top: 1px solid var(--crm-border-soft);
    color: var(--crm-text-muted);
    font-size: var(--crm-text-xs);
  }
  .browser-status span {
    flex: 1;
  }
  .save-status {
    font-size: var(--crm-text-xs);
    text-align: right;
    color: var(--crm-success);
  }
  .save-status:empty {
    display: none;
  }
  .no-results {
    text-align: center;
    padding: 28px;
    color: var(--crm-text-muted);
  }
</style>
