<script>
  import { SvelteMap } from 'svelte/reactivity';

  import Notice from '$lib/components/Notice.svelte';
  import ErrorNotice from '$lib/components/ErrorNotice.svelte';
  import { googleErrorMessage } from '$lib/utils/google-feedback.js';
  import '$lib/v2/styles/module-layout.css';
  import { useI18n } from '$lib/i18n/context.js';
  const { ui, locale } = useI18n();

  import CreateAppointment from '$lib/v2/components/CreateAppointment.svelte';
  let { data } = $props();
  import EventDetails from '$lib/v2/components/EventDetails.svelte';
  /** @type {EventDetails} */
  let details;
  import { onMount, tick } from 'svelte';
  import { watchResourceStatus } from '$lib/utils/watch-resource-status.js';
  import { resolve } from '$app/paths';
  import { page } from '$app/state';
  import { ChevronLeft, ChevronRight, Building2, UserRound } from '@lucide/svelte';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import { calendarDays, dateKey, shiftDate, timedCards } from '$lib/v2/calendar.js';
  let selected = $state(new Date());
  let view = $state('month');
  const periodView = $derived(view === 'agenda' ? 'month' : view);
  const zone = Intl.DateTimeFormat().resolvedOptions().timeZone.replaceAll('_', ' ');
  let ready = $state(false);
  /** @type {HTMLDivElement} */
  let scroller;
  const hours = Array.from({ length: 24 }, (_, hour) => hour);
  $effect(() => {
    const mode = view;
    if (ready)
      void tick().then(() => {
        if (scroller) scroller.scrollTop = ['month', 'agenda'].includes(mode) ? 0 : 8 * 60;
      });
  });
  let events = $state(/** @type {any[]} */ ([]));
  let busy = $state(true);
  let failure = $state('');
  let googleError = $state('');
  let refresh = $state(0);
  const days = $derived(calendarDays(selected, periodView));
  const title = $derived(
    view === 'day'
      ? selected.toLocaleDateString(locale(), { month: 'long', day: 'numeric', year: 'numeric' })
      : view === 'week'
        ? `${days[0].toLocaleDateString(locale(), { month: 'short', day: 'numeric' })} – ${days[6].toLocaleDateString(locale(), { month: 'short', day: 'numeric', year: 'numeric' })}`
        : selected.toLocaleDateString(locale(), { month: 'long', year: 'numeric' })
  );
  const grouped = $derived.by(() => {
    const result = new SvelteMap();
    for (const event of [...events].sort((a, b) => Date.parse(a.start) - Date.parse(b.start))) {
      for (const day of days) {
        const key = dateKey(day);
        const next = new Date(day.getFullYear(), day.getMonth(), day.getDate() + 1);
        const begins = Date.parse(event.start),
          ends = Date.parse(event.end || event.start);
        const occurs = event.allDay
          ? key >= event.startDate && key < event.endDate
          : begins < next.getTime() &&
            (ends > day.getTime() || dateKey(new Date(event.start)) === key);
        if (!occurs) continue;
        if (!result.has(key)) result.set(key, []);
        result.get(key).push(event);
      }
    }
    return result;
  });
  onMount(() => {
    const date = page.url.searchParams.get('date');
    const requested = /^\d{4}-\d{2}-\d{2}$/.test(date || '') ? new Date(`${date}T12:00:00`) : null;
    selected = requested && Number.isFinite(requested.getTime()) ? requested : new Date();
    if (window.matchMedia('(max-width: 700px)').matches) view = 'agenda';
    ready = true;
  });
  $effect(() => {
    if (!ready) return;
    const first = days[0],
      last = days[days.length - 1];
    const end = new Date(last.getFullYear(), last.getMonth(), last.getDate() + 1);
    const query = new URLSearchParams({
      start: first.toISOString(),
      end: end.toISOString()
    });
    refresh;
    let stopped = false;
    let revision = null;
    const controller = new AbortController();
    busy = true;
    failure = '';
    events = [];
    async function loadEvents() {
      const response = await fetch(`${resolve('/calendar/events')}?${query}`, {
        signal: controller.signal
      });
      if (!response.ok) throw new Error('Could not load appointments.');
      const result = await response.json();
      if (!stopped) {
        events = result.events;
        details?.refresh(events);
        googleError = result.googleError || '';
        revision = result.calendarRevision;
        failure = '';
      }
    }
    let stopWatching = () => {};
    loadEvents()
      .then(() => {
        if (stopped) return;
        stopWatching = watchResourceStatus({
          endpoint: `${resolve('/calendar/events')}?view=status`,
          onStatus: async (status) => {
            if (status.revision !== revision) await loadEvents();
          },
          onUnavailable: () => {
            events = [];
            failure = 'Could not load appointments. Please try again.';
            details?.close();
          }
        });
      })
      .catch(() => {
        if (!stopped) failure = 'Could not load appointments. Please try again.';
      })
      .finally(() => {
        if (!stopped) busy = false;
      });
    return () => {
      stopped = true;
      controller.abort();
      stopWatching();
    };
  });
</script>

{#snippet eventCard(event)}
  {@const attendeeType = event.attendee?.type ?? event.type}
  {@const typeLabel =
    event.type === 'google'
      ? 'Google Calendar'
      : attendeeType === 'company'
        ? 'Company'
        : attendeeType === 'contact'
          ? 'Contact'
          : 'Event'}
  <button
    type="button"
    title={`${ui(typeLabel)} · ${event.title} · ${event.allDay ? ui('All day') : new Date(event.start).toLocaleTimeString(locale(), { hour: 'numeric', minute: '2-digit' })}`}
    class="appointment"
    class:company={attendeeType === 'company'}
    class:unlinked={attendeeType !== 'company' && attendeeType !== 'contact'}
    onclick={(click) => details.open(event, click.currentTarget)}
  >
    <div class="event-time">
      {event.allDay
        ? ui('All day')
        : new Date(event.start).toLocaleTimeString(locale(), {
            hour: 'numeric',
            minute: '2-digit'
          })}
    </div>
    <strong
      >{#if attendeeType === 'company'}<Building2
          size={12}
          aria-label={ui('Company')}
        />{:else if attendeeType === 'contact'}<UserRound
          size={12}
          aria-label={ui('Contact')}
        />{/if}{event.title}</strong
    >
  </button>
{/snippet}

<EventDetails bind:this={details} onChanged={() => refresh++} />
<PageHeader title={ui('Calendar')} compact>
  {#snippet actions()}
    <CreateAppointment
      hosts={data.hosts}
      defaultHost={data.defaultHost}
      {selected}
      onCreated={() => refresh++}
    />
  {/snippet}
</PageHeader>
{#if googleError}<div class="v2-pad">
    <ErrorNotice message={ui(googleErrorMessage(googleError))} />
    <a class="v2-btn v2-btn-sm" href={resolve('/profile?google=settings')}
      >{ui('Manage connection')}</a
    >
  </div>{/if}
<div class="calendar-toolbar crm-module-toolbar">
  <div class="period-controls">
    <button class="v2-btn" onclick={() => (selected = new Date())}>{ui('Today')}</button>
    <button
      class="v2-btn"
      aria-label={ui('Previous period')}
      onclick={() => (selected = shiftDate(selected, periodView, -1))}
      ><ChevronLeft size={16} /></button
    >
    <button
      class="v2-btn"
      aria-label={ui('Next period')}
      onclick={() => (selected = shiftDate(selected, periodView, 1))}
      ><ChevronRight size={16} /></button
    >
  </div>
  <div class="period-heading">
    <h2 aria-live="polite" aria-atomic="true">{title}</h2>
    <span class="calendar-zone">{zone}</span>
  </div>
  <input
    class="v2-input jump-date"
    type="date"
    aria-label={ui('Go to date')}
    value={dateKey(selected)}
    onchange={(event) => {
      const value = new Date(`${event.currentTarget.value}T12:00:00`);
      if (Number.isFinite(value.getTime())) selected = value;
    }}
  />
  <div class="views crm-view-switch" aria-label={ui('Calendar view')}>
    {#each ['day', 'week', 'month', 'agenda'] as mode (mode)}<button
        class="v2-btn"
        class:v2-btn-primary={view === mode}
        aria-pressed={view === mode}
        onclick={() => (view = mode)}>{ui(mode[0].toUpperCase() + mode.slice(1))}</button
      >{/each}
  </div>
</div>
<div class="calendar-meta">
  <div class="event-legend" aria-label={ui('Event types')}>
    <span class="contact-key"><UserRound size={13} />{ui('Contacts')}</span><span
      class="company-key"><Building2 size={13} />{ui('Companies')}</span
    >
  </div>
</div>
{#if failure}<Notice message={ui(failure)}
    >{#snippet actions()}<button class="v2-btn" onclick={() => refresh++}>{ui('Retry')}</button
      >{/snippet}</Notice
  >
{:else if busy}<div class="calendar-message" role="status">{ui('Loading appointments…')}</div>{/if}
<div
  class="calendar-scroll crm-panel"
  bind:this={scroller}
  aria-busy={busy}
  onscroll={() => details?.close()}
>
  {#if view === 'agenda'}
    <div class="agenda">
      {#each days.filter((day) => day.getMonth() === selected.getMonth() && grouped.get(dateKey(day))?.length) as day (dateKey(day))}
        <section
          class="agenda-day"
          aria-label={day.toLocaleDateString(locale(), { dateStyle: 'full' })}
        >
          <div class="agenda-date" class:is-today={dateKey(day) === dateKey(new Date())}>
            <span>{day.toLocaleDateString(locale(), { weekday: 'short' })}</span><strong
              >{day.getDate()}</strong
            >
          </div>
          <div class="agenda-events">
            {#each grouped.get(dateKey(day)) ?? [] as event (event.id)}{@render eventCard(
                event
              )}{/each}
          </div>
        </section>
      {:else}
        {#if !busy && !failure}<p class="agenda-empty">{ui('No appointments this month.')}</p>{/if}
      {/each}
    </div>
  {:else if view === 'month'}
    <div class="month-weekdays" aria-hidden="true">
      {#each days.slice(0, 7) as day (dateKey(day))}<span
          >{day.toLocaleDateString(locale(), { weekday: 'short' })}</span
        >{/each}
    </div>
    <div class="calendar-grid month">
      {#each days as day (dateKey(day))}
        <section
          class="day"
          class:outside={view === 'month' && day.getMonth() !== selected.getMonth()}
          aria-label={day.toDateString()}
        >
          <header>
            <button
              class:today={dateKey(day) === dateKey(new Date())}
              aria-label={ui('View {date}', {
                date: day.toLocaleDateString(locale(), { dateStyle: 'full' })
              })}
              onclick={() => {
                selected = day;
                view = 'day';
              }}>{day.getDate()}</button
            >
          </header>
          <div class="appointments">
            {#each grouped.get(dateKey(day)) ?? [] as event (event.id)}
              {@render eventCard(event)}
            {:else}{#if view !== 'month' && !busy && !failure}<p class="v2-sub">
                  {ui('No appointments')}
                </p>{/if}{/each}
          </div>
        </section>
      {/each}
    </div>
  {:else}
    <div class="time-grid" style={`--day-count:${days.length}`}>
      <div class="time-corner">{ui('Time')}</div>
      {#each days as day (dateKey(day))}
        <header class="time-header">
          <span>{day.toLocaleDateString(locale(), { weekday: 'short' })}</span>
          <button
            class:today={dateKey(day) === dateKey(new Date())}
            aria-label={ui('View {date}', {
              date: day.toLocaleDateString(locale(), { dateStyle: 'full' })
            })}
            onclick={() => {
              selected = day;
              view = 'day';
            }}>{day.getDate()}</button
          >
        </header>
      {/each}
      <div class="all-day-label">{ui('All day')}</div>
      {#each days as day (dateKey(day))}<div class="all-day-events">
          {#each (grouped.get(dateKey(day)) ?? []).filter((event) => event.allDay) as event (event.id)}{@render eventCard(
              event
            )}{/each}
        </div>{/each}
      <div class="hour-labels">
        {#each hours as hour (hour)}<div class="hour-label" style={`top:${hour * 60}px`}>
            {hour % 12 || 12}
            {hour < 12 ? 'AM' : 'PM'}
          </div>{/each}
      </div>
      {#each days as day (dateKey(day))}
        <section class="time-day" aria-label={day.toDateString()}>
          {#each hours as hour (hour)}<div
              class="hour-line"
              style={`top:${hour * 60}px`}
              aria-hidden="true"
            ></div>{/each}
          {#each timedCards((grouped.get(dateKey(day)) ?? [])
              .filter((event) => !event.allDay)
              .map( (event) => ({ ...event, start: new Date(Math.max(Date.parse(event.start), day.getTime())).toISOString(), end: event.end ? new Date(Math.min(Date.parse(event.end), new Date(day.getFullYear(), day.getMonth(), day.getDate() + 1).getTime())).toISOString() : undefined, original: event }) )) as item (item.event.id)}
            <div
              class="timed-card"
              style={`height:${Math.max(14, item.duration - 2)}px;top:${item.minute}px;left:calc(${(item.lane / item.lanes) * 100}% + 3px);width:calc(${100 / item.lanes}% - 6px)`}
            >
              {@render eventCard(item.event.original ?? item.event)}
            </div>
          {/each}
        </section>
      {/each}
    </div>
  {/if}
</div>

<style>
  .all-day-label,
  .all-day-events {
    padding: 6px;
    border-bottom: 1px solid var(--v2-line);
    font-size: var(--crm-text-xs);
  }
  .all-day-events {
    display: grid;
    gap: var(--crm-space-1);
  }
  .time-grid {
    display: grid;
    grid-template-columns: 52px repeat(var(--day-count), minmax(90px, 1fr));
    isolation: isolate;
  }
  .time-corner,
  .time-header {
    position: sticky;
    top: 0;
    z-index: 3;
    background: var(--crm-surface-subtle);
    min-height: 50px;
    margin: 0;
    padding: var(--crm-space-2);
    border-bottom: 1px solid var(--v2-line);
  }
  .time-corner {
    left: 0;
    z-index: 4;
    color: var(--v2-slate);
    font-size: var(--crm-text-xs);
    display: flex;
    align-items: center;
  }
  .time-header {
    justify-content: center;
    border-right: 1px solid var(--v2-line);
  }
  .hour-labels {
    position: sticky;
    left: 0;
    z-index: 2;
    background: var(--crm-surface-subtle);
    height: 1440px;
  }
  .hour-label {
    position: absolute;
    right: 8px;
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
    padding-top: 3px;
  }
  .time-day {
    position: relative;
    height: 1440px;
    border-right: 1px solid var(--v2-line);
    min-width: 0;
  }
  .hour-line {
    position: absolute;
    width: 100%;
    height: 60px;
    border-top: 1px solid var(--v2-line);
    pointer-events: none;
  }
  .hour-line::after {
    content: '';
    position: absolute;
    top: 29px;
    width: 100%;
    border-top: 1px dotted var(--v2-line-soft);
  }
  .timed-card {
    position: absolute;
    height: 58px;
    min-width: 0;
  }
  .timed-card .appointment {
    height: 100%;
    box-sizing: border-box;
    overflow: hidden;
    padding: 2px 6px;
    gap: 1px;
  }

  .timed-card .appointment strong {
    width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: var(--crm-text-xs);
  }

  h2 {
    font-size: var(--crm-text-base);
    margin: 0;
    font-weight: 600;
  }
  .calendar-toolbar {
    align-items: center;
  }
  .views {
    margin-left: auto;
  }
  .calendar-scroll {
    margin: var(--crm-space-2) var(--crm-page-gutter) var(--crm-space-6);
    flex: 1;
    min-height: 0;
    overflow: auto;
  }
  .calendar-grid {
    display: grid;
    grid-template-columns: repeat(7, minmax(0, 1fr));
    grid-auto-rows: minmax(96px, auto);
    align-content: start;
  }

  .day {
    min-width: 0;
    border-right: 1px solid var(--v2-line);
    border-bottom: 1px solid var(--v2-line);
    padding: 6px;
  }
  .month .day {
    min-height: 96px;
  }
  .outside {
    background: var(--crm-canvas);
  }
  header {
    display: flex;
    align-items: center;
    gap: var(--crm-space-2);
    margin-bottom: 4px;
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
  }
  header button {
    border: 0;
    background: transparent;
    color: inherit;
    border-radius: 50%;
    width: 32px;
    height: 32px;
    cursor: pointer;
  }
  header button.today {
    background: var(--crm-action-bg);
    color: var(--crm-primary-text);
  }
  .appointments {
    display: grid;
    align-content: start;
    gap: var(--crm-space-2);
  }
  .month .appointments {
    min-width: 0;
  }
  .appointment {
    width: 100%;
    text-align: left;
    cursor: pointer;
    font-family: inherit;
    display: flex;
    flex-direction: column;
    gap: var(--crm-space-1);
    padding: 9px;
    background: var(--crm-info-bg);
    border: 1px solid var(--crm-info-bg);
    border-left: 3px solid var(--crm-info);
    border-radius: var(--crm-radius-sm);
    color: var(--crm-info);
    text-decoration: none;
    font-size: var(--crm-text-xs);
    overflow-wrap: anywhere;
  }
  .month .appointments {
    gap: 3px;
  }
  .month .appointment {
    flex-direction: row;
    align-items: center;
    gap: 6px;
    padding: 3px 6px;
    height: 26px;
    min-width: 0;
    overflow: hidden;
    white-space: nowrap;
  }
  .month .event-time {
    flex: none;
    white-space: nowrap;
    font-size: var(--crm-text-xs);
  }
  .month .appointment strong {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: var(--crm-text-xs);
  }
  .appointment:hover {
    filter: brightness(0.97);
  }
  .event-legend {
    display: flex;
    gap: var(--crm-space-3);
    font-size: var(--crm-text-xs);
  }
  .event-legend span {
    display: flex;
    align-items: center;
    gap: var(--crm-space-1);
  }
  .contact-key {
    color: var(--crm-info);
  }
  .company-key {
    color: var(--crm-calendar-external);
  }
  .appointment strong :global(svg) {
    display: inline-block;
    vertical-align: -1px;
    margin-right: var(--crm-space-1);
  }
  .appointment.unlinked {
    background: var(--crm-surface-subtle);
    border-color: var(--crm-control-border);
    border-left-color: var(--crm-text-muted);
    color: var(--crm-text);
  }
  .appointment.company {
    background: var(--crm-calendar-external-bg);
    border-color: var(--crm-calendar-external-bg);
    border-left-color: var(--crm-calendar-external);
    color: var(--crm-calendar-external);
  }
  .event-time {
    display: flex;
    justify-content: space-between;
    gap: 5px;
    flex-wrap: wrap;
    font-size: var(--crm-text-xs);
  }
  .appointment strong {
    font-size: var(--crm-text-sm);
  }

  .calendar-message {
    padding: 10px var(--crm-space-6);
    color: var(--crm-text-muted);
    font-size: var(--crm-text-sm);
  }
  .appointment:focus-visible,
  header button:focus-visible {
    outline: 2px solid var(--crm-focus);
    outline-offset: 2px;
  }
  .period-controls {
    display: flex;
    gap: 0;
    border: 1px solid var(--crm-border);
    border-radius: var(--crm-button-radius);
    overflow: hidden;
    background: var(--crm-surface);
  }
  .period-controls .v2-btn {
    min-width: 34px;
    min-height: 36px;
    padding-inline: 10px;
    border: 0;
    border-radius: 0;
    font-size: var(--crm-text-xs);
  }
  .period-heading {
    flex: 1;
    min-width: 160px;
  }
  .calendar-zone {
    font-size: var(--crm-text-xs);
    color: var(--crm-text-muted);
  }
  .jump-date {
    width: 142px;
    min-height: 36px;
    font-size: var(--crm-text-xs);
  }
  .calendar-toolbar {
    gap: 10px;
    padding-inline: var(--crm-page-gutter);
    padding-block: 8px;
  }
  .views {
    flex-wrap: nowrap;
    gap: 2px;
    padding: 3px;
    border: 1px solid var(--crm-border);
    border-radius: var(--crm-radius-md);
    background: var(--crm-surface);
  }
  .views .v2-btn {
    border: 0;
    min-height: 30px;
    padding-inline: 10px;
    font-size: var(--crm-text-xs);
  }
  .calendar-meta {
    padding: 0 var(--crm-page-gutter) 4px;
  }
  .month-weekdays {
    position: sticky;
    top: 0;
    z-index: 3;
    display: grid;
    grid-template-columns: repeat(7, minmax(0, 1fr));
    background: var(--crm-surface-subtle);
    height: 36px;
    align-items: center;
    text-align: center;
    color: var(--crm-text-muted);
    font-size: var(--crm-text-xs);
    border-bottom: 1px solid var(--crm-border);
  }
  .agenda-day {
    display: grid;
    grid-template-columns: 60px minmax(0, 1fr);
    gap: 16px;
    padding: 16px;
    border-bottom: 1px solid var(--crm-border-soft);
  }
  .agenda-date {
    display: flex;
    flex-direction: column;
    align-items: center;
    align-self: start;
    gap: 2px;
    padding: 8px;
    font-size: var(--crm-text-xs);
    color: var(--crm-text-muted);
    border-radius: var(--crm-radius-md);
  }
  .agenda-date strong {
    font-size: var(--crm-text-xl);
    color: var(--crm-text);
  }
  .agenda-date.is-today {
    background: var(--crm-action-bg);
    color: var(--crm-primary-text);
  }
  .agenda-date.is-today strong {
    color: inherit;
  }
  .agenda-events {
    display: grid;
    gap: 8px;
  }
  .agenda-events .appointment {
    padding: 12px;
  }
  .agenda-empty {
    text-align: center;
    padding: 48px 16px;
    color: var(--crm-text-muted);
  }
  @media (max-width: 1100px) {
    .month .appointment {
      flex-direction: column;
      align-items: flex-start;
      gap: 2px;
      height: auto;
      min-height: 44px;
      padding: 5px;
    }
    .month .appointment strong {
      max-width: 100%;
    }
  }
  @media (max-width: 700px) {
    .calendar-scroll {
      margin: var(--crm-space-2) var(--crm-space-3) var(--crm-space-4);
    }
    .event-legend {
      order: 3;
      flex-basis: 100%;
    }
    .period-heading {
      order: -1;
      flex-basis: 100%;
    }
    .jump-date {
      flex: 1;
      min-width: 120px;
    }
    .views {
      margin-left: 0;
      width: 100%;
    }
    .views .v2-btn {
      flex: 1;
      min-height: 40px;
    }
    .calendar-grid,
    .month-weekdays {
      min-width: 560px;
    }
    .calendar-meta {
      padding-inline: 12px;
    }
    .calendar-toolbar {
      padding-inline: 12px;
      gap: 8px;
    }
    .agenda-day {
      grid-template-columns: 44px minmax(0, 1fr);
      gap: 8px;
      padding: 12px;
    }
  }
</style>
