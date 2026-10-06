<script>
  import { useI18n } from '$lib/i18n/context.js';
  const { ui, locale, relativeTime } = useI18n();

  import { onMount } from 'svelte';
  import { afterNavigate, goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { asInternalPath } from '$lib/utils/paths.js';
  import { Bell, X, Check } from '@lucide/svelte';
  import { resolvedLink, reminderLabel, reminderDetail } from '$lib/v2/notification-content.js';
  import { announceReminders } from '$lib/v2/reminder-alerts.js';

  let { collapsed = false } = $props();
  const id = $props.id();
  let rows = $state(/** @type {any[]} */ ([]));
  let unread = $state(0),
    loading = $state(false),
    writing = $state(false);
  let failure = $state(''),
    open = $state(false);
  let panel = $state(/** @type {HTMLDivElement | undefined} */ (undefined));
  let left = $state(8),
    top = $state(70);
  let controller;
  let alive = false;
  let generation = 0;

  async function refresh() {
    if (!alive) return;
    const version = ++generation;
    controller?.abort();
    controller = new AbortController();
    loading = true;
    try {
      const response = await fetch(resolve('/api/notifications') + '/?limit=20', {
        signal: controller.signal,
        cache: 'no-store'
      });
      if (!response.ok) throw new Error();
      const data = await response.json();
      if (!alive || version !== generation) return;
      rows = data.results || [];
      announceReminders(rows, Date.now(), ui, locale());
      unread = data.unread_count || 0;
      failure = '';
    } catch (error) {
      if (alive && version === generation && error.name !== 'AbortError')
        failure = 'Could not load notifications.';
    } finally {
      if (alive && version === generation) loading = false;
    }
  }
  onMount(() => {
    alive = true;
    void refresh();
    const timer = setInterval(() => {
      if (document.visibilityState === 'visible' && !writing && !loading) void refresh();
    }, 45000);
    const resume = () => {
      if (document.visibilityState === 'visible' && !writing) void refresh();
    };
    document.addEventListener('visibilitychange', resume);
    window.addEventListener('focus', resume);
    return () => {
      alive = false;
      generation++;
      controller?.abort();
      clearInterval(timer);
      document.removeEventListener('visibilitychange', resume);
      window.removeEventListener('focus', resume);
    };
  });
  afterNavigate((navigation) => {
    panel?.hidePopover();
    if (alive && navigation.from) void refresh();
  });
  function show(event) {
    const rect = event.currentTarget.getBoundingClientRect();
    left = Math.max(8, Math.min(rect.left, window.innerWidth - 388));
    top = Math.max(8, Math.min(rect.bottom + 8, window.innerHeight - 160));
    void refresh();
  }
  function destination(row) {
    return resolvedLink(row.link);
  }

  function description(row) {
    if (reminderLabel(row)) return ui(reminderLabel(row));
    const actor = row.actor?.user_details?.name || row.actor?.user_details?.email || ui('Someone');
    if (row.verb === 'webform.submitted') return ui('New website submission');
    if (row.verb === 'case.mentioned') return ui('{actor} mentioned you', { actor });
    if (row.verb === 'case.commented') return ui('{actor} added a comment', { actor });
    return (
      actor +
      ' · ' +
      String(row.verb || 'Update')
        .replace(/^[^.]+\./, '')
        .replaceAll('_', ' ')
    );
  }
  async function mark(row = null) {
    if (writing) return false;
    writing = true;
    generation++;
    controller?.abort();
    loading = false;
    try {
      const url = row
        ? resolve('/api/notifications/[id]/read', { id: row.id })
        : resolve('/api/notifications/read-all');
      const response = await fetch(url + '/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: '{}'
      });
      if (!response.ok) throw new Error();
      if (!alive) return false;
      await refresh();
      return true;
    } catch {
      failure = 'Could not mark notifications as read. Try again.';
      return false;
    } finally {
      writing = false;
    }
  }
  async function openRow(row) {
    if (!row.read_at && !(await mark(row))) return;
    const link = destination(row);
    if (link) {
      panel?.hidePopover();
      await goto(resolve(asInternalPath(link)));
    }
  }
</script>

<svelte:window onresize={() => panel?.hidePopover()} />
<button
  class="bell-trigger"
  class:collapsed
  type="button"
  popovertarget={id}
  aria-label={unread ? `Notifications, ${unread} unread` : ui('Notifications')}
  aria-expanded={open}
  title={ui('Notifications')}
  onclick={show}
>
  <span class="bell-icon"
    ><Bell size={19} />{#if collapsed && unread}<span class="dot"></span>{/if}</span
  >
  {#if !collapsed}<span>{ui('Notifications')}</span>{#if unread}<b>{unread > 99 ? '99+' : unread}</b
      >{/if}{/if}
</button>
<div
  {id}
  bind:this={panel}
  popover="auto"
  role="dialog"
  aria-label={ui('Notifications')}
  class="notification-panel"
  style:left={`${left}px`}
  style:top={`${top}px`}
  style:max-height={`calc(100dvh - ${top + 8}px)`}
  ontoggle={(event) => (open = event.newState === 'open')}
>
  <header>
    <h2>
      {ui('Notifications')}
      {#if unread}<span>{unread}</span>{/if}
    </h2>
    <button
      type="button"
      aria-label={ui('Close notifications')}
      onclick={() => panel?.hidePopover()}><X size={17} /></button
    >
  </header>
  {#if unread}<div class="read-actions">
      <button type="button" disabled={writing} onclick={() => mark()}
        ><Check size={13} />{ui('Mark all read')}</button
      >
    </div>{/if}
  <div class="feed" aria-busy={loading}>
    {#if failure}<p role="alert" class="error">
        {ui(failure)}<button type="button" onclick={() => refresh()}>{ui('Retry')}</button>
      </p>{/if}
    {#if loading && !rows.length}<p class="empty" role="status">{ui('Loading notifications…')}</p>
    {:else if !rows.length && !failure}<div class="empty">
        <Bell size={25} /><strong>{ui("You're all caught up")}</strong><span
          >{ui('New notifications will appear here.')}</span
        >
      </div>
    {:else}
      {#each rows as row (row.id)}
        <button
          class="notification-row"
          class:unread={!row.read_at}
          disabled={writing}
          onclick={() => openRow(row)}
        >
          <span class="read-dot" aria-label={row.read_at ? ui('Read') : ui('Unread')}></span>
          <span class="row-body"
            ><strong>{description(row)}</strong>{#if row.entity_name}<span>{row.entity_name}</span
              >{/if}{#if reminderDetail(row, locale())}<p>
                {reminderDetail(row, locale())}
              </p>{/if}{#if row.data?.comment_excerpt}<p>{row.data.comment_excerpt}</p>{/if}<small
              >{relativeTime(row.created_at)}</small
            ></span
          >
        </button>
      {/each}
    {/if}
  </div>
  <footer>
    <a href={resolve('/notifications')} onclick={() => panel?.hidePopover()}>{ui('View history')}</a
    >
  </footer>
</div>

<style>
  .bell-trigger {
    display: flex;
    align-items: center;
    gap: 11px;
    width: 100%;
    background: transparent;
    color: inherit;
    border: 0;
    padding: 10px var(--crm-space-3);
    border-radius: var(--crm-radius-md);
    cursor: pointer;
    font: inherit;
    font-size: var(--crm-text-sm);
    text-align: left;
  }
  .bell-trigger:hover {
    background: var(--crm-nav-hover);
  }
  .bell-trigger b {
    margin-left: auto;
    border-radius: var(--crm-radius-sm);
    background: var(--crm-surface-secondary);
    color: var(--crm-text);
    padding: 2px 6px;
    font-size: var(--crm-text-xs);
  }
  .bell-icon {
    position: relative;
    display: flex;
    flex: none;
  }
  .collapsed {
    justify-content: center;
    padding: 10px 0;
  }
  .dot {
    position: absolute;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--crm-primary);
    right: -2px;
    top: -2px;
  }
  .notification-panel {
    position: fixed;
    inset: auto;
    margin: 0;
    width: min(380px, calc(100vw - 16px));
    max-height: calc(100dvh - 100px);
    padding: 0;
    border: 1px solid var(--v2-line);
    border-radius: var(--crm-radius-lg);
    background: var(--v2-bg, var(--crm-surface));
    color: var(--v2-ink);
    box-shadow: var(--crm-shadow-lg);
    overflow: auto;
  }
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--crm-space-4);
    border-bottom: 1px solid var(--v2-line-soft);
  }
  h2 {
    display: flex;
    gap: var(--crm-space-2);
    align-items: center;
    font-size: var(--crm-text-sm);
    margin: 0;
  }
  h2 span {
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
  }
  header button,
  .read-actions button,
  .error button {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    border: 0;
    background: none;
    color: var(--v2-slate);
    cursor: pointer;
    font: inherit;
    font-size: var(--crm-text-xs);
  }
  .read-actions {
    padding: 10px var(--crm-space-4);
    text-align: right;
  }
  .feed {
    max-height: min(450px, 55dvh);
    overflow-y: auto;
  }
  .notification-row {
    display: flex;
    gap: 10px;
    width: 100%;
    text-align: left;
    background: transparent;
    border: 0;
    border-bottom: 1px solid var(--v2-line-soft);
    padding: 14px var(--crm-space-4);
    font: inherit;
    color: inherit;
    cursor: pointer;
  }
  .notification-row:hover {
    background: var(--v2-line-soft);
  }
  .notification-row.unread {
    background: color-mix(in srgb, var(--v2-line-soft) 60%, transparent);
  }
  .read-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    margin-top: 6px;
    flex: none;
  }
  .unread .read-dot {
    background: var(--v2-ink);
  }
  .row-body {
    display: grid;
    gap: 5px;
    min-width: 0;
    font-size: var(--crm-text-xs);
    overflow-wrap: anywhere;
  }
  .row-body strong {
    font-weight: 550;
    line-height: 1.5;
  }
  .row-body p {
    margin: 0;
    color: var(--v2-slate);
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .row-body small {
    color: var(--v2-slate);
    font-size: var(--crm-text-xs);
  }
  .empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
    padding: var(--crm-space-8) 18px;
    color: var(--v2-slate);
    font-size: var(--crm-text-xs);
  }
  .empty strong {
    color: var(--v2-ink);
    font-weight: 500;
  }
  .error {
    padding: var(--crm-space-3) var(--crm-space-4);
    color: var(--v2-rust);
    font-size: var(--crm-text-xs);
  }
  footer {
    padding: var(--crm-space-3) var(--crm-space-4);
    border-top: 1px solid var(--v2-line-soft);
    text-align: center;
  }
  footer a {
    color: var(--v2-ink);
    font-size: var(--crm-text-xs);
    text-decoration: none;
  }
</style>
