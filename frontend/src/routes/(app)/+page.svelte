<script>
  import '$lib/v2/styles/module-layout.css';
  import { useI18n } from '$lib/i18n/context.js';
  const { ui, locale, money } = useI18n();

  import { resolve } from '$app/paths';
  import { invalidateAll } from '$app/navigation';
  import { enhance } from '$app/forms';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import EventDetails from '$lib/v2/components/EventDetails.svelte';

  import { CalendarDays, Circle, CheckCheck, Clock3, ArrowUpRight } from '@lucide/svelte';
  let { data, form } = $props();
  let day = $derived(data.day);
  let details;
  let saving = $state({});
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
</script>

<PageHeader title={ui('Today')}>
  {#snippet sub()}{ui('Your day at a glance ·')}
    {new Date(`${day.date}T12:00:00`).toLocaleDateString(locale(), {
      weekday: 'long',
      month: 'long',
      day: 'numeric'
    })}{/snippet}
  {#snippet actions()}{#if day.can_select_user}<form method="GET">
        <select
          class="v2-input"
          aria-label={ui('Whose day')}
          name="user"
          value={day.selected_user}
          onchange={(event) => event.currentTarget.form?.requestSubmit()}
          ><option value="all">{ui('Team day')}</option>{#each day.people as person}<option
              value={person.id}
              >{person.id === day.current_user ? ui('My day') : person.name}</option
            >{/each}</select
        >
      </form>{:else}<span class="my-day">{ui('My day')}</span>{/if}{/snippet}
</PageHeader>
<EventDetails bind:this={details} onChanged={() => void invalidateAll()} />
{#if form?.error}<p class="error" role="alert">{ui(form.error)}</p>{/if}
<div class="today-scroll crm-module-body">
  <div class="day-counts crm-stat-grid">
    <div class="crm-stat crm-panel">
      <span><CalendarDays size={16} />{ui('Events today')}</span><strong>{day.counts.events}</strong
      >
    </div>
    <div class="crm-stat crm-panel">
      <span><CheckCheck size={16} />{ui('Tasks due today')}</span><strong
        >{day.counts.tasks_today}</strong
      >
    </div>
    <div class="crm-stat crm-panel" class:late={day.counts.overdue > 0}>
      <span><Clock3 size={16} />{ui('Overdue')}</span><strong>{day.counts.overdue}</strong>
    </div>
  </div>
  <div class="day-layout">
    <section class="panel agenda crm-panel">
      <header>
        <h2>{ui("Today's agenda")} <span>{day.counts.events}</span></h2>
        <a href={resolve('/calendar')}>{ui('View calendar')} <ArrowUpRight size={13} /></a>
      </header>
      <p class="timezone">{day.timezone.replaceAll('_', ' ')}</p>
      {#each day.events as event}<button
          class="event"
          class:company={event.attendee?.type === 'company'}
          onclick={(click) => details.open(event, click.currentTarget)}
          ><span class="event-time">{clock(event.start)}<small>{clock(event.end)}</small></span
          ><span
            ><strong>{event.title}</strong>{#if event.attendee}<small
                >{event.attendee.type === 'company' ? ui('Company') : ui('Contact')} · {event
                  .attendee.name}</small
              >{/if}<small>{event.host}</small></span
          ></button
        >{:else}<div class="empty">
          <CalendarDays size={24} />
          <p>{ui('No events scheduled today.')}</p>
          <a href={resolve('/calendar')}>{ui('Schedule an event')}</a>
        </div>{/each}
      {#if day.counts.events > day.events.length}<a class="more" href={resolve('/calendar')}
          >{ui('View all')} {day.counts.events} {ui('events')}</a
        >{/if}
    </section>
    <div class="work">
      {#if day.reminders?.length}<section class="panel crm-panel">
          <header>
            <h2>{ui('Task reminders')} <span>{day.counts.reminders}</span></h2>
            <a href={resolve('/tasks')}>{ui('View all')} <ArrowUpRight size={13} /></a>
          </header>
          {#each day.reminders as task}<a class="work-row" href={resolve(`/tasks/${task.id}`)}
              ><span class="record"
                ><strong>{task.name}</strong><small>{task.priority} {ui('priority')}</small></span
              ><span class="due">{ui('Due')} {date(task.due)}</span></a
            >{/each}
        </section>{/if}
      <section class="panel crm-panel">
        <header>
          <h2>{ui('Tasks')} <span>{day.counts.tasks}</span></h2>
          <a href={resolve('/tasks')}>{ui('View all')} <ArrowUpRight size={13} /></a>
        </header>
        {#each day.tasks as task}<div class="work-row">
            <form
              method="POST"
              action="?/complete"
              use:enhance={() => {
                saving[task.id] = true;
                return async ({ update }) => {
                  try {
                    await update({ reset: false });
                  } finally {
                    saving[task.id] = false;
                  }
                };
              }}
            >
              <input type="hidden" name="id" value={task.id} /><button
                class="complete"
                aria-label={`Complete ${task.name}`}
                title={ui('Complete task')}
                disabled={saving[task.id]}><Circle size={19} /></button
              >
            </form>
            <a class="record" href={resolve(`/tasks/${task.id}`)}
              ><strong>{task.name}</strong><small>{task.priority} · {task.status}</small></a
            ><span class="due" class:late={task.overdue}
              >{task.overdue ? date(task.due) : ui('Today')}</span
            >
          </div>{:else}<p class="empty-copy">{ui('No tasks due today or overdue.')}</p>{/each}
      </section>
      <section class="panel crm-panel">
        <header>
          <h2>{ui('Deals to follow up')} <span>{day.counts.deals}</span></h2>
          <a href={resolve('/pipeline')}>{ui('View all')} <ArrowUpRight size={13} /></a>
        </header>
        {#each day.deals as deal}<a class="work-row record" href={resolve(`/pipeline/${deal.id}`)}
            ><span
              ><strong>{deal.name}</strong><small
                >{deal.stage} · {money(deal.amount, deal.currency)}</small
              ></span
            ><span class="due" class:late={deal.overdue}
              >{deal.overdue ? date(deal.due) : ui('Today')}</span
            ></a
          >{:else}<p class="empty-copy">
            {ui('No open deals due to close today or overdue.')}
          </p>{/each}
      </section>
      <section class="panel crm-panel">
        <header>
          <h2>{ui('Tickets')} <span>{day.counts.tickets}</span></h2>
          <a href={resolve('/tickets')}>{ui('View all')} <ArrowUpRight size={13} /></a>
        </header>
        {#each day.tickets as ticket}<a
            class="work-row record"
            href={resolve(`/tickets/${ticket.id}`)}
            ><span
              ><strong>{ticket.name}</strong><small>{ticket.code} · {ticket.priority}</small></span
            ><span class="due" class:late={ticket.overdue}
              >{ticket.overdue ? date(ticket.due) : ui('Today')}</span
            ></a
          >{:else}<p class="empty-copy">{ui('No open tickets due today or overdue.')}</p>{/each}
      </section>
    </div>
  </div>
</div>

<style>
  .today-scroll {
    flex: 1;
    min-height: 0;
    overflow: auto;
  }
  .day-counts {
    margin-bottom: var(--crm-space-5);
  }
  .day-counts span {
    display: flex;
    align-items: center;
    gap: var(--crm-space-2);
  }
  .day-counts .late strong {
    color: var(--crm-danger);
  }
  header {
    flex-wrap: wrap;
  }
  .event:hover {
    background: var(--crm-surface-selected);
  }
  .event:focus-visible,
  .complete:focus-visible {
    outline: 2px solid var(--crm-focus);
    outline-offset: 2px;
  }
  .day-layout {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1.1fr);
    gap: var(--crm-space-4);
    align-items: start;
  }
  .panel {
    padding: var(--crm-space-5);
  }
  .work {
    display: grid;
    gap: var(--crm-space-4);
  }
  header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 10px;
    margin-bottom: var(--crm-space-3);
  }
  h2 {
    font-size: var(--crm-text-sm);
    font-weight: 650;
    margin: 0;
  }
  h2 span {
    font-weight: 400;
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
    margin-left: 6px;
  }
  header a {
    display: flex;
    align-items: center;
    gap: var(--crm-space-1);
    font-size: var(--crm-text-xs);
    white-space: nowrap;
    color: var(--v2-slate);
    text-decoration: none;
  }
  .timezone {
    margin: -4px 0 var(--crm-space-4);
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
  }
  .event {
    display: flex;
    text-align: left;
    gap: var(--crm-space-4);
    width: 100%;
    border: 0;
    border-left: 3px solid var(--crm-primary);
    background: var(--v2-paper);
    border-radius: var(--crm-radius-md);
    padding: 14px var(--crm-space-3);
    margin: var(--crm-space-2) 0;
    cursor: pointer;
    color: var(--v2-ink);
  }
  .event.company {
    border-left-color: var(--crm-success);
  }
  .event-time {
    flex-shrink: 0;
    font-size: var(--crm-text-xs);
    min-width: 72px;
  }
  .event strong,
  .record strong {
    font-size: var(--crm-text-sm);
    font-weight: 600;
    overflow-wrap: anywhere;
  }
  small {
    display: block;
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
    margin-top: 5px;
  }
  .work-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: var(--crm-space-3) 0;
    border-bottom: 1px solid var(--v2-line-soft);
  }
  .work-row:last-child {
    border-bottom: 0;
    padding-bottom: 0;
  }
  .record {
    color: var(--v2-ink);
    text-decoration: none;
    flex: 1;
    min-width: 0;
  }
  .record:hover strong {
    text-decoration: underline;
  }
  .work-row > span:first-child {
    flex: 1;
  }
  .due {
    margin-left: auto;
    font-size: var(--crm-text-xs);
    flex-shrink: 0;
    color: var(--v2-slate);
  }
  .late {
    color: var(--v2-rust);
  }
  .complete {
    border: 0;
    background: none;
    display: grid;
    place-items: center;
    width: 28px;
    height: 28px;
    color: var(--v2-slate);
    cursor: pointer;
  }
  .complete:disabled {
    opacity: 0.4;
    cursor: wait;
  }
  .empty {
    padding: 36px var(--crm-space-3);
    text-align: center;
    color: var(--v2-slate);
    font-size: var(--crm-text-sm);
  }
  .empty :global(svg) {
    margin: auto;
  }
  .empty a,
  .more {
    font-size: var(--crm-text-xs);
    color: var(--v2-ink);
  }
  .empty-copy {
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
    margin: var(--crm-space-5) 0 6px;
  }
  .error {
    color: var(--v2-rust);
    padding: 0 var(--crm-space-6);
  }
  .my-day {
    color: var(--v2-slate);
    font-size: var(--crm-text-sm);
  }
  @media (max-width: 1050px) {
    .day-layout {
      grid-template-columns: 1fr;
    }
  }
</style>
