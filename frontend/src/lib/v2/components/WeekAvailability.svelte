<script>
  import { resolve } from '$app/paths';
  import { dateKey } from '$lib/v2/calendar.js';
  import { tick } from 'svelte';
  /** @type {{host:string,date:string,start:string,end:string,blocked?:boolean,disabled?:boolean,conflicting?:boolean,refresh?:number}} */
  let {
    host,
    date = $bindable(''),
    start = $bindable('09:00'),
    end = $bindable('10:00'),
    blocked = $bindable(true),
    conflicting = $bindable(false),
    refresh = 0,
    disabled = false
  } = $props();
  let slots = $state(/** @type {Array<{starts_at:string,ends_at:string,title?:string|null}>} */ ([]));
  let loading = $state(true),
    error = $state(''),
    retry = $state(0);
  let scroll;
  let initialized = false;
  const minutes = (value) => {
    const [h, m] = value.split(':').map(Number);
    return h * 60 + m;
  };
  const time = (value) =>
    `${String(Math.floor(value / 60)).padStart(2, '0')}:${String(value % 60).padStart(2, '0')}`;
  const week = $derived.by(() => {
    const first = new Date(`${date}T12:00:00`);
    if (!Number.isFinite(first.getTime())) return '';
    first.setDate(first.getDate() - first.getDay());
    return dateKey(first);
  });
  const days = $derived.by(() =>
    Array.from({ length: 7 }, (_, i) => {
      const d = new Date(`${week}T12:00:00`);
      d.setDate(d.getDate() + i);
      return d;
    })
  );
  const conflict = $derived(
    slots.some(
      (s) =>
        Date.parse(s.starts_at) < new Date(`${date}T${end}`).getTime() &&
        Date.parse(s.ends_at) > new Date(`${date}T${start}`).getTime()
    )
  );
  $effect(() => {
    blocked = loading || !!error || !host || !week || !start || !end || end <= start;
    conflicting = conflict;
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
      last = new Date(first);
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
    if (scroll && !initialized) {
      initialized = true;
      tick().then(() => {
        scroll.scrollTop = Math.max(0, minutes(start) - 60);
      });
    }
  });
  function moveWeek(offset) {
    const d = new Date(`${date}T12:00:00`);
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
      until = new Date(from);
    until.setDate(until.getDate() + 1);
    return slots
      .filter((s) => Date.parse(s.starts_at) < until.getTime() && Date.parse(s.ends_at) > from)
      .map((s) => {
        const a = new Date(Math.max(from, Date.parse(s.starts_at))),
          b = new Date(Math.min(until.getTime(), Date.parse(s.ends_at)));
        const top = a.getHours() * 60 + a.getMinutes(),
          bottom = b.getTime() === until.getTime() ? 1440 : b.getHours() * 60 + b.getMinutes();
        return {
          title: s.title || 'Busy',
          top,
          height: Math.max(4, bottom - top),
          label: `${a.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })} – ${b.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}`
        };
      });
  }
  const zone = Intl.DateTimeFormat().resolvedOptions().timeZone;
</script>

<section class="week-picker" aria-label="Host weekly availability">
  <header>
    <div class="week-nav">
      <button
        type="button"
        class="v2-btn"
        aria-label="Previous week"
        {disabled}
        onclick={() => moveWeek(-7)}>‹</button
      ><strong
        >{days[0]?.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} – {days[6]?.toLocaleDateString(
          'en-US',
          { month: 'short', day: 'numeric', year: 'numeric' }
        )}</strong
      ><button
        type="button"
        class="v2-btn"
        aria-label="Next week"
        {disabled}
        onclick={() => moveWeek(7)}>›</button
      ><button type="button" class="v2-btn" {disabled} onclick={() => (date = dateKey(new Date()))}
        >Today</button
      >
    </div>
    <div class="legend">
      <span><i class="busy-key"></i>Busy</span><span><i class="selected-key"></i>Selected</span
      ><span>{zone}</span>
    </div>
  </header>
  <div class="status" aria-live="polite">
    {#if loading}Checking availability…{:else if error}{error}
      <button type="button" onclick={() => retry++}>Retry</button>{:else if !host}Select a Host to
      see availability.{:else if conflict}<span role="alert"
        >This host already has an event at this time.</span
      >{/if}
  </div>
  <div class="week-scroll" bind:this={scroll}>
    <div class="calendar-grid">
      <div class="day-head">
        <span></span>{#each days as day}<div class:chosen={dateKey(day) === date}>
            {day.toLocaleDateString('en-US', { weekday: 'short' })}<b>{day.getDate()}</b>
          </div>{/each}
      </div>
      <div class="hours">
        <div class="ruler">
          {#each Array.from({ length: 24 }, (_, i) => i) as h}<span style:top={`${h * 60}px`}
              >{h % 12 || 12} {h < 12 ? 'AM' : 'PM'}</span
            >{/each}
        </div>
        {#each days as day}
          <div class="day">
            {#each Array.from({ length: 48 }, (_, i) => i * 30) as minute}
              <button
                class="slot"
                type="button"
                disabled={disabled || loading || !!error || !host}
                aria-label={`Select ${day.toLocaleDateString('en-US')} at ${time(minute)}`}
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
            {#each blocks(day) as block}<div
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
                aria-label={`Selected ${start} to ${end}`}
                style:top={`${minutes(start)}px`}
                style:height={`${minutes(end) - minutes(start)}px`}
              >
                <b>{start}</b><span> – {end}</span>
              </div>{/if}
          </div>
        {/each}
      </div>
    </div>
  </div>
</section>

<style>
  .week-picker {
    min-width: 0;
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden;
    background: white;
  }
  header {
    padding: 16px 20px 0;
  }
  .week-nav {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .week-nav strong {
    flex: 1;
    font-size: 14px;
  }
  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    font-size: 11px;
    color: var(--v2-slate);
    margin-top: 12px;
  }
  .legend span {
    display: flex;
    align-items: center;
    gap: 5px;
  }
  .legend span:last-child {
    margin-left: auto;
  }
  i {
    width: 9px;
    height: 9px;
    border-radius: 3px;
  }
  .busy-key {
    background: #cbd5e1;
  }
  .selected-key {
    background: #3b82f6;
  }
  .status {
    min-height: 30px;
    padding: 6px 20px;
    font-size: 12px;
    color: #b42318;
  }
  .week-scroll {
    overflow: auto;
    flex: 1;
    min-height: 0;
  }
  .calendar-grid {
    min-width: 650px;
  }
  .day-head {
    display: grid;
    grid-template-columns: 58px repeat(7, minmax(0, 1fr));
    position: sticky;
    top: 0;
    z-index: 4;
    background: white;
    border-bottom: 1px solid #e2e8f0;
    height: 58px;
  }
  .day-head div {
    text-align: center;
    font-size: 11px;
    color: #64748b;
    padding: 6px;
  }
  .day-head b {
    display: block;
    font-size: 16px;
    margin-top: 3px;
  }
  .day-head .chosen {
    color: #2563eb;
    background: #eff6ff;
  }
  .hours {
    display: grid;
    grid-template-columns: 58px repeat(7, minmax(0, 1fr));
    height: 1440px;
  }
  .ruler {
    position: relative;
  }
  .ruler span {
    position: absolute;
    right: 8px;
    font-size: 10px;
    color: #64748b;
  }
  .day {
    position: relative;
    border-left: 1px solid #e2e8f0;
  }
  .slot {
    position: absolute;
    left: 0;
    width: 100%;
    height: 30px;
    border: 0;
    border-top: 1px solid #f1f5f9;
    background: transparent;
    cursor: pointer;
  }
  .slot:nth-child(odd) {
    border-top-color: #e2e8f0;
  }
  .slot:hover:not(:disabled),
  .slot:focus-visible {
    background: #eff6ff;
    outline: 2px solid #93c5fd;
    outline-offset: -2px;
  }
  .busy-block,
  .selection {
    position: absolute;
    left: 3px;
    right: 3px;
    border-radius: 5px;
    padding: 4px 5px;
    box-sizing: border-box;
    font-size: 11px;
    overflow: hidden;
  }
  .busy-block {
    background: #e2e8f0;
    border-left: 3px solid #94a3b8;
    color: #475569;
    pointer-events: none;
  }
  .selection {
    background: #dbeafe;
    border: 1px solid #60a5fa;
    border-left: 3px solid #2563eb;
    color: #1d4ed8;
    cursor: grab;
    z-index: 2;
  }
  .selection.conflict {
    background: #fee2e2;
    border-color: #ef4444;
    color: #b91c1c;
  }
</style>
