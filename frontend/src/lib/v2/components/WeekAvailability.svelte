<script>
  import { SvelteDate } from 'svelte/reactivity';

  import { useI18n } from '$lib/i18n/context.js';
  const { ui, locale } = useI18n();

  import { resolve } from '$app/paths';
  import { dateKey, formatClockTime } from '$lib/v2/calendar.js';
  import { onMount, tick, untrack } from 'svelte';
  import { ChevronLeft, ChevronRight } from '@lucide/svelte';
  let view = $state('week');
  onMount(() => {
    if (window.matchMedia('(max-width: 700px)').matches) view = 'day';
  });
  /** @type {{host:string,date:string,start:string,end:string,blocked?:boolean,disabled?:boolean,conflicting?:boolean,refresh?:number,visible?:boolean}} */
  let {
    host,
    date = $bindable(''),
    start = $bindable('09:00'),
    end = $bindable('10:00'),
    blocked = $bindable(true),
    conflicting = $bindable(false),
    refresh = 0,
    disabled = false,
    visible = true
  } = $props();
  let slots = $state(
    /** @type {Array<{starts_at:string,ends_at:string,title?:string|null}>} */ ([])
  );
  let loading = $state(true),
    error = $state(''),
    retry = $state(0);
  let scroll = $state();
  const minutes = (value) => {
    const [h, m] = value.split(':').map(Number);
    return h * 60 + m;
  };
  const time = (value) =>
    `${String(Math.floor(value / 60)).padStart(2, '0')}:${String(value % 60).padStart(2, '0')}`;
  const week = $derived.by(() => {
    const first = new SvelteDate(`${date}T12:00:00`);
    if (!Number.isFinite(first.getTime())) return '';
    first.setDate(first.getDate() - first.getDay());
    return dateKey(first);
  });
  const days = $derived.by(() =>
    Array.from({ length: 7 }, (_, i) => {
      const d = new SvelteDate(`${week}T12:00:00`);
      d.setDate(d.getDate() + i);
      return d;
    })
  );
  const visibleDays = $derived(view === 'day' ? days.filter((day) => dateKey(day) === date) : days);
  let focusedSlot = $state(0);
  $effect(() => {
    const dayIndex = Math.max(
      0,
      visibleDays.findIndex((day) => dateKey(day) === date)
    );
    const minute = minutes(start);
    focusedSlot =
      dayIndex * 48 +
      (Number.isFinite(minute) ? Math.min(47, Math.max(0, Math.floor(minute / 30))) : 18);
  });
  function navigateSlot(event, index) {
    const offsets = { ArrowUp: -1, ArrowDown: 1, ArrowLeft: -48, ArrowRight: 48 };
    let next;
    if (event.key === 'Home') next = Math.floor(index / 48) * 48;
    else if (event.key === 'End') next = Math.floor(index / 48) * 48 + 47;
    else if (event.key in offsets) next = index + offsets[event.key];
    else return;
    event.preventDefault();
    focusedSlot = Math.max(0, Math.min(visibleDays.length * 48 - 1, next));
    const grid = event.currentTarget.closest('.calendar-grid');
    tick().then(() => grid?.querySelector(`[data-slot-index="${focusedSlot}"]`)?.focus());
  }
  const conflict = $derived(
    slots.some(
      (s) =>
        Date.parse(s.starts_at) < new Date(`${date}T${end}`).getTime() &&
        Date.parse(s.ends_at) > new Date(`${date}T${start}`).getTime()
    )
  );
  $effect(() => {
    const nextBlocked = loading || !!error || !host || !week || !start || !end || end <= start;
    if (untrack(() => blocked) !== nextBlocked) blocked = nextBlocked;
    if (untrack(() => conflicting) !== conflict) conflicting = conflict;
  });
  $effect(() => {
    const selectedHost = host,
      selectedWeek = week;
    retry;
    refresh;
    if (!selectedHost || !selectedWeek) {
      slots = [];
      loading = false;
      return;
    }
    const first = new Date(`${selectedWeek}T00:00:00`),
      last = new SvelteDate(first);
    last.setDate(last.getDate() + 7);
    const controller = new AbortController();
    loading = true;
    error = '';
    slots = [];
    fetch(
      `${resolve('/calendar/availability')}?${new URLSearchParams({ host: selectedHost, start: first.toISOString(), end: last.toISOString() })}`,
      { signal: controller.signal }
    )
      .then(async (r) => {
        if (!r.ok) throw new Error();
        const result = await r.json();
        if (!controller.signal.aborted) slots = result.busy;
      })
      .catch(() => {
        if (!controller.signal.aborted) error = 'Could not load availability.';
      })
      .finally(() => {
        if (!controller.signal.aborted) loading = false;
      });
    return () => controller.abort();
  });
  $effect(() => {
    const target = scroll;
    if (target && visible) {
      const initialScroll = untrack(() => Math.max(0, minutes(start) - 60));
      tick().then(() => {
        target.scrollTop = initialScroll;
      });
    }
  });
  function moveWeek(offset) {
    const d = new SvelteDate(`${date}T12:00:00`);
    d.setDate(d.getDate() + offset);
    date = dateKey(d);
  }
  function choose(day, minute) {
    if (disabled || loading || error || !host) return;
    const duration = Math.max(15, minutes(end) - minutes(start) || 60);
    const finish = Math.min(1439, minute + duration);
    const key = dateKey(day);
    date = key;
    start = time(minute);
    end = time(finish);
  }
  function blocks(day) {
    const from = new Date(`${dateKey(day)}T00:00:00`).getTime(),
      until = new SvelteDate(from);
    until.setDate(until.getDate() + 1);
    return slots
      .filter((s) => Date.parse(s.starts_at) < until.getTime() && Date.parse(s.ends_at) > from)
      .map((s) => {
        const a = new Date(Math.max(from, Date.parse(s.starts_at))),
          b = new Date(Math.min(until.getTime(), Date.parse(s.ends_at)));
        const top = a.getHours() * 60 + a.getMinutes(),
          bottom = b.getTime() === until.getTime() ? 1440 : b.getHours() * 60 + b.getMinutes();
        return {
          slot: s,
          title: s.title || 'Busy',
          top,
          height: Math.max(4, bottom - top),
          label: `${a.toLocaleTimeString(locale(), { hour: 'numeric', minute: '2-digit', hour12: true })} – ${b.toLocaleTimeString(locale(), { hour: 'numeric', minute: '2-digit', hour12: true })}`
        };
      });
  }
</script>

<section class="week-picker" aria-label={ui('Host weekly availability')}>
  {#if !week}
    <p class="status" role="status">{ui('Select a date to see availability.')}</p>
  {:else}
    <header>
      <div class="week-nav">
        <button
          type="button"
          class="v2-btn"
          aria-label={ui(view === 'day' ? 'Previous day' : 'Previous week')}
          {disabled}
          onclick={() => moveWeek(view === 'day' ? -1 : -7)}><ChevronLeft size={16} /></button
        ><strong
          >{view === 'day'
            ? new Date(`${date}T12:00:00`).toLocaleDateString(locale(), {
                month: 'short',
                day: 'numeric',
                year: 'numeric'
              })
            : `${days[0]?.toLocaleDateString(locale(), { month: 'short', day: 'numeric' })} – ${days[6]?.toLocaleDateString(locale(), { month: 'short', day: 'numeric' })}`}</strong
        ><button
          type="button"
          class="v2-btn"
          aria-label={ui(view === 'day' ? 'Next day' : 'Next week')}
          {disabled}
          onclick={() => moveWeek(view === 'day' ? 1 : 7)}><ChevronRight size={16} /></button
        ><button
          type="button"
          class="v2-btn"
          {disabled}
          onclick={() => (date = dateKey(new Date()))}>{ui('Today')}</button
        >
      </div>
      <div class="availability-views" aria-label={ui('Availability view')}>
        {#each ['day', 'week'] as mode (mode)}<button
            type="button"
            class="v2-btn v2-btn-sm"
            class:v2-btn-primary={view === mode}
            aria-pressed={view === mode}
            onclick={() => (view = mode)}>{ui(mode === 'day' ? 'Day' : 'Week')}</button
          >{/each}
      </div>
      <div class="legend">
        <span><i class="busy-key"></i>{ui('Busy')}</span><span
          ><i class="selected-key"></i>{ui('Selected')}</span
        >
      </div>
    </header>
    <div class="status" aria-live="polite">
      {#if loading}{ui('Checking availability…')}{:else if error}{error}
        <button type="button" onclick={() => retry++}>{ui('Retry')}</button>{:else if !host}{ui(
          'Select a Host to see availability.'
        )}{:else if conflict}<span role="alert"
          >{ui('This host already has an event at this time.')}</span
        >{/if}
    </div>
    <div class="week-scroll" bind:this={scroll}>
      <div class="calendar-grid" style={`--days:${visibleDays.length}`}>
        <div class="day-head">
          <span></span>{#each visibleDays as day, dayIndex (dayIndex)}<div
              class:chosen={dateKey(day) === date}
            >
              {day.toLocaleDateString(locale(), { weekday: 'short' })}<b>{day.getDate()}</b>
            </div>{/each}
        </div>
        <div class="hours">
          <div class="ruler">
            {#each Array.from({ length: 24 }, (_, i) => i) as h (h)}<span style:top={`${h * 60}px`}
                >{h % 12 || 12} {h < 12 ? 'AM' : 'PM'}</span
              >{/each}
          </div>
          {#each visibleDays as day, dayIndex (dayIndex)}
            <div class="day">
              {#each Array.from({ length: 48 }, (_, i) => i * 30) as minute (minute)}
                <button
                  class="slot"
                  data-slot-index={dayIndex * 48 + minute / 30}
                  tabindex={focusedSlot === dayIndex * 48 + minute / 30 ? 0 : -1}
                  onkeydown={(event) => navigateSlot(event, dayIndex * 48 + minute / 30)}
                  type="button"
                  disabled={disabled || loading || !!error || !host}
                  aria-label={`Select ${day.toLocaleDateString(locale())} at ${formatClockTime(time(minute), locale())}`}
                  style:top={`${minute}px`}
                  onclick={() => choose(day, minute)}
                  ondragover={(e) => e.preventDefault()}
                  ondrop={(e) => {
                    e.preventDefault();
                    if (e.dataTransfer?.getData('text/plain') === 'crm-selected-time')
                      choose(day, minute);
                  }}
                ></button>
              {/each}
              {#each blocks(day) as block (block.slot)}<div
                  class="busy-block"
                  style:top={`${block.top}px`}
                  style:height={`${block.height}px`}
                  title={`${block.title} · ${block.label}`}
                >
                  {block.title}
                </div>{/each}
              {#if dateKey(day) === date && end > start}<div
                  class="selection"
                  class:conflict
                  draggable={!disabled}
                  ondragstart={(e) => e.dataTransfer?.setData('text/plain', 'crm-selected-time')}
                  role="img"
                  aria-label={`Selected ${formatClockTime(start, locale())} – ${formatClockTime(end, locale())}`}
                  style:top={`${minutes(start)}px`}
                  style:height={`${minutes(end) - minutes(start)}px`}
                >
                  <b>{formatClockTime(start, locale())}</b><span
                    >{formatClockTime(end, locale())}</span
                  >
                </div>{/if}
            </div>
          {/each}
        </div>
      </div>
    </div>
  {/if}
</section>

<style>
  .week-picker {
    min-width: 0;
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden;
    background: var(--crm-surface);
  }
  header {
    padding: var(--crm-space-4) var(--crm-space-5) 0;
  }
  .week-nav {
    display: flex;
    align-items: center;
    gap: var(--crm-space-2);
  }
  .week-nav strong {
    flex: 1;
    font-size: var(--crm-text-sm);
  }
  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: var(--crm-space-4);
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
    margin-top: var(--crm-space-3);
  }
  .legend span {
    display: flex;
    align-items: center;
    gap: 5px;
  }
  i {
    width: 9px;
    height: 9px;
    border-radius: var(--crm-radius-sm);
  }
  .busy-key {
    background: var(--crm-control-border);
  }
  .selected-key {
    background: var(--crm-info);
  }
  .status {
    min-height: 30px;
    padding: 6px var(--crm-space-5);
    font-size: var(--crm-text-xs);
    color: var(--crm-text-muted);
  }
  .status :global([role='alert']) {
    color: var(--crm-danger);
  }
  .week-scroll {
    overflow: auto;
    flex: 1;
    min-height: 0;
  }
  .calendar-grid {
    min-width: 0;
  }
  .day-head {
    display: grid;
    grid-template-columns: 48px repeat(var(--days), minmax(0, 1fr));
    position: sticky;
    top: 0;
    z-index: 4;
    background: var(--crm-surface);
    border-bottom: 1px solid var(--crm-border);
    height: 58px;
  }
  .day-head div {
    text-align: center;
    font-size: var(--crm-text-xs);
    color: var(--crm-text-muted);
    padding: 6px;
  }
  .day-head b {
    display: block;
    font-size: var(--crm-text-base);
    margin-top: 3px;
  }
  .day-head .chosen {
    color: var(--crm-info);
    background: var(--crm-info-bg);
  }
  .hours {
    display: grid;
    grid-template-columns: 48px repeat(var(--days), minmax(0, 1fr));
    height: 1440px;
  }
  .ruler {
    position: relative;
  }
  .ruler span {
    position: absolute;
    right: 8px;
    font-size: var(--crm-text-xs);
    color: var(--crm-text-muted);
  }
  .day {
    position: relative;
    border-left: 1px solid var(--crm-border);
  }
  .slot {
    position: absolute;
    left: 0;
    width: 100%;
    height: 30px;
    border: 0;
    border-top: 1px solid var(--crm-surface-secondary);
    background: transparent;
    cursor: pointer;
  }
  .slot:nth-child(odd) {
    border-top-color: var(--crm-border);
  }
  .slot:hover:not(:disabled),
  .slot:focus-visible {
    background: var(--crm-info-bg);
    outline: 2px solid var(--crm-focus);
    outline-offset: -2px;
  }
  .busy-block,
  .selection {
    position: absolute;
    left: 3px;
    right: 3px;
    border-radius: var(--crm-radius-sm);
    padding: var(--crm-space-1) 5px;
    box-sizing: border-box;
    font-size: var(--crm-text-xs);
    overflow: hidden;
  }
  .busy-block {
    background: var(--crm-border);
    border-left: 3px solid var(--crm-text-muted);
    color: var(--crm-text-muted);
    pointer-events: none;
  }
  .selection {
    background: var(--crm-info-bg);
    border: 1px solid var(--crm-info);
    border-left: 3px solid var(--crm-info);
    color: var(--crm-info);
    cursor: grab;
    z-index: 2;
  }
  .selection b,
  .selection span {
    display: block;
    white-space: nowrap;
    font-size: 10px;
    line-height: 1.3;
  }
  .selection.conflict {
    background: var(--crm-danger-bg);
    border-color: var(--crm-danger);
    color: var(--crm-danger);
  }
  .availability-views {
    display: flex;
    gap: 4px;
    align-items: center;
  }
  .week-nav .v2-btn {
    padding-inline: 8px;
    min-width: 32px;
  }
  header {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: center;
    gap: 8px 12px;
    padding: 12px 14px 8px;
  }
  .week-nav {
    gap: 4px;
  }
  .week-nav .v2-btn {
    min-height: 32px;
    font-size: var(--crm-text-xs);
  }
  .status:empty {
    display: none;
  }
  @media (max-width: 480px) {
    header {
      grid-template-columns: 1fr;
    }
    .availability-views {
      grid-row: 2;
    }
  }
  .week-nav strong {
    text-align: center;
    font-size: var(--crm-text-xs);
  }
  .legend {
    grid-column: 1 / -1;
    margin-top: 0;
    gap: 12px;
  }
</style>
