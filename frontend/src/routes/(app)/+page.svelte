<script>
  import { onMount } from 'svelte';
  import { page } from '$app/state';
  import { resolve } from '$app/paths';
  import { goto, invalidateAll } from '$app/navigation';
  import { enhance } from '$app/forms';
  import {
    CalendarDays,
    Circle,
    CheckCheck,
    Clock3,
    ArrowUpRight,
    Plus,
    ChevronDown,
    LifeBuoy,
    Handshake,
    ListTodo
  } from '@lucide/svelte';
  import Notice from '$lib/components/Notice.svelte';
  import SearchableSelect from '$lib/components/SearchableSelect.svelte';
  import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import EventDetails from '$lib/v2/components/EventDetails.svelte';
  import CreateAppointment from '$lib/v2/components/CreateAppointment.svelte';
  import { can } from '$lib/v2/permissions.js';
  import { asInternalPath } from '$lib/utils/paths.js';
  import { attentionPreview, agendaPreview } from '$lib/v2/today-dashboard.js';
  import { useI18n } from '$lib/i18n/context.js';
  import '$lib/v2/styles/module-layout.css';

  const { ui, locale, money } = useI18n();
  let { data, form } = $props();
  let day = $derived(data.day);
  let details;
  let saving = $state({});
  let filter = $state('all');
  let now = $state(0);
  let agendaSection;
  const work = $derived(attentionPreview(day, filter));
  const agenda = $derived(agendaPreview(day.events, now || Date.parse(day.now)));
  const tabs = ['all', 'tasks', 'tickets', 'deals'];
  const labels = {
    all: 'All',
    tasks: 'Tasks',
    tickets: 'Tickets',
    deals: 'Deals',
    overdue: 'Overdue',
    today: 'Tasks today',
    followups: 'Follow-ups'
  };
  const types = { tasks: 'Task', tickets: 'Ticket', deals: 'Deal' };
  const icons = { tasks: ListTodo, tickets: LifeBuoy, deals: Handshake };
  const createOptions = [
    { module: 'contacts', label: 'Create contact', path: '/contacts/new' },
    { module: 'companies', label: 'Create company', path: '/accounts/new' },
    { module: 'deals', label: 'Create deal', path: '/pipeline/new' },
    { module: 'tasks', label: 'Create task', path: '/tasks/new' },
    { module: 'tickets', label: 'Create ticket', path: '/tickets/new' }
  ];
  const allowedCreates = $derived(
    createOptions.filter((option) => can(page.data.permissions, option.module, 'create'))
  );
  const dayOptions = $derived([
    { value: 'all', label: ui('Team day') },
    ...day.people.map((person) => ({
      value: person.id,
      label: person.id === day.current_user ? ui('My day') : person.name
    }))
  ]);
  const clock = (value) =>
    new Date(value).toLocaleTimeString(locale(), {
      hour: 'numeric',
      minute: '2-digit',
      timeZone: day.timezone
    });
  const date = (value) =>
    new Date(`${String(value).slice(0, 10)}T12:00:00`).toLocaleDateString(locale(), {
      month: 'short',
      day: 'numeric'
    });
  onMount(() => {
    now = Date.now();
    const timer = setInterval(() => {
      now = Date.now();
    }, 30000);
    return () => clearInterval(timer);
  });
  function selectMetric(next) {
    filter = filter === next ? 'all' : next;
  }
</script>

<PageHeader title={ui('Today')} compact>
  {#snippet sub()}{new Date(`${day.date}T12:00:00`).toLocaleDateString(locale(), {
      weekday: 'long',
      month: 'short',
      day: 'numeric'
    })}{/snippet}
  {#snippet actions()}
    <div class="day-actions crm-control-toolbar">
      {#if day.can_select_user}
        <div class="day-select">
          <SearchableSelect
            value={day.selected_user}
            options={dayOptions}
            label={ui('Whose day')}
            onchange={(value) =>
              void goto(resolve(asInternalPath(`/?user=${encodeURIComponent(value)}`)), {
                keepFocus: true,
                noScroll: true
              })}
          />
        </div>
      {:else}<span class="my-day">{ui('My day')}</span>{/if}
      {#if allowedCreates.length}
        <DropdownMenu.Root>
          <DropdownMenu.Trigger class="v2-btn v2-btn-primary"
            ><Plus size={16} />{ui('Create')}<ChevronDown size={14} /></DropdownMenu.Trigger
          >
          <DropdownMenu.Content align="end">
            {#each allowedCreates as option (option.module)}
              <DropdownMenu.Item
                >{#snippet child({ props })}<a
                    {...props}
                    href={resolve(asInternalPath(option.path))}>{ui(option.label)}</a
                  >{/snippet}</DropdownMenu.Item
              >
            {/each}
          </DropdownMenu.Content>
        </DropdownMenu.Root>
      {/if}
    </div>
  {/snippet}
</PageHeader>
<EventDetails bind:this={details} onChanged={() => void invalidateAll()} />
{#if form?.error}<Notice message={ui(form.error)} />{/if}
<div class="today-scroll crm-module-body">
  <div class="day-counts" aria-label={ui('Daily summary')}>
    <button
      class="metric crm-panel"
      class:active={filter === 'overdue'}
      class:late={day.counts.overdue > 0}
      aria-pressed={filter === 'overdue'}
      onclick={() => selectMetric('overdue')}
    >
      <span class="metric-label"><Clock3 size={17} />{ui('Overdue')}</span><strong
        >{day.counts.overdue}</strong
      ><ArrowUpRight class="metric-arrow" size={16} />
    </button>
    <button
      class="metric crm-panel"
      class:active={filter === 'today'}
      aria-pressed={filter === 'today'}
      onclick={() => selectMetric('today')}
    >
      <span class="metric-label"><CheckCheck size={17} />{ui('Tasks today')}</span><strong
        >{day.counts.tasks_today}</strong
      ><ArrowUpRight class="metric-arrow" size={16} />
    </button>
    <button
      class="metric crm-panel"
      onclick={() => {
        agendaSection?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        agendaSection?.focus({ preventScroll: true });
      }}
    >
      <span class="metric-label"><CalendarDays size={17} />{ui('Meetings')}</span><strong
        >{day.counts.events}</strong
      ><ArrowUpRight class="metric-arrow" size={16} />
    </button>
    <button
      class="metric crm-panel"
      class:active={filter === 'followups'}
      aria-pressed={filter === 'followups'}
      onclick={() => selectMetric('followups')}
    >
      <span class="metric-label"><Handshake size={17} />{ui('Follow-ups')}</span><strong
        >{day.counts.deals + day.counts.reminders}</strong
      ><ArrowUpRight class="metric-arrow" size={16} />
    </button>
  </div>
  <div class="day-layout">
    <section class="panel crm-panel" aria-labelledby="attention-title">
      <header class="crm-panel-heading">
        <h2 id="attention-title">
          {ui('Needs attention')} <span class="count">{work.total}</span>
        </h2>
      </header>
      <div class="queue-toolbar crm-control-toolbar" aria-label={ui('Filter pending work')}>
        {#each tabs as tab (tab)}<button
            class="v2-btn v2-btn-ghost"
            class:selected={filter === tab}
            aria-pressed={filter === tab}
            onclick={() => {
              filter = tab;
            }}>{ui(labels[tab])}</button
          >{/each}
        {#if !tabs.includes(filter)}<button
            class="v2-btn v2-btn-secondary active-filter"
            onclick={() => {
              filter = 'all';
            }}
            aria-label={ui('Clear filter')}>{ui(labels[filter])} ×</button
          >{/if}
      </div>
      <div class="work-list" aria-live="polite">
        {#each work.rows as item (`${item.kind}:${item.id}`)}
          <div class="work-row">
            {#if item.kind === 'tasks' && item.can_complete}
              <form
                method="POST"
                action="?/complete"
                use:enhance={() => {
                  saving[item.id] = true;
                  return async ({ update }) => {
                    try {
                      await update({ reset: false });
                    } finally {
                      saving[item.id] = false;
                    }
                  };
                }}
              >
                <input type="hidden" name="id" value={item.id} />
                <button
                  class="complete"
                  aria-label={`${ui('Complete task')}: ${item.name}`}
                  title={ui('Complete task')}
                  disabled={saving[item.id]}><Circle size={19} /></button
                >
              </form>
            {:else}{@const Icon = icons[item.kind]}<span class="record-icon"
                ><Icon size={18} /></span
              >{/if}
            <a class="record" href={resolve(asInternalPath(item.href))}
              ><strong>{item.name}</strong><small
                >{ui(types[item.kind])}{#if item.reminder}
                  · {ui('Reminder')}{:else if item.kind === 'deals'}
                  · {ui(item.stage)}{:else if item.priority}
                  · {ui(item.priority)}{/if}</small
              ></a
            >
            <span class="due" class:late={item.overdue}
              >{#if item.overdue}<span>{ui('Overdue')}</span>{/if}{item.due === day.date
                ? ui('Today')
                : date(item.due)}</span
            >
            <a
              class="open-record v2-icon-btn"
              href={resolve(asInternalPath(item.href))}
              aria-label={`${ui('Open')}: ${item.name}`}><ArrowUpRight size={17} /></a
            >
          </div>
        {:else}<p class="empty-copy">{ui('No pending items in this view.')}</p>{/each}
      </div>
      <footer class="panel-footer">
        <span
          >{ui('Showing {shown} of {total}', { shown: work.rows.length, total: work.total })}</span
        >
        <div class="module-links">
          {#if can(page.data.permissions, 'tasks')}<a href={resolve('/tasks')}
              >{ui('Tasks')}<ArrowUpRight size={12} /></a
            >{/if}
          {#if can(page.data.permissions, 'tickets')}<a href={resolve('/tickets')}
              >{ui('Tickets')}<ArrowUpRight size={12} /></a
            >{/if}
          {#if can(page.data.permissions, 'deals')}<a href={resolve('/pipeline')}
              >{ui('Deals')}<ArrowUpRight size={12} /></a
            >{/if}
        </div>
      </footer>
    </section>
    <section
      class="panel agenda crm-panel"
      bind:this={agendaSection}
      tabindex="-1"
      aria-labelledby="agenda-title"
    >
      <header class="crm-panel-heading">
        <h2 id="agenda-title">
          {ui("Today's agenda")} <span class="count">{day.counts.events}</span>
        </h2>
        <a href={resolve('/calendar')} aria-label={ui('View calendar')} title={ui('View calendar')}
          ><ArrowUpRight size={16} /></a
        >
      </header>
      {#each agenda.rows as event (event.id)}
        <button
          class="event"
          class:next={event.id === agenda.nextId}
          class:finished={Date.parse(event.end) <= now}
          onclick={(click) => details.open(event, click.currentTarget)}
        >
          <span class="event-time">{clock(event.start)}<small>{clock(event.end)}</small></span>
          <span class="event-info"
            >{#if event.id === agenda.nextId}<span class="next-label"
                >{ui(Date.parse(event.start) <= now ? 'In progress' : 'Up next')}</span
              >{/if}<strong>{event.title}</strong>{#if event.attendee}<small
                >{event.attendee.name}</small
              >{/if}{#if day.selected_user === 'all'}<small>{event.host}</small>{/if}</span
          >
          <ArrowUpRight size={15} />
        </button>
      {:else}<p class="empty-copy">{ui('No events scheduled today.')}</p>{/each}
      <footer class="panel-footer">
        <a href={resolve('/calendar')}>{ui('View calendar')}<ArrowUpRight size={12} /></a
        >{#if can(page.data.permissions, 'calendar', 'create')}
          <CreateAppointment
            hosts={day.people}
            defaultHost={day.selected_user === 'all' ? day.current_user : day.selected_user}
            selected={new Date(`${day.date}T12:00:00`)}
            onCreated={() => void invalidateAll()}
          />
        {/if}
      </footer>
    </section>
  </div>
  <section class="panel weekly crm-panel" aria-labelledby="weekly-title">
    <header class="crm-panel-heading">
      <h2 id="weekly-title">
        {ui('Deals closing this week')} <span class="count">{day.counts.weekly_deals}</span>
      </h2>
      <div class="weekly-actions">
        <span>{date(day.date)} – {date(day.week_end)}</span><a href={resolve('/pipeline')}
          >{ui('View all')}<ArrowUpRight size={13} /></a
        >
      </div>
    </header>
    <table class="deal-table">
      <thead
        ><tr
          ><th scope="col">{ui('Name')}</th><th scope="col">{ui('Stage')}</th><th
            scope="col"
            class="numeric">{ui('Amount')}</th
          ><th scope="col">{ui('Close date')}</th><th scope="col"
            ><span class="sr-only">{ui('Open')}</span></th
          ></tr
        ></thead
      >
      <tbody
        >{#each day.weekly_deals as deal (deal.id)}<tr
            ><td
              ><a class="record" href={resolve(`/pipeline/${deal.id}`)}
                ><strong>{deal.name}</strong></a
              ></td
            ><td>{ui(deal.stage)}</td><td class="numeric">{money(deal.amount, deal.currency)}</td
            ><td>{deal.due === day.date ? ui('Today') : date(deal.due)}</td><td
              ><a
                class="v2-icon-btn"
                href={resolve(`/pipeline/${deal.id}`)}
                aria-label={`${ui('Open')}: ${deal.name}`}><ArrowUpRight size={16} /></a
              ></td
            ></tr
          >{:else}<tr
            ><td colspan="5" class="empty-copy">{ui('No open deals closing this week.')}</td></tr
          >{/each}</tbody
      >
    </table>
    {#if day.counts.weekly_deals > day.weekly_deals.length}<footer class="panel-footer">
        <span
          >{ui('Showing {shown} of {total}', {
            shown: day.weekly_deals.length,
            total: day.counts.weekly_deals
          })}</span
        ><a href={resolve('/pipeline')}>{ui('View all')}<ArrowUpRight size={12} /></a>
      </footer>{/if}
  </section>
</div>

<style>
  .today-scroll {
    flex: 1;
    min-height: 0;
    overflow: auto;
  }
  .day-actions {
    display: flex;
    align-items: center;
    gap: var(--crm-space-3);
  }
  .day-select {
    width: 11rem;
  }
  .my-day {
    color: var(--crm-text-muted);
    font-size: var(--crm-text-sm);
  }
  .day-counts {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: var(--crm-panel-gap);
    margin-bottom: var(--crm-space-4);
  }
  .metric {
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: var(--crm-space-2);
    padding: var(--crm-space-4) var(--crm-space-5);
    cursor: pointer;
    text-align: left;
    color: var(--crm-text);
  }
  .metric-label {
    display: flex;
    align-items: center;
    gap: var(--crm-space-2);
    color: var(--crm-text-muted);
    font-size: var(--crm-text-sm);
  }
  .metric strong {
    font-size: var(--crm-text-2xl);
    line-height: 1.15;
    font-weight: 650;
    font-variant-numeric: tabular-nums;
  }
  .metric :global(.metric-arrow) {
    position: absolute;
    right: var(--crm-space-4);
    bottom: var(--crm-space-4);
    color: var(--crm-text-muted);
  }
  .metric:hover {
    background: var(--crm-surface-subtle);
  }
  .metric.active {
    border-color: var(--crm-primary);
    background: var(--crm-surface-selected);
  }
  .late,
  .metric.late strong {
    color: var(--crm-danger);
  }
  .day-layout {
    display: grid;
    grid-template-columns: minmax(0, 1.85fr) minmax(0, 1fr);
    gap: var(--crm-panel-gap);
    align-items: start;
  }
  .panel {
    padding: 0;
    overflow: hidden;
  }
  h2 {
    display: flex;
    align-items: center;
    gap: var(--crm-space-2);
    margin: 0;
    font-size: var(--crm-text-base);
    font-weight: 650;
  }
  .count {
    color: var(--crm-text-muted);
    font-size: var(--crm-text-xs);
    font-weight: 500;
  }
  .crm-panel-heading {
    min-height: 3.25rem;
    padding: var(--crm-space-3) var(--crm-space-4);
  }
  .queue-toolbar {
    display: flex;
    align-items: center;
    gap: var(--crm-space-1);
    padding: var(--crm-space-2) var(--crm-space-4);
    border-bottom: 1px solid var(--crm-border-soft);
  }
  .queue-toolbar .selected {
    background: var(--crm-surface-selected);
    color: var(--crm-link);
  }
  .active-filter {
    margin-left: auto;
  }
  .work-row {
    display: flex;
    align-items: center;
    gap: var(--crm-space-3);
    padding: var(--crm-space-3) var(--crm-space-4);
    border-bottom: 1px solid var(--crm-border-soft);
    min-height: 4rem;
  }
  .work-row:last-child {
    border-bottom: 0;
  }
  .work-row:hover {
    background: var(--crm-surface-subtle);
  }
  .complete,
  .record-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 1.75rem;
    height: 1.75rem;
    flex: none;
    color: var(--crm-text-muted);
  }
  .complete {
    cursor: pointer;
    border: 0;
    background: transparent;
    border-radius: 50%;
  }
  .complete:hover {
    color: var(--crm-success);
    background: var(--crm-success-bg);
  }
  .complete:disabled {
    opacity: 0.45;
    cursor: wait;
  }
  .record {
    min-width: 0;
    flex: 1;
    color: var(--crm-text);
    text-decoration: none;
  }
  .record strong,
  .event strong {
    display: block;
    font-weight: 600;
    font-size: var(--crm-text-sm);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .record small,
  .event small {
    display: block;
    margin-top: 3px;
    color: var(--crm-text-muted);
    font-size: var(--crm-text-xs);
  }
  .record:hover strong {
    color: var(--crm-link);
  }
  .due {
    text-align: right;
    flex: none;
    font-size: var(--crm-text-xs);
  }
  .due span {
    display: block;
    font-weight: 600;
    margin-bottom: 3px;
  }
  .open-record {
    flex: none;
  }
  .event {
    width: 100%;
    display: flex;
    align-items: center;
    gap: var(--crm-space-3);
    padding: var(--crm-space-4);
    color: var(--crm-text);
    background: transparent;
    border: 0;
    border-bottom: 1px solid var(--crm-border-soft);
    text-align: left;
    cursor: pointer;
  }
  .event.next {
    background: var(--crm-surface-selected);
    box-shadow: inset 3px 0 var(--crm-primary);
  }
  .event:hover {
    background: var(--crm-surface-subtle);
  }
  .event.finished {
    color: var(--crm-text-muted);
  }
  .event-time {
    flex: none;
    width: 5.2rem;
    font-size: var(--crm-text-sm);
    font-weight: 600;
    font-variant-numeric: tabular-nums;
  }
  .event-info {
    min-width: 0;
    flex: 1;
  }
  .next-label {
    display: block;
    margin-bottom: var(--crm-space-1);
    font-size: var(--crm-text-xs);
    font-weight: 600;
    color: var(--crm-link);
  }
  .empty-copy {
    margin: 0;
    padding: var(--crm-space-6) var(--crm-space-4);
    color: var(--crm-text-muted);
    font-size: var(--crm-text-sm);
  }
  .panel-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--crm-space-3);
    padding: var(--crm-space-3) var(--crm-space-4);
    border-top: 1px solid var(--crm-border-soft);
    color: var(--crm-text-muted);
    font-size: var(--crm-text-xs);
  }
  .panel-footer a,
  .crm-panel-heading a {
    display: inline-flex;
    align-items: center;
    gap: var(--crm-space-1);
    color: var(--crm-link);
    text-decoration: none;
    font-size: var(--crm-text-xs);
  }
  .module-links,
  .weekly-actions {
    display: flex;
    align-items: center;
    gap: var(--crm-space-4);
  }
  .weekly {
    margin-top: var(--crm-space-4);
  }
  .weekly-actions > span {
    color: var(--crm-text-muted);
    font-size: var(--crm-text-xs);
  }
  .deal-table {
    width: 100%;
    border-collapse: collapse;
    text-align: left;
    font-size: var(--crm-text-sm);
  }
  .deal-table th {
    background: var(--crm-surface-secondary);
    color: var(--crm-text-muted);
    font-weight: 600;
  }
  .deal-table th,
  .deal-table td {
    padding: var(--crm-space-3) var(--crm-space-4);
    border-bottom: 1px solid var(--crm-border-soft);
  }
  .deal-table tr:last-child td {
    border-bottom: 0;
  }
  .deal-table th:first-child {
    width: 42%;
  }
  .deal-table td:last-child {
    width: 3rem;
  }
  .deal-table tbody tr:hover {
    background: var(--crm-surface-subtle);
  }
  .numeric {
    text-align: right;
    font-variant-numeric: tabular-nums;
  }
</style>
