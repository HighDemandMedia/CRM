<script>
  import CreateAppointment from '$lib/v2/components/CreateAppointment.svelte';
  let { data } = $props();
  import EventDetails from '$lib/v2/components/EventDetails.svelte';
  /** @type {EventDetails} */
  let details;
  import { onMount, tick } from 'svelte';
  import { resolve } from '$app/paths';
  import { page } from '$app/state';
  import { ChevronLeft, ChevronRight, Building2, UserRound } from '@lucide/svelte';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import { calendarDays, dateKey, shiftDate, timedCards } from '$lib/v2/calendar.js';
  let selected = $state(new Date());
  let view = $state('month');
  let ready = $state(false);
  /** @type {HTMLDivElement} */
  let scroller;
  const hours = Array.from({ length: 24 }, (_, hour) => hour);
  $effect(() => {
    const mode = view;
    if (ready)
      void tick().then(() => {
        if (scroller) scroller.scrollTop = mode === 'month' ? 0 : 8 * 60;
      });
  });
  let events = $state(/** @type {any[]} */ ([]));
  let busy = $state(true);
  let failure = $state('');
  let refresh = $state(0);
  const days = $derived(calendarDays(selected, view));
  const title = $derived(
    view === 'day'
      ? selected.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })
      : view === 'week'
        ? `${days[0].toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} – ${days[6].toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}`
        : selected.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
  );
  const grouped = $derived.by(() => {
    const result = new Map();
    for (const event of events) {
      const key = dateKey(new Date(event.start));
      if (!result.has(key)) result.set(key, []);
      result.get(key).push(event);
    }
    return result;
  });
  onMount(() => {
    const date = page.url.searchParams.get('date');
    const requested = /^\d{4}-\d{2}-\d{2}$/.test(date || '') ? new Date(`${date}T12:00:00`) : null;
    selected = requested && Number.isFinite(requested.getTime()) ? requested : new Date();
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
    const controller = new AbortController();
    busy = true;
    failure = '';
    events = [];
    fetch(`${resolve('/calendar/events')}?${query}`, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error('Could not load appointments.');
        const result = await response.json();
        if (!controller.signal.aborted) events = result.events;
      })
      .catch((err) => {
        if (!controller.signal.aborted)
          failure = 'Could not load appointments. Please try again.';
      })
      .finally(() => {
        if (!controller.signal.aborted) busy = false;
      });
    return () => controller.abort();
  });
</script>

{#snippet eventCard(event)}
    {@const attendeeType = event.attendee?.type ?? event.type}
    {@const typeLabel =
      attendeeType === 'company' ? 'Company' : attendeeType === 'contact' ? 'Contact' : 'Event'}
    <button
      type="button"
      title={`${typeLabel} · ${event.title} · ${new Date(event.start).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}`}
      class="appointment"
      class:company={attendeeType === 'company'}
      class:unlinked={attendeeType !== 'company' && attendeeType !== 'contact'}
      onclick={(click) => details.open(event, click.currentTarget)}
    >
      <div class="event-time">
        {new Date(event.start).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}
      </div>
      <strong
        >{#if attendeeType === 'company'}<Building2
            size={12}
            aria-label="Company"
          />{:else if attendeeType === 'contact'}<UserRound
            size={12}
            aria-label="Contact"
          />{/if}{event.title}</strong
      >
    </button>
{/snippet}

<EventDetails bind:this={details} onChanged={() => refresh++} />
<PageHeader title="Calendar" />
<div class="calendar-toolbar">
  <button class="v2-btn" onclick={() => (selected = new Date())}>Today</button>
  <button
    class="v2-btn"
    aria-label="Previous period"
    onclick={() => (selected = shiftDate(selected, view, -1))}><ChevronLeft size={16} /></button
  >
  <button
    class="v2-btn"
    aria-label="Next period"
    onclick={() => (selected = shiftDate(selected, view, 1))}><ChevronRight size={16} /></button
  >
  <h2>{title}</h2>
  <div class="event-legend" aria-label="Event types">
    <span class="contact-key"><UserRound size={13} />Contacts</span><span class="company-key"
      ><Building2 size={13} />Companies</span
    >
  </div>
  <CreateAppointment
    hosts={data.hosts}
    defaultHost={data.defaultHost}
    {selected}
    onCreated={() => refresh++}
  />
  <div class="views" aria-label="Calendar view">
    {#each ['day', 'week', 'month'] as mode}<button
        class="v2-btn"
        class:active={view === mode}
        aria-pressed={view === mode}
        onclick={() => (view = mode)}>{mode[0].toUpperCase() + mode.slice(1)}</button
      >{/each}
  </div>
</div>
{#if failure}<div class="calendar-message" role="alert">
    {failure} <button class="v2-btn" onclick={() => refresh++}>Retry</button>
  </div>
{:else if busy}<div class="calendar-message" role="status">Loading appointments…</div>{/if}
<div
  class="calendar-scroll"
  bind:this={scroller}
  aria-busy={busy}
  onscroll={() => details?.close()}
>
  {#if view === 'month'}
    <div class="calendar-grid month">
      {#each days as day (dateKey(day))}
        <section
          class="day"
          class:outside={view === 'month' && day.getMonth() !== selected.getMonth()}
          aria-label={day.toDateString()}
        >
          <header>
            <span>{day.toLocaleDateString('en-US', { weekday: 'short' })}</span><button
              class:today={dateKey(day) === dateKey(new Date())}
              aria-label={`View ${day.toDateString()}`}
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
                  No appointments
                </p>{/if}{/each}
          </div>
        </section>
      {/each}
    </div>
  {:else}
    <div class="time-grid" style={`--day-count:${days.length}`}>
      <div class="time-corner">Time</div>
      {#each days as day (dateKey(day))}
        <header class="time-header">
          <span>{day.toLocaleDateString('en-US', { weekday: 'short' })}</span>
          <button
            class:today={dateKey(day) === dateKey(new Date())}
            aria-label={`View ${day.toDateString()}`}
            onclick={() => {
              selected = day;
              view = 'day';
            }}>{day.getDate()}</button
          >
        </header>
      {/each}
      <div class="hour-labels">
        {#each hours as hour}<div class="hour-label" style={`top:${hour * 60}px`}>
            {hour % 12 || 12}
            {hour < 12 ? 'AM' : 'PM'}
          </div>{/each}
      </div>
      {#each days as day (dateKey(day))}
        <section class="time-day" aria-label={day.toDateString()}>
          {#each hours as hour}<div
              class="hour-line"
              style={`top:${hour * 60}px`}
              aria-hidden="true"
            ></div>{/each}
          {#each timedCards(grouped.get(dateKey(day)) ?? []) as item (item.event.id)}
            <div
              class="timed-card"
              style={`height:${Math.max(14, item.duration - 2)}px;top:${item.minute}px;left:calc(${(item.lane / item.lanes) * 100}% + 3px);width:calc(${100 / item.lanes}% - 6px)`}
            >
              {@render eventCard(item.event)}
            </div>
          {/each}
        </section>
      {/each}
    </div>
  {/if}
</div>

<style>
  .time-grid {
    display: grid;
    grid-template-columns: 64px repeat(var(--day-count), minmax(160px, 1fr));
    isolation: isolate;
  }
  .time-corner,
  .time-header {
    position: sticky;
    top: 0;
    z-index: 3;
    background: var(--v2-bg, white);
    min-height: 50px;
    margin: 0;
    padding: 8px;
    border-bottom: 1px solid var(--v2-line);
  }
  .time-corner {
    left: 0;
    z-index: 4;
    color: var(--v2-slate);
    font-size: 11px;
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
    background: var(--v2-bg, white);
    height: 1440px;
  }
  .hour-label {
    position: absolute;
    right: 8px;
    font-size: 11px;
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

  .calendar-toolbar {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 14px 22px;
    flex-wrap: wrap;
    border-bottom: 1px solid var(--v2-line);
  }
  h2 {
    font-size: 18px;
    margin: 0 12px;
    font-weight: 600;
  }
  .views {
    margin-left: auto;
    display: flex;
    gap: 4px;
  }
  .views .active {
    background: var(--v2-ink);
    color: white;
  }
  .calendar-scroll {
    flex: 1;
    min-height: 0;
    overflow: auto;
  }
  .calendar-grid {
    display: grid;
    grid-template-columns: repeat(7, minmax(155px, 1fr));
    min-height: 100%;
  }

  .day {
    min-width: 0;
    border-right: 1px solid var(--v2-line);
    border-bottom: 1px solid var(--v2-line);
    padding: 10px;
  }
  .month .day {
    min-height: 160px;
  }
  .outside {
    background: var(--v2-line-soft);
  }
  header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 10px;
    font-size: 12px;
    color: var(--v2-slate);
  }
  header button {
    border: 0;
    background: transparent;
    color: inherit;
    border-radius: 50%;
    width: 28px;
    height: 28px;
    cursor: pointer;
  }
  header button.today {
    background: #2563eb;
    color: white;
  }
  .appointments {
    display: grid;
    align-content: start;
    gap: 8px;
  }
  .month .appointments {
    max-height: 210px;
    overflow-y: auto;
  }
  .appointment {
    width: 100%;
    text-align: left;
    cursor: pointer;
    font-family: inherit;
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 9px;
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-left: 3px solid #3b82f6;
    border-radius: 6px;
    color: #1e3a5f;
    text-decoration: none;
    font-size: 12px;
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
    font-size: 10px;
  }
  .month .appointment strong {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 12px;
  }
  .appointment:hover {
    filter: brightness(0.97);
  }
  .event-legend {
    display: flex;
    gap: 12px;
    font-size: 12px;
  }
  .event-legend span {
    display: flex;
    align-items: center;
    gap: 4px;
  }
  .contact-key {
    color: #2563eb;
  }
  .company-key {
    color: #7c3aed;
  }
  .appointment strong :global(svg) {
    display: inline-block;
    vertical-align: -1px;
    margin-right: 4px;
  }
  .appointment.unlinked {
    background: #f3f4f6;
    border-color: #d1d5db;
    border-left-color: #6b7280;
    color: #374151;
  }
  .appointment.company {
    background: #f5f3ff;
    border-color: #ddd6fe;
    border-left-color: #8b5cf6;
    color: #4c1d95;
  }
  .event-time {
    display: flex;
    justify-content: space-between;
    gap: 5px;
    flex-wrap: wrap;
    font-size: 10px;
  }
  .appointment strong {
    font-size: 13px;
  }

  .calendar-message {
    padding: 10px 22px;
  }
</style>
