<script>
  import { goto } from '$app/navigation';
  import { page, navigating } from '$app/state';
  import { base, resolve } from '$app/paths';
  import { asInternalPath } from '$lib/utils/paths.js';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import { Download, ChevronLeft, ChevronRight, ChartNoAxesCombined, Info } from '@lucide/svelte';

  /** @type {{data:any}} */
  let { data } = $props();
  let report = $derived(data.report);
  let chosen = $derived(report?.objects.find((item) => item.key === report.object));
  let busy = $derived(Boolean(navigating.to));
  let start = $state(''),
    end = $state('');
  $effect(() => {
    start = report?.start || '';
    end = report?.end || '';
  });
  let peak = $derived(Math.max(1, ...(report?.series || []).map((item) => item.count)));
  let axisStep = $derived.by(() => {
    const raw = peak / 4;
    const magnitude = 10 ** Math.floor(Math.log10(raw));
    return Math.max(1, [1, 2, 5, 10].find((value) => value * magnitude >= raw) * magnitude);
  });
  let axisMax = $derived(Math.ceil(peak / axisStep) * axisStep);
  let yTicks = $derived(
    Array.from({ length: Math.round(axisMax / axisStep) + 1 }, (_, i) => i * axisStep)
  );
  let xTicks = $derived.by(() => {
    const series = report?.series || [];
    const count = Math.min(5, series.length);
    return Array.from({ length: count }, (_, i) => {
      const index = count === 1 ? 0 : Math.round((i * (series.length - 1)) / (count - 1));
      return { index, date: series[index].date, position: ((index + 0.5) / series.length) * 100 };
    });
  });
  function axisDate(value) {
    return new Date(`${value}T12:00:00Z`).toLocaleDateString('en-US', {
      month: 'short',
      ...(report.interval === 'month' ? { year: '2-digit' } : { day: 'numeric' }),
      timeZone: 'UTC'
    });
  }
  let maxGroup = $derived(Math.max(1, ...(report?.breakdown || []).map((item) => item.count)));
  let periodLabel = $derived(report ? `${shortDate(report.start)} – ${shortDate(report.end)}` : '');
  let exportUrl = $derived(`${base}/api/reports/export?${page.url.searchParams}`);
  let chartTable = $state(false);
  const number = (value) => new Intl.NumberFormat('en-US').format(value);
  function money(value, currency) {
    try {
      return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency,
        maximumFractionDigits: 2
      }).format(Number(value));
    } catch {
      return `${currency} ${value}`;
    }
  }
  function shortDate(value) {
    return new Date(`${value.slice(0, 10)}T12:00:00Z`).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      timeZone: 'UTC'
    });
  }
  function recordDate(value) {
    if (!value) return '—';
    return value.includes('T')
      ? new Date(value).toLocaleString('en-US', {
          month: 'short',
          day: 'numeric',
          year: 'numeric',
          hour: 'numeric',
          minute: '2-digit',
          timeZone: report.timezone
        })
      : shortDate(value);
  }
  function update(values) {
    const params = new URLSearchParams(page.url.searchParams);
    params.delete('page');
    Object.entries(values).forEach(([key, value]) =>
      value ? params.set(key, String(value)) : params.delete(key)
    );
    void goto(`${resolve('/reports')}?${params}`, { keepFocus: true, noScroll: true });
  }
  function changeObject(value) {
    update({ object: value, date_field: '', group_by: '', owner: '', stage: '' });
  }
  function datesChanged() {
    if (start && end && start <= end) update({ start, end, interval: 'auto' });
  }
  function preset(value) {
    if (!value) return;
    const today = new Date(`${report.today}T12:00:00Z`);
    let first = new Date(today),
      last = new Date(today);
    if (value === '30') first.setUTCDate(first.getUTCDate() - 29);
    if (value === 'month') first.setUTCDate(1);
    if (value === 'last_month') {
      first.setUTCDate(1);
      first.setUTCMonth(first.getUTCMonth() - 1);
      last.setUTCDate(0);
    }
    if (value === 'year') {
      first.setUTCMonth(0, 1);
    }
    update({
      start: first.toISOString().slice(0, 10),
      end: last.toISOString().slice(0, 10),
      interval: 'auto'
    });
  }
</script>

<PageHeader title="Reports">
  {#snippet sub()}Explore performance over a period of time.{/snippet}
  {#snippet actions()}{#if report?.can_export}<a class="v2-btn" href={exportUrl} download
        ><Download size={15} />Export report</a
      >{/if}{/snippet}
</PageHeader>
<div class="reports" aria-busy={busy}>
  {#if data.reportError}
    <div class="report-error" role="alert">
      <strong>Could not open this report</strong>
      <p>{data.reportError}</p>
      <a class="v2-btn" href={resolve('/reports')}>Reset report filters</a>
    </div>
  {:else if report}
    <div class="filters">
      <label
        >Object<select
          class="v2-input"
          value={report.object}
          onchange={(e) => changeObject(e.currentTarget.value)}
          disabled={busy}
          >{#each report.objects as item}<option value={item.key}>{item.label}</option
            >{/each}</select
        ></label
      >
      <label
        >Date to use<select
          class="v2-input"
          value={report.date_field}
          onchange={(e) => update({ date_field: e.currentTarget.value })}
          disabled={busy}
          >{#each chosen.dates as item}<option value={item.key}>{item.label}</option>{/each}</select
        ></label
      >
      <label
        >From<input
          class="v2-input"
          type="date"
          bind:value={start}
          max={end || undefined}
          onchange={datesChanged}
          disabled={busy}
        /></label
      >
      <label
        >To<input
          class="v2-input"
          type="date"
          bind:value={end}
          min={start || undefined}
          onchange={datesChanged}
          disabled={busy}
        /></label
      >
      <label
        >Quick range<select
          class="v2-input"
          value=""
          onchange={(e) => preset(e.currentTarget.value)}
          disabled={busy}
          ><option value="">Choose dates</option><option value="30">Last 30 days</option><option
            value="month">This month</option
          ><option value="last_month">Last month</option><option value="year">This year</option
          ></select
        ></label
      >
    </div>
    <div class="secondary-filters">
      <label
        >{report.object === 'events' ? 'Host' : 'Owner'}<select
          class="v2-input"
          value={report.owner}
          onchange={(e) => update({ owner: e.currentTarget.value })}
          disabled={busy}
          ><option value="">All accessible {report.object === 'events' ? 'hosts' : 'owners'}</option
          >{#each report.owners as item}<option value={item.id}>{item.name}</option>{/each}</select
        ></label
      >
      <label
        >{report.object === 'events' ? 'Status' : 'Stage'}<select
          class="v2-input"
          value={report.stage}
          onchange={(e) => update({ stage: e.currentTarget.value })}
          disabled={busy}
          ><option value="">All {report.object === 'events' ? 'statuses' : 'stages'}</option
          >{#each report.stages as item}<option value={item.key}>{item.label}</option
            >{/each}</select
        ></label
      >
      <p class="timezone">{report.timezone}</p>
    </div>
    <div class="period-heading">
      <h2>{report.label}<span>{periodLabel}</span></h2>
      {#if busy}<span role="status">Updating…</span>{/if}
    </div>
    <div class="metrics">
      <section class="metric">
        <span>Records in period</span><strong>{number(report.summary.count)}</strong><small
          >{report.date_label}</small
        >
      </section>
      <section class="metric">
        <span>Previous period</span><strong>{number(report.summary.previous_count)}</strong><small
          >{shortDate(report.previous_start)} – {shortDate(report.previous_end)}</small
        >
      </section>
      <section class="metric">
        <span>Change in records</span><strong
          >{report.summary.change_percent === null
            ? '—'
            : `${report.summary.change_percent > 0 ? '+' : ''}${report.summary.change_percent}%`}</strong
        ><small
          >{report.summary.previous_count === 0
            ? 'No previous records to compare'
            : `${number(report.summary.count - report.summary.previous_count)} records vs. previous period`}</small
        >
      </section>
      {#if report.object === 'deals'}
        <section class="metric">
          <span>Deal value in period</span>
          <div class="amounts">
            {#each report.summary.amounts as item}<strong
                >{money(item.amount, item.currency)} <small>{item.currency}</small></strong
              >{:else}<strong>—</strong>{/each}
          </div>
          <small>Current amounts · all included stages</small>
        </section>
      {/if}
    </div>
    {#if report.object === 'deals' && report.summary.won_amounts.length}<div class="won-value">
        <span>Currently won in this selection</span>{#each report.summary.won_amounts as item}<b
            >{money(item.amount, item.currency)} {item.currency}</b
          >{/each}
      </div>{/if}
    <div class="charts">
      <section class="chart-panel">
        <div class="panel-heading">
          <div>
            <h3>Records over time</h3>
            <p>{report.date_label}</p>
          </div>
          <select
            class="v2-input"
            aria-label="Time interval"
            value={report.interval}
            onchange={(e) => update({ interval: e.currentTarget.value })}
            disabled={busy}
            ><option
              value="day"
              disabled={(new Date(report.end).getTime() - new Date(report.start).getTime()) /
                86400000 >
                365}>Day</option
            ><option
              value="week"
              disabled={(new Date(report.end).getTime() - new Date(report.start).getTime()) /
                86400000 >
                2561}>Week</option
            ><option value="month">Month</option></select
          >
        </div>
        {#if report.summary.count}
          <div
            class="time-chart"
            role="group"
            aria-label="Records over time, dates on the X axis and record count on the Y axis"
          >
            <div class="y-axis-title">Records</div>
            <div class="chart-frame">
              <div class="y-axis" aria-hidden="true">
                {#each yTicks as value}<span style={`bottom:${(value / axisMax) * 100}%`}
                    >{number(value)}</span
                  >{/each}
              </div>
              <div class="chart-scroll">
                <div class="plot-area" style={`--points:${report.series.length}`}>
                  <div class="bars">
                    <div class="grid-lines" aria-hidden="true">
                      {#each yTicks as value}<span style={`bottom:${(value / axisMax) * 100}%`}
                        ></span>{/each}
                    </div>
                    {#each report.series as item, index}
                      <button
                        type="button"
                        class="bar-column"
                        style={`--bar-height:${(item.count / axisMax) * 100}%`}
                        aria-label={`${shortDate(item.date)}: ${number(item.count)} ${item.count === 1 ? 'record' : 'records'}`}
                      >
                        <span class="bar" aria-hidden="true"></span>
                        <span
                          class="bar-tooltip"
                          class:align-start={index < report.series.length * 0.2}
                          class:align-end={index >= report.series.length * 0.8}
                          aria-hidden="true"
                        >
                          <span>{shortDate(item.date)}</span><strong
                            >{number(item.count)} {item.count === 1 ? 'record' : 'records'}</strong
                          >
                        </span>
                      </button>
                    {/each}
                  </div>
                  <div class="x-axis" aria-hidden="true">
                    {#each xTicks as item, index}<span
                        class:first-tick={index === 0}
                        class:last-tick={index === xTicks.length - 1 && index > 0}
                        style={`left:${item.position}%`}
                        title={shortDate(item.date)}>{axisDate(item.date)}</span
                      >{/each}
                  </div>
                </div>
              </div>
            </div>
            <div class="x-axis-title">Date</div>
          </div>
        {:else}<div class="empty-chart">
            <ChartNoAxesCombined size={30} /><strong>No records in this period</strong><span
              >Try another date range or date property.</span
            >
          </div>{/if}
        <button
          class="text-action"
          aria-expanded={chartTable}
          onclick={() => (chartTable = !chartTable)}
          >{chartTable ? 'Hide data' : 'View data'}</button
        >
        {#if chartTable}<div class="series-table">
            <table>
              <thead><tr><th>{report.interval} beginning</th><th>Records</th></tr></thead><tbody
                >{#each report.series as item}<tr
                    ><td>{shortDate(item.date)}</td><td>{number(item.count)}</td></tr
                  >{/each}</tbody
              >
            </table>
          </div>{/if}
      </section>
      <section class="chart-panel breakdown">
        <div class="panel-heading">
          <h3>Breakdown</h3>
          <select
            class="v2-input"
            aria-label="Breakdown"
            value={report.group_by}
            onchange={(e) => update({ group_by: e.currentTarget.value })}
            disabled={busy}
            >{#each chosen.groups as item}<option value={item.key}>{item.label}</option
              >{/each}</select
          >
        </div>
        <div class="breakdown-list">
          {#each report.breakdown as item}<div class="group-row">
              <div>
                <span title={item.label}>{item.label}</span><strong
                  >{number(item.count)}
                  <small>{Math.round((item.count / report.summary.count) * 100)}%</small></strong
                >
              </div>
              <div class="track"><div style={`width:${(item.count / maxGroup) * 100}%`}></div></div>
            </div>{:else}<p class="empty-small">No data for these filters.</p>{/each}
        </div>
      </section>
    </div>
    <section class="records-panel">
      <div class="panel-heading">
        <h3>Included records <span>{number(report.summary.count)}</span></h3>
        <span>{report.date_label}</span>
      </div>
      <div class="records-scroll">
        <table>
          <thead
            ><tr
              ><th>Name</th><th>{report.object === 'events' ? 'Status' : 'Stage'}</th><th
                >{report.object === 'events' ? 'Host' : 'Owner'}</th
              >{#if report.object === 'deals'}<th>Amount</th>{/if}<th>{report.date_label}</th></tr
            ></thead
          ><tbody
            >{#each report.records as item}<tr
                ><td
                  ><a class="record-link" href={resolve(asInternalPath(item.url))}
                    >{item.name || 'Unnamed record'}</a
                  ></td
                ><td>{item.state || '—'}</td><td>{item.owners.join(', ') || 'Unassigned'}</td
                >{#if report.object === 'deals'}<td
                    >{item.amount === null ? '—' : money(item.amount, item.currency)}
                    {item.currency}</td
                  >{/if}<td class="record-date">{recordDate(item.date)}</td></tr
              >{:else}<tr
                ><td colspan={report.object === 'deals' ? 5 : 4} class="empty-small"
                  >No records match this report.</td
                ></tr
              >{/each}</tbody
          >
        </table>
      </div>
      {#if report.pages > 1}<div class="pagination">
          <span>Page {report.page} of {number(report.pages)}</span><button
            class="v2-btn"
            aria-label="Previous page"
            disabled={busy || report.page <= 1}
            onclick={() => update({ page: report.page - 1 })}><ChevronLeft size={16} /></button
          ><button
            class="v2-btn"
            aria-label="Next page"
            disabled={busy || report.page >= report.pages}
            onclick={() => update({ page: report.page + 1 })}><ChevronRight size={16} /></button
          >
        </div>{/if}
    </section>
    <details class="definitions">
      <summary><Info size={15} />How this report is calculated</summary>
      <div>
        <p>
          Dates include the entire first and last day in {report.timezone}. The previous period has
          the same number of days. Reports include only records you can access.
        </p>
        <p>
          Stages, owners and amounts reflect current values of existing records. This is not a
          snapshot of their values at the end of the period. Deleted records and merged duplicates
          are excluded.
        </p>
        {#if report.object === 'deals'}<p>
            Expected close date is a planned date. “Currently won” means deals that are won now and
            match the selected date filter; it is not cash collected or a history of wins during
            that period.
          </p>{/if}{#if report.date_field === 'last_activity_at'}<p>
            Last activity counts each record once, using its latest recorded property change (or
            creation date). Opening a record does not count as activity.
          </p>{/if}{#if report.date_field.includes('stage')}<p>
            Last stage change is the latest transition only. It does not count every stage
            transition.
          </p>{/if}{#if report.object === 'events'}<p>
            Events are counted once, regardless of attendee count. Cancelled events remain included
            unless you filter by Scheduled. Scheduled means not cancelled; it does not confirm
            attendance.
          </p>{/if}
        <p>
          Export report downloads these totals, the complete breakdown and time series. It requires
          export permission covering this report.
        </p>
      </div>
    </details>
  {/if}
</div>

<style>
  .reports {
    padding: 0 28px 32px;
    min-height: 0;
    overflow: auto;
    flex: 1;
    color: var(--v2-text);
  }
  .filters,
  .secondary-filters {
    display: flex;
    gap: 14px;
    align-items: end;
    flex-wrap: wrap;
  }
  .filters {
    background: var(--v2-surface, #fff);
    padding: 18px;
    border: 1px solid var(--v2-line);
    border-radius: 12px;
  }
  .filters label {
    flex: 1;
    min-width: 140px;
  }
  label {
    display: grid;
    gap: 7px;
    font-size: 12px;
    color: var(--v2-slate);
  }
  .v2-input {
    width: 100%;
    min-height: 38px;
    font-size: 13px;
    background: var(--v2-surface, #fff);
  }
  .secondary-filters {
    padding: 14px 0 0;
  }
  .secondary-filters label {
    min-width: 175px;
  }
  .timezone {
    margin: 0 0 10px auto;
    font-size: 12px;
    color: var(--v2-slate);
  }
  .period-heading {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin: 26px 0 15px;
  }
  .period-heading h2 {
    font-size: 18px;
    font-weight: 650;
    margin: 0;
    display: flex;
    gap: 12px;
    align-items: baseline;
    flex-wrap: wrap;
  }
  .period-heading h2 span,
  .period-heading > span {
    font-size: 13px;
    font-weight: 400;
    color: var(--v2-slate);
  }
  .metrics {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
    gap: 14px;
  }
  .metric {
    padding: 20px;
    background: var(--v2-surface, #fff);
    border: 1px solid var(--v2-line);
    border-radius: 12px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .metric > span {
    font-size: 13px;
    color: var(--v2-slate);
  }
  .metric strong {
    font-size: 29px;
    line-height: 1.2;
    letter-spacing: -0.7px;
    font-weight: 650;
  }
  .metric small {
    font-size: 11px;
    color: var(--v2-slate);
  }
  .amounts {
    display: grid;
    gap: 7px;
  }
  .amounts strong {
    font-size: 23px;
  }
  .amounts small {
    font-size: 10px;
    margin-left: 7px;
    letter-spacing: 0;
  }
  .won-value {
    display: flex;
    gap: 14px;
    flex-wrap: wrap;
    margin-top: 14px;
    font-size: 13px;
  }
  .won-value span {
    color: var(--v2-slate);
  }
  .charts {
    display: grid;
    grid-template-columns: minmax(0, 1.7fr) minmax(280px, 1fr);
    gap: 18px;
    margin: 20px 0;
  }
  .chart-panel,
  .records-panel {
    background: var(--v2-surface, #fff);
    border: 1px solid var(--v2-line);
    border-radius: 12px;
    min-width: 0;
  }
  .chart-panel {
    padding: 20px;
  }
  .panel-heading {
    display: flex;
    gap: 12px;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 18px;
  }
  .panel-heading h3 {
    font-size: 14px;
    font-weight: 650;
    margin: 0;
  }
  .panel-heading h3 span {
    font-weight: 400;
    color: var(--v2-slate);
    margin-left: 6px;
  }
  .panel-heading p,
  .panel-heading > span {
    font-size: 12px;
    color: var(--v2-slate);
    margin: 4px 0 0;
  }
  .panel-heading select {
    width: auto;
    max-width: 180px;
  }
  .time-chart {
    --plot-height: 190px;
    --tooltip-space: 52px;
  }
  .y-axis-title,
  .x-axis-title {
    font-size: 11px;
    color: var(--v2-slate);
  }
  .y-axis-title {
    margin-bottom: 2px;
  }
  .x-axis-title {
    text-align: center;
    margin-left: 44px;
    margin-top: 3px;
  }
  .chart-frame {
    display: grid;
    grid-template-columns: 44px minmax(0, 1fr);
  }
  .y-axis {
    position: relative;
    height: var(--plot-height);
    margin-top: var(--tooltip-space);
  }
  .y-axis > span {
    position: absolute;
    right: 9px;
    transform: translateY(50%);
    font-size: 10px;
    color: var(--v2-slate);
    font-variant-numeric: tabular-nums;
  }
  .chart-scroll {
    overflow-x: auto;
  }
  .plot-area {
    min-width: max(260px, calc(var(--points) * 5px));
    padding-top: var(--tooltip-space);
  }
  .bars {
    position: relative;
    display: grid;
    grid-template-columns: repeat(var(--points), minmax(0, 1fr));
    height: var(--plot-height);
    border-left: 1px solid var(--v2-line);
  }
  .grid-lines {
    position: absolute;
    inset: 0;
    pointer-events: none;
  }
  .grid-lines > span {
    position: absolute;
    left: 0;
    right: 0;
    border-top: 1px solid var(--v2-line);
  }
  .bar-column {
    position: relative;
    height: 100%;
    min-width: 0;
    padding: 0 1px;
    display: flex;
    align-items: end;
    justify-content: center;
    border: 0;
    background: transparent;
    cursor: default;
  }
  .bar-column:hover,
  .bar-column:focus-visible {
    z-index: 2;
  }
  .bar-column:focus-visible {
    outline: 2px solid #81778c;
    outline-offset: -2px;
  }
  .bar {
    display: block;
    width: 100%;
    max-width: 64px;
    height: var(--bar-height);
    background: #7b7187;
    border-radius: 3px 3px 0 0;
  }
  .bar-column:hover .bar,
  .bar-column:focus-visible .bar {
    background: #514759;
  }
  .bar-tooltip {
    display: none;
    position: absolute;
    bottom: calc(var(--bar-height) + 8px);
    left: 50%;
    transform: translateX(-50%);
    background: #343137;
    color: #fff;
    border-radius: 7px;
    padding: 7px 10px;
    white-space: nowrap;
    box-shadow: 0 3px 10px #0002;
    pointer-events: none;
    text-align: left;
    line-height: 1.4;
  }
  .bar-tooltip > span {
    display: block;
    font-size: 10px;
    color: #ddd8e2;
  }
  .bar-tooltip strong {
    display: block;
    font-size: 12px;
    font-weight: 600;
  }
  .bar-tooltip.align-start {
    left: 0;
    transform: none;
  }
  .bar-tooltip.align-end {
    left: auto;
    right: 0;
    transform: none;
  }
  .bar-column:hover .bar-tooltip,
  .bar-column:focus-visible .bar-tooltip {
    display: block;
  }
  .x-axis {
    height: 28px;
    position: relative;
    margin-top: 9px;
  }
  .x-axis > span {
    position: absolute;
    transform: translateX(-50%);
    font-size: 10px;
    white-space: nowrap;
    color: var(--v2-slate);
  }
  .x-axis > .first-tick {
    transform: none;
  }
  .x-axis > .last-tick {
    transform: translateX(-100%);
  }
  .text-action {
    font-size: 12px;
    color: var(--v2-slate);
    margin-top: 14px;
    text-decoration: underline;
    text-underline-offset: 3px;
  }
  .empty-chart {
    height: 215px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    gap: 10px;
    color: var(--v2-slate);
    font-size: 12px;
  }
  .empty-chart strong {
    color: var(--v2-text);
    font-size: 14px;
  }
  .breakdown-list {
    max-height: 250px;
    overflow: auto;
    padding-right: 3px;
  }
  .group-row {
    margin-bottom: 17px;
  }
  .group-row > div:first-child {
    display: flex;
    justify-content: space-between;
    gap: 8px;
    font-size: 12px;
    margin-bottom: 7px;
  }
  .group-row span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .group-row strong {
    white-space: nowrap;
    font-weight: 600;
  }
  .group-row small {
    color: var(--v2-slate);
    font-weight: 400;
    font-size: 10px;
    margin-left: 9px;
  }
  .track {
    height: 5px;
    background: var(--v2-line);
    border-radius: 4px;
  }
  .track > div {
    height: 100%;
    border-radius: 4px;
    background: #8d8597;
  }
  .records-panel {
    overflow: hidden;
  }
  .records-panel > .panel-heading {
    padding: 18px 20px;
    margin: 0;
  }
  .records-scroll {
    overflow: auto;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    text-align: left;
    font-size: 12px;
  }
  th {
    color: var(--v2-slate);
    font-weight: 500;
    white-space: nowrap;
    background: var(--v2-bg, #faf9fb);
  }
  th,
  td {
    padding: 13px 18px;
    border-top: 1px solid var(--v2-line);
  }
  td {
    max-width: 280px;
    overflow-wrap: anywhere;
  }
  .record-date {
    white-space: nowrap;
  }
  .record-link {
    font-weight: 550;
    text-decoration: underline;
    text-decoration-color: var(--v2-line);
    text-underline-offset: 4px;
  }
  .record-link:hover {
    color: #766184;
  }
  .pagination {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    padding: 12px 16px;
    align-items: center;
    border-top: 1px solid var(--v2-line);
  }
  .pagination span {
    font-size: 12px;
    margin-right: 10px;
    color: var(--v2-slate);
  }
  .empty-small {
    color: var(--v2-slate);
    padding: 25px 18px;
    font-size: 13px;
  }
  .series-table {
    max-height: 260px;
    overflow: auto;
    margin-top: 12px;
  }
  .series-table th {
    position: sticky;
    top: 0;
  }
  .definitions {
    font-size: 12px;
    color: var(--v2-slate);
    margin-top: 20px;
    line-height: 1.6;
  }
  .definitions summary {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    width: fit-content;
  }
  .definitions > div {
    max-width: 850px;
    padding: 8px 0;
  }
  .definitions p {
    margin: 8px 0;
  }
  .report-error {
    padding: 24px;
    border: 1px solid var(--v2-line);
    border-radius: 12px;
    background: #fff;
  }
  .report-error p {
    margin: 12px 0;
  }
  .v2-btn {
    gap: 7px;
  }
  button:disabled,
  select:disabled,
  input:disabled {
    opacity: 0.6;
  }
  button:focus-visible,
  a:focus-visible,
  summary:focus-visible {
    outline: 2px solid #81778c;
    outline-offset: 3px;
  }
  @media (max-width: 1050px) {
    .charts {
      grid-template-columns: 1fr;
    }
    .reports {
      padding: 0 18px 24px;
    }
    .filters label {
      min-width: 150px;
    }
    .metric {
      padding: 16px;
    }
  }
  @media (max-width: 600px) {
    .reports {
      padding: 0 12px 20px;
    }
    .filters {
      padding: 12px;
      gap: 10px;
    }
    .filters label {
      min-width: 125px;
    }
    .metrics {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    .metric strong {
      font-size: 24px;
    }
    .secondary-filters label {
      flex: 1;
      min-width: 120px;
    }
    .timezone {
      width: 100%;
      margin-top: 4px;
    }
    .chart-panel {
      padding: 15px;
    }
  }
</style>
