<script>
  import CreateAppointment from '$lib/v2/components/CreateAppointment.svelte';
  let { data } = $props();
  import EventDetails from '$lib/v2/components/EventDetails.svelte';
  /** @type {EventDetails} */
  let details;
  import { onMount, tick } from 'svelte';
  import { resolve } from '$app/paths';
  import { ChevronLeft, ChevronRight } from '@lucide/svelte';
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
        if (scroller) scroller.scrollTop = mode === 'month' ? 0 : 8 * 120;
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
    selected = new Date();
    ready = true;
  });
  $effect(() => {
    if (!ready) return;
    const first = days[0],
      last = days[days.length - 1];
    const end = new Date(last.getFullYear(), last.getMonth(), last.getDate() + 1);
    const query = new URLSearchParams({ start: first.toISOString(), end: end.toISOString() });
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
        if (!controller.signal.aborted) failure = 'Could not load appointments. Please try again.';
      })
      .finally(() => {
        if (!controller.signal.aborted) busy = false;
      });
    return () => controller.abort();
  });
</script>

{#snippet eventCard(event)}
  <button
    type="button"
    class="appointment"
    class:company={event.type === 'company'}
    onclick={(click) => details.open(event, click.currentTarget)}
  >
    <div class="event-time">
      {new Date(event.start).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}
    </div>
    <strong>{event.title}</strong>
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
        {#each hours as hour}<div class="hour-label" style={`top:${hour * 120}px`}>
            {hour % 12 || 12}
            {hour < 12 ? 'AM' : 'PM'}
          </div>{/each}
      </div>
      {#each days as day (dateKey(day))}
        <section class="time-day" aria-label={day.toDateString()}>
          {#each hours as hour}<div
              class="hour-line"
              style={`top:${hour * 120}px`}
              aria-hidden="true"
            ></div>{/each}
          {#each timedCards(grouped.get(dateKey(day)) ?? []) as item (item.event.id)}
            <div
              class="timed-card"
              style={`height:${Math.max(28, item.duration * 2 - 4)}px;top:${item.minute * 2}px;left:calc(${(item.lane / item.lanes) * 100}% + 3px);width:calc(${100 / item.lanes}% - 6px)`}
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
    height: 3000px;
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
    height: 3000px;
    border-right: 1px solid var(--v2-line);
    min-width: 0;
  }
  .hour-line {
    position: absolute;
    width: 100%;
    height: 120px;
    border-top: 1px solid var(--v2-line);
    pointer-events: none;
  }
  .hour-line::after {
    content: '';
    position: absolute;
    top: 59px;
    width: 100%;
    border-top: 1px dotted var(--v2-line-soft);
  }
  .timed-card {
    position: absolute;
    height: 116px;
    min-width: 0;
  }
  .timed-card .appointment {
    height: 100%;
    box-sizing: border-box;
    overflow: auto;
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
  .appointment:hover {
    filter: brightness(0.97);
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
