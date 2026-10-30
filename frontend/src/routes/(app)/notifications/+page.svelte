<script>
  import Notice from '$lib/components/Notice.svelte';
  import { useI18n } from '$lib/i18n/context.js';
  const { ui, locale, relativeTime } = useI18n();

  import { resolve } from '$app/paths';
  import { goto } from '$app/navigation';
  import { enhance, deserialize } from '$app/forms';
  import { page } from '$app/state';
  import { reminderLabel, reminderDetail } from '$lib/v2/notification-content.js';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import SearchableSelect from '$lib/components/SearchableSelect.svelte';
  import NotificationPreferences from '$lib/v2/components/NotificationPreferences.svelte';

  import { Bell, Check, ChevronLeft, ChevronRight } from '@lucide/svelte';

  /** @type {{data:any, form:any}} */
  let { data, form } = $props();
  let preferencesOpen = $derived(page.url.searchParams.get('tab') === 'preferences');
  let busy = $state(false);
  let historyStatus = $derived(data.pagination.status);
  const submit = () => {
    busy = true;
    return async ({ update }) => {
      try {
        await update({ reset: false });
      } finally {
        busy = false;
      }
    };
  };
  /** @returns {`/notifications?${string}`} */
  function historyLink(status = data.pagination.status, number = 1) {
    return `/notifications?${new URLSearchParams({ status, page: String(number) })}`;
  }
  let error = $state('');
  async function openNotification(event, n) {
    if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || n.read_at) return;
    event.preventDefault();
    if (busy) return;
    busy = true;
    error = '';
    try {
      const body = new FormData();
      body.set('id', n.id);
      const response = await fetch('?/read', { method: 'POST', body });
      const result = deserialize(await response.text());
      if (result.type !== 'success') throw new Error();
      await goto(resolve(n.resolved_link));
    } catch {
      error = 'Could not open this notification. Please try again.';
    } finally {
      busy = false;
    }
  }
  function phrase(verb) {
    return (
      {
        'webform.submitted': 'received a website submission through',
        'case.mentioned': 'mentioned you on',
        'case.commented': 'commented on',
        'support.replied': 'replied to',
        'support.status_changed': 'updated'
      }[verb] || 'updated'
    );
  }
</script>

<PageHeader title={ui('Notifications')} compact>
  {#snippet actions()}
    {#if !preferencesOpen}
      <form method="POST" action="?/readAll" use:enhance={submit}>
        <button class="v2-btn v2-btn-sm" disabled={busy || !data.totals.unread}
          ><Check size={15} />{ui('Mark all read')}</button
        >
      </form>
    {/if}
  {/snippet}
</PageHeader>
<nav class="tabs crm-preferences-tabs" aria-label={ui('Notification sections')}>
  <a
    href={resolve('/notifications')}
    class:active={!preferencesOpen}
    aria-current={!preferencesOpen ? 'page' : undefined}>{ui('History')}</a
  >
  <a
    href={resolve('/notifications?tab=preferences')}
    class:active={preferencesOpen}
    aria-current={preferencesOpen ? 'page' : undefined}>{ui('Preferences')}</a
  >
</nav>
<div class="v2-scroll">
  <div class="content crm-preferences-body crm-settings-content">
    {#if preferencesOpen}
      <NotificationPreferences settings={data.preferences} />
    {:else}
      {#if error}<Notice message={ui(error)} />{/if}
      {#if form?.error}<Notice message={ui(form.error)} />{/if}
      <div class="history-surface crm-settings-surface">
        <div class="history-table-wrap">
          <table class="crm-settings-table history-table">
            <caption class="sr-only">{ui('Notification history')}</caption>
            <thead
              ><tr>
                <th scope="col">
                  <div class="notification-heading crm-control-toolbar">
                    <span>{ui('Notification')}</span>
                    <div class="status-filter">
                      <SearchableSelect
                        label={ui('Notification status')}
                        bind:value={historyStatus}
                        options={[
                          { value: 'all', label: ui('All') },
                          { value: 'unread', label: ui('Unread') },
                          { value: 'read', label: ui('Read') }
                        ]}
                        onchange={(value) => goto(resolve(historyLink(value)), { noScroll: true })}
                      />
                    </div>
                  </div>
                </th>
                <th scope="col" class="status-column">{ui('Status')}</th>
                <th scope="col" class="date-column">{ui('Date')}</th>
                <th scope="col" class="actions-column"
                  ><span class="sr-only">{ui('Actions')}</span></th
                >
              </tr></thead
            >
            <tbody>
              {#each data.results as n (n.id)}
                <tr class:unread={!n.read_at}>
                  <td class="message">
                    <p>
                      {#if reminderLabel(n)}<strong>{ui(reminderLabel(n))}:</strong>{:else}<strong
                          >{n.actor_name || ui('The system')}</strong
                        >
                        {ui(phrase(n.verb))}{/if}
                      {#if n.resolved_link}<a
                          href={resolve(n.resolved_link)}
                          onclick={(event) => openNotification(event, n)}
                          >{n.entity_name || ui('Record')}</a
                        >
                      {:else}{n.entity_name || ui('Record')}{/if}
                    </p>
                    {#if reminderDetail(n, locale())}<p class="excerpt">
                        {reminderDetail(n, locale())}
                      </p>{/if}
                    {#if n.data?.comment_excerpt}<p class="excerpt">
                        {n.data.comment_excerpt}
                      </p>{/if}
                  </td>
                  <td
                    ><span class="read-status" class:is-unread={!n.read_at}>
                      <span class="status-dot" aria-hidden="true"></span>{n.read_at
                        ? ui('Read')
                        : ui('Unread')}
                    </span></td
                  >
                  <td
                    ><time
                      datetime={n.created_at}
                      title={new Date(n.created_at).toLocaleString(locale())}
                    >
                      {relativeTime(n.created_at)}
                    </time></td
                  >
                  <td class="row-actions">
                    {#if !n.read_at}<form method="POST" action="?/read" use:enhance={submit}>
                        <input type="hidden" name="id" value={n.id} />
                        <button
                          class="v2-btn v2-btn-sm read-button"
                          disabled={busy}
                          aria-label={ui('Mark notification read')}
                          title={ui('Mark read')}><Check size={16} /></button
                        >
                      </form>{/if}
                  </td>
                </tr>
              {:else}<tr
                  ><td colspan="4"
                    ><div class="empty">
                      <Bell size={26} /><strong
                        >{data.pagination.status === 'unread'
                          ? ui('You’re all caught up')
                          : ui('No notifications here')}</strong
                      >
                    </div></td
                  ></tr
                >{/each}
            </tbody>
          </table>
        </div>
        <nav class="history-pagination" aria-label={ui('Notification pages')}>
          <span class="page-summary" aria-live="polite">
            {ui('Showing')}
            {data.results.length ? (data.pagination.page - 1) * data.pagination.size + 1 : 0}–{data
              .results.length
              ? (data.pagination.page - 1) * data.pagination.size + data.results.length
              : 0}
            {ui('of')}
            {data.totals.count}
          </span>
          <div class="page-controls">
            {#if data.pagination.page > 1}<a
                class="v2-btn v2-btn-sm"
                href={resolve(historyLink(data.pagination.status, data.pagination.page - 1))}
                ><ChevronLeft size={14} />{ui('Previous')}</a
              >
            {:else}<button class="v2-btn v2-btn-sm" disabled
                ><ChevronLeft size={14} />{ui('Previous')}</button
              >{/if}
            <span>{ui('Page')} {data.pagination.page} {ui('of')} {data.pagination.pages}</span>
            {#if data.pagination.page < data.pagination.pages}<a
                class="v2-btn v2-btn-sm"
                href={resolve(historyLink(data.pagination.status, data.pagination.page + 1))}
                >{ui('Next')}<ChevronRight size={14} /></a
              >
            {:else}<button class="v2-btn v2-btn-sm" disabled
                >{ui('Next')}<ChevronRight size={14} /></button
              >{/if}
          </div>
        </nav>
      </div>
    {/if}
  </div>
</div>

<style>
  .tabs {
    display: flex;
    gap: 26px;
    padding: 0 var(--crm-space-6);
    border-bottom: 1px solid var(--v2-line);
  }
  .tabs a {
    padding: 14px 0;
    color: var(--v2-slate);
    text-decoration: none;
    border-bottom: 2px solid transparent;
    font-size: var(--crm-text-sm);
  }
  .tabs a.active {
    color: var(--v2-ink);
    border-color: var(--v2-ink);
    font-weight: 600;
  }
  .content {
    padding: var(--crm-space-6);
    max-width: 1040px;
  }
  .history-surface {
    overflow: hidden;
  }
  .notification-heading {
    display: flex;
    align-items: center;
    gap: var(--crm-space-3);
  }
  .status-filter {
    width: 120px;
    flex: none;
  }
  .history-table-wrap {
    overflow-x: auto;
  }
  .history-table {
    table-layout: fixed;
  }
  .status-column {
    width: 110px;
  }
  .date-column {
    width: 160px;
  }
  .actions-column {
    width: 64px;
  }
  .message p {
    margin: 0;
    line-height: 1.6;
    overflow-wrap: anywhere;
  }
  .message strong {
    font-weight: 500;
  }
  .unread .message strong {
    font-weight: 600;
  }
  .message a {
    color: var(--crm-link);
    text-underline-offset: 3px;
  }
  .message .excerpt {
    color: var(--v2-slate);
    font-size: var(--crm-text-xs);
    margin-top: var(--crm-space-1);
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .read-status {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    color: var(--v2-slate);
    font-size: var(--crm-text-xs);
    white-space: nowrap;
  }
  .status-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--crm-border);
  }
  .is-unread .status-dot {
    background: var(--crm-primary);
  }
  time {
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
  }
  .read-button {
    width: 30px;
    height: 30px;
    padding: 0;
  }
  .history-pagination,
  .page-controls {
    display: flex;
    align-items: center;
    gap: var(--crm-space-2);
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
  }
  .history-pagination {
    padding: var(--crm-space-3) var(--crm-space-4);
    border-top: 1px solid var(--v2-line-soft);
  }
  .page-summary {
    margin-right: auto;
  }
  .empty {
    display: flex;
    flex-direction: column;
    gap: var(--crm-space-3);
    align-items: center;
    text-align: center;
    padding: 48px var(--crm-space-4);
    color: var(--v2-slate);
  }
  .empty strong {
    font-size: var(--crm-text-sm);
    font-weight: 500;
  }
</style>
