<script>
  import { resolve } from '$app/paths';
  /** @type {{host:string,date:string,start:string,end:string,active?:boolean,exclude?:string,blocked?:boolean}} */
  let { host, date, start, end, active = true, exclude = '', blocked = $bindable(true) } = $props();
  let slots = $state(/** @type {Array<{starts_at:string,ends_at:string}>} */ ([])),
    loading = $state(false),
    error = $state(''),
    retry = $state(0);
  const conflict = $derived(
    slots.some(
      (slot) =>
        Date.parse(slot.starts_at) < new Date(`${date}T${end}`).getTime() &&
        Date.parse(slot.ends_at) > new Date(`${date}T${start}`).getTime()
    )
  );
  $effect(() => {
    blocked = loading || !!error || conflict || !host || !date;
  });
  $effect(() => {
    if (!active || !host || !date) return;
    const first = new Date(`${date}T00:00:00`);
    if (!Number.isFinite(first.getTime())) return;
    const last = new Date(first);
    last.setDate(last.getDate() + 1);
    const query = new URLSearchParams({
      host,
      start: first.toISOString(),
      end: last.toISOString()
    });
    if (exclude) query.set('exclude', exclude);
    retry;
    const controller = new AbortController();
    loading = true;
    error = '';
    slots = [];
    fetch(`${resolve('/calendar/availability')}?${query}`, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error();
        const result = await response.json();
        if (!controller.signal.aborted) slots = result.busy;
      })
      .catch(() => {
        if (!controller.signal.aborted) error = 'Could not check availability.';
      })
      .finally(() => {
        if (!controller.signal.aborted) loading = false;
      });
    return () => controller.abort();
  });
  const time = (value) =>
    new Date(value).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
</script>

<div class="availability" aria-live="polite">
  {#if loading}<span>Checking availability…</span>
  {:else if error}<span>{error}</span>
    <button type="button" class="v2-btn" onclick={() => retry++}>Retry</button>
  {:else if host && date}
    {#if slots.length}<strong>Host busy</strong>
      <div class="slots">
        {#each slots as slot}<span>{time(slot.starts_at)} – {time(slot.ends_at)}</span>{/each}
      </div>{:else}<span>No bookings for this host on this date.</span>{/if}
    {#if conflict}<p role="alert">
        This time overlaps another event. Choose a different time.
      </p>{/if}
  {/if}
</div>

<style>
  .availability {
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
    line-height: 1.5;
  }
  .slots {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    margin-top: 6px;
  }
  .slots span {
    padding: 3px 7px;
    background: var(--v2-line-soft);
    border-radius: var(--crm-radius-sm);
  }
  p {
    color: var(--crm-danger);
    margin: var(--crm-space-2) 0 0;
  }
</style>
