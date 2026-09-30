<script>
  import { resolve } from '$app/paths';
  import { goto } from '$app/navigation';
  import { enhance, deserialize } from '$app/forms';
  import { page } from '$app/state';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import { relativeTime } from '$lib/v2/format.js';
  import { Bell, Check, ChevronLeft, ChevronRight } from '@lucide/svelte';

  /** @type {{data:any, form:any}} */
  let { data, form } = $props();
  let preferencesOpen = $derived(page.url.searchParams.get('tab') === 'preferences');
  let busy = $state(false);
  const submit = () => {
    busy = true;
    return async ({update}) => { try { await update({reset:false}); } finally { busy = false; } };
  };
  /** @returns {`/notifications?${string}`} */
  function historyLink(status = data.pagination.status, number = 1) {
    return `/notifications?${new URLSearchParams({status, page:String(number)})}`;
  }
  let error = $state('');
  async function openNotification(event, n) {
    if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || n.read_at) return;
    event.preventDefault();
    if (busy) return;
    busy = true;
    error = '';
    try {
      const body = new FormData(); body.set('id', n.id);
      const response = await fetch('?/read', {method:'POST', body});
      const result = deserialize(await response.text());
      if (result.type !== 'success') throw new Error();
      await goto(resolve(n.resolved_link));
    } catch { error = 'Could not open this notification. Please try again.'; }
    finally { busy = false; }
  }
  function phrase(verb) {
    return {'webform.submitted':'received a website submission through', 'case.mentioned':'mentioned you on', 'case.commented':'commented on', 'support.replied':'replied to', 'support.status_changed':'updated'}[verb] || 'updated';
  }
</script>

<PageHeader title="Notifications">
  {#snippet sub()}{data.totals.unread} unread{/snippet}
  {#snippet actions()}
    {#if !preferencesOpen}
      <form method="POST" action="?/readAll" use:enhance={submit}>
        <button class="v2-btn v2-btn-sm" disabled={busy || !data.totals.unread}><Check size={15}/>Mark all read</button>
      </form>
    {/if}
  {/snippet}
</PageHeader>
<nav class="tabs" aria-label="Notification sections">
  <a href={resolve('/notifications')} class:active={!preferencesOpen} aria-current={!preferencesOpen ? 'page' : undefined}>History</a>
  <a href={resolve('/notifications?tab=preferences')} class:active={preferencesOpen} aria-current={preferencesOpen ? 'page' : undefined}>Preferences</a>
</nav>
<div class="v2-scroll">
  <div class="content">
    {#if preferencesOpen}
      <h2>Notification preferences</h2>
      <p class="muted">Choose the notifications you receive in this organization.</p>
      <form class="preferences" method="POST" action="?/preferences&tab=preferences" use:enhance={submit}>
        {#each [
          ['notify_in_app', 'In-app notifications', 'Receive notifications inside the CRM.'],
          ['notify_mentions', 'Mentions', 'When someone mentions you in a ticket.'],
          ['notify_comments', 'Ticket comments', 'New comments on tickets you follow.']
        ] as [key, label, description]}
          <label class="preference"><span><strong>{label}</strong><small>{description}</small></span><input type="checkbox" name={key} checked={data.preferences[key] ?? true}/></label>
        {/each}
        <button class="v2-btn save" disabled={busy}>{busy ? 'Saving…' : 'Save preferences'}</button>
        {#if form?.scope === 'preferences'}<p role="status" class:error={form.message}>{form.message || 'Preferences saved.'}</p>{/if}
      </form>
    {:else}
      <nav class="filters" aria-label="Filter notifications">
        {#each [['all','All'], ['unread','Unread'], ['read','Read']] as [value,label]}
          <a href={resolve(historyLink(value))} class:selected={data.pagination.status === value} aria-current={data.pagination.status === value ? 'page' : undefined}>{label}</a>
        {/each}
      </nav>
      {#if error}<p class="error" role="alert">{error}</p>{/if}
      {#if form?.error}<p class="error" role="alert">{form.error}</p>{/if}
      {#if data.results.length}
        <ul class="feed">
          {#each data.results as n (n.id)}
            <li class:unread={!n.read_at}>
              <span class="indicator" class:dot={!n.read_at} aria-label={n.read_at ? 'Read' : 'Unread'}></span>
              <div class="message">
                <p><strong>{n.actor?.name || 'The system'}</strong> {phrase(n.verb)}
                  {#if n.resolved_link}<a href={resolve(n.resolved_link)} onclick={(event) => openNotification(event, n)}>{n.entity_name || 'a ticket'}</a>{:else}{n.entity_name || 'a ticket'}{/if}
                </p>
                {#if n.data?.comment_excerpt}<p class="excerpt">{n.data.comment_excerpt}</p>{/if}
                <time datetime={n.created_at} title={new Date(n.created_at).toLocaleString()}>{relativeTime(n.created_at)} · {n.read_at ? 'Read' : 'Unread'}</time>
              </div>
              {#if !n.read_at}
                <form method="POST" action="?/read" use:enhance={submit}>
                  <input type="hidden" name="id" value={n.id}/>
                  <button class="read-button" disabled={busy} aria-label="Mark notification read" title="Mark read"><Check size={16}/></button>
                </form>
              {/if}
            </li>
          {/each}
        </ul>
      {:else}
        <div class="empty"><Bell size={26}/><h2>{data.pagination.status === 'unread' ? 'You’re all caught up' : 'No notifications here'}</h2><p>New notifications will appear here as they arrive.</p></div>
      {/if}
      {#if data.pagination.pages > 1 || data.pagination.page > 1}
        <nav class="pagination" aria-label="Notification pages">
          {#if data.pagination.page > 1}<a class="v2-btn v2-btn-sm" href={resolve(historyLink(data.pagination.status, data.pagination.page - 1))}><ChevronLeft size={14}/>Previous</a>{/if}
          <span>Page {data.pagination.page} · {data.totals.count} notifications</span>
          {#if data.pagination.page < data.pagination.pages}<a class="v2-btn v2-btn-sm" href={resolve(historyLink(data.pagination.status, data.pagination.page + 1))}>Next<ChevronRight size={14}/></a>{/if}
        </nav>
      {/if}
    {/if}
  </div>
</div>

<style>
  .tabs { display:flex; gap:26px; padding:0 24px; border-bottom:1px solid var(--v2-line); }
  .tabs a { padding:14px 0; color:var(--v2-slate); text-decoration:none; border-bottom:2px solid transparent; font-size:13px; }
  .tabs a.active { color:var(--v2-ink); border-color:var(--v2-ink); font-weight:600; }
  .content { padding:24px; max-width:1040px; }
  .filters { display:flex; gap:4px; margin-bottom:20px; }
  .filters a { padding:7px 14px; border-radius:7px; text-decoration:none; color:var(--v2-slate); font-size:12px; }
  .filters a.selected { background:var(--v2-line-soft); color:var(--v2-ink); font-weight:600; }
  .feed { list-style:none; margin:0; padding:0; }
  li { display:flex; align-items:flex-start; gap:12px; padding:16px 12px; border-bottom:1px solid var(--v2-line-soft); }
  li.unread { background:var(--v2-line-soft); border-radius:8px; }
  .indicator { width:6px; height:6px; flex:none; margin-top:7px; border-radius:50%; }
  .dot { background:var(--v2-ink); }
  .message { flex:1; min-width:0; }
  .message p { margin:0; font-size:13px; line-height:1.6; overflow-wrap:anywhere; }
  .message a { color:inherit; text-decoration:underline; text-underline-offset:3px; }
  .message .excerpt { color:var(--v2-slate); margin-top:4px; display:-webkit-box; -webkit-line-clamp:2; line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }
  time { display:block; margin-top:7px; font-size:11px; color:var(--v2-slate); }
  .read-button { display:grid; place-items:center; border:1px solid var(--v2-line); background:transparent; color:var(--v2-slate); border-radius:6px; width:30px; height:30px; cursor:pointer; }
  .pagination { display:flex; align-items:center; justify-content:flex-end; flex-wrap:wrap; gap:14px; margin-top:20px; font-size:12px; color:var(--v2-slate); }
  .empty { display:flex; flex-direction:column; align-items:center; text-align:center; padding:64px 16px; color:var(--v2-slate); }
  h2 { font-size:16px; color:var(--v2-ink); }
  .empty p,.muted { font-size:13px; color:var(--v2-slate); }
  .preferences { max-width:640px; }
  .preference { display:flex; justify-content:space-between; align-items:center; gap:20px; padding:18px 0; border-bottom:1px solid var(--v2-line-soft); }
  .preference strong { font-size:13px; font-weight:500; }
  .preference small { display:block; color:var(--v2-slate); margin-top:5px; font-size:12px; }
  .preference input { accent-color:var(--v2-ink); width:17px; height:17px; }
  .save { margin-top:20px; }
  .error { color:var(--v2-rust); }
  @media(max-width:600px) { .content { padding:16px; } .tabs { padding-inline:16px; } }
</style>
