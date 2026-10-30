<script>
  import { SvelteURLSearchParams } from 'svelte/reactivity';

  import { parseDate } from '@internationalized/date';
  import DateRangeDialog from '$lib/v2/components/DateRangeDialog.svelte';
  import SearchableSelect from '$lib/components/SearchableSelect.svelte';
  import ReportMetric from '$lib/v2/components/ReportMetric.svelte';
  import Notice from '$lib/components/Notice.svelte';
  import '$lib/v2/styles/module-layout.css';
  import { useI18n } from '$lib/i18n/context.js';
  const { ui, locale } = useI18n();

  import { goto } from '$app/navigation';
  import { page, navigating } from '$app/state';
  import { resolve } from '$app/paths';
  import { asInternalPath } from '$lib/utils/paths.js';
  import { canFilterOwners } from '$lib/v2/permissions.js';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import { Download, ChevronLeft, ChevronRight, ChartNoAxesCombined } from '@lucide/svelte';

  /** @type {{data:any}} */
  let { data } = $props();
  let report = $derived(data.report);
  let chosen = $derived(report?.objects.find((item) => item.key === report.object));
  let busy = $derived(Boolean(navigating.to));
  let customRangeOpen = $state(false);
  let ranges = $derived.by(() => {
    if (!report) return [];
    const today = parseDate(report.today);
    const month = today.set({ day: 1 });
    return [
      {
        value: '30',
        label: ui('Last 30 days'),
        start: today.subtract({ days: 29 }).toString(),
        end: today.toString()
      },
      { value: 'month', label: ui('This month'), start: month.toString(), end: today.toString() },
      {
        value: 'last_month',
        label: ui('Last month'),
        start: month.subtract({ months: 1 }).toString(),
        end: month.subtract({ days: 1 }).toString()
      },
      {
        value: 'year',
        label: ui('This year'),
        start: today.set({ month: 1, day: 1 }).toString(),
        end: today.toString()
      }
    ];
  });
  let rangePreset = $derived(
    ranges.find((item) => item.start === report?.start && item.end === report?.end)?.value ||
      'custom'
  );
  let rangeSelection = $state('');
  $effect(() => {
    if (!customRangeOpen) rangeSelection = rangePreset;
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
    return new Date(`${value}T12:00:00Z`).toLocaleDateString(locale(), {
      month: 'short',
      ...(report.interval === 'month' ? { year: '2-digit' } : { day: 'numeric' }),
      timeZone: 'UTC'
    });
  }
  let maxGroup = $derived(Math.max(1, ...(report?.breakdown || []).map((item) => item.count)));
  let periodLabel = $derived(report ? `${shortDate(report.start)} – ${shortDate(report.end)}` : '');
  let exportUrl = $derived(`/api/reports/export?${page.url.searchParams}`);
  let chartTable = $state(false);
  const number = (value) => new Intl.NumberFormat(locale()).format(value);
  function money(value, currency) {
    try {
      return new Intl.NumberFormat(locale(), {
        style: 'currency',
        currency,
        maximumFractionDigits: 2
      }).format(Number(value));
    } catch {
      return `${currency} ${value}`;
    }
  }
  function shortDate(value) {
    return new Date(`${value.slice(0, 10)}T12:00:00Z`).toLocaleDateString(locale(), {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      timeZone: 'UTC'
    });
  }
  function recordDate(value) {
    if (!value) return '—';
    return value.includes('T')
      ? new Date(value).toLocaleString(locale(), {
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
    const params = new SvelteURLSearchParams(page.url.searchParams);
    params.delete('page');
    Object.entries(values).forEach(([key, value]) =>
      value ? params.set(key, String(value)) : params.delete(key)
    );
    void goto(resolve(asInternalPath(`/reports?${params}`)), { keepFocus: true, noScroll: true });
  }
  function changeObject(value) {
    update({ object: value, date_field: '', group_by: '', owner: '', stage: '' });
  }
  function preset(value) {
    if (value === 'custom') {
      customRangeOpen = true;
      return;
    }
    const range = ranges.find((item) => item.value === value);
    if (range) update({ start: range.start, end: range.end, interval: 'auto' });
  }
</script>

<PageHeader title={ui('Reports')} compact />
<div class="reports crm-module-body crm-pill-controls" aria-busy={busy}>
  {#if data.reportError}
    <Notice title={ui('Could not open this report')} message={data.reportError}>
      {#snippet actions()}<a class="v2-btn" href={resolve('/reports')}
          >{ui('Reset report filters')}</a
        >{/snippet}
    </Notice>
  {:else if report}
    <div class="report-controls crm-panel crm-control-toolbar">
      <div class="filter-field">
        <SearchableSelect
          label={ui('Object')}
          value={report.object}
          options={report.objects.map((item) => ({ value: item.key, label: ui(item.label) }))}
          disabled={busy}
          onchange={changeObject}
        />
      </div>
      <div class="filter-field">
        <SearchableSelect
          label={ui('Date to use')}
          value={report.date_field}
          options={chosen.dates.map((item) => ({ value: item.key, label: ui(item.label) }))}
          disabled={busy}
          onchange={(value) => update({ date_field: value })}
        />
      </div>
      <div class="filter-field">
        <SearchableSelect
          label={ui('Choose dates')}
          bind:value={rangeSelection}
          options={[...ranges, { value: 'custom', label: ui('Custom') }]}
          disabled={busy}
          onchange={preset}
        />
      </div>
      {#if canFilterOwners(page.data.permissions, 'reports') && canFilterOwners(page.data.permissions, report.object === 'events' ? 'calendar' : report.object)}
        <div class="filter-field">
          <SearchableSelect
            label={report.object === 'events' ? ui('Host') : ui('Owner')}
            value={report.owner}
            placeholder={report.object === 'events' ? ui('All hosts') : ui('All owners')}
            options={report.owners.map((item) => ({ value: item.id, label: item.name }))}
            disabled={busy}
            onchange={(value) => update({ owner: value })}
          />
        </div>
      {/if}
      <div class="filter-field">
        <SearchableSelect
          label={report.object === 'events' ? ui('Status') : ui('Stage')}
          value={report.stage}
          placeholder={report.object === 'events' ? ui('All statuses') : ui('All stages')}
          options={report.stages.map((item) => ({ value: item.key, label: ui(item.label) }))}
          disabled={busy}
          onchange={(value) => update({ stage: value })}
        />
      </div>
    </div>
    {#if customRangeOpen}<DateRangeDialog
        bind:open={customRangeOpen}
        start={report.start}
        end={report.end}
        onapply={(start, end) => update({ start, end, interval: 'auto' })}
      />{/if}
    <div class="period-heading">
      <h2>{ui(report.label)}<span>{periodLabel}</span></h2>
      {#if busy}<span role="status">{ui('Updating…')}</span>{/if}
    </div>
    <div
      class="metrics crm-stat-grid"
      style={`--metric-columns:${1 + (report.metrics?.length || 0)}`}
    >
      <section class="metric crm-stat crm-panel">
        <span>{ui('Records in selection')}</span><strong>{number(report.summary.count)}</strong>
        <small title={`${shortDate(report.previous_start)} – ${shortDate(report.previous_end)}`}>
          {report.summary.change_percent === null
            ? ui('No previous records to compare')
            : `${report.summary.change_percent > 0 ? '+' : ''}${number(report.summary.change_percent)}% · ${ui('vs. previous period')}`}
        </small>
      </section>
      {#each report.metrics || [] as metric (metric.key)}<ReportMetric {metric} />{/each}
    </div>
    <div class="charts">
      <section class="chart-panel crm-panel">
        <div class="panel-heading crm-control-toolbar">
          <div>
            <h3>{ui(report.label)} · {ui('Trend')}</h3>
            <p>{ui(report.date_label)}</p>
          </div>
          <div class="chart-control">
            <SearchableSelect
              label={ui('Time interval')}
              value={report.interval}
              options={[
                ...((new Date(report.end).getTime() - new Date(report.start).getTime()) /
                  86400000 <=
                365
                  ? [{ value: 'day', label: ui('Day') }]
                  : []),
                ...((new Date(report.end).getTime() - new Date(report.start).getTime()) /
                  86400000 <=
                2561
                  ? [{ value: 'week', label: ui('Week') }]
                  : []),
                { value: 'month', label: ui('Month') }
              ]}
              disabled={busy}
              onchange={(value) => update({ interval: value })}
            />
          </div>
        </div>
        {#if report.summary.count}
          <div
            class="time-chart"
            role="group"
            aria-label={ui('Records over time, dates on the X axis and record count on the Y axis')}
          >
            <div class="y-axis-title">{ui('Records')}</div>
            <div class="chart-frame">
              <div class="y-axis" aria-hidden="true">
                {#each yTicks as value (value)}<span style={`bottom:${(value / axisMax) * 100}%`}
                    >{number(value)}</span
                  >{/each}
              </div>
              <div class="chart-scroll">
                <div class="plot-area" style={`--points:${report.series.length}`}>
                  <div class="bars">
                    <div class="grid-lines" aria-hidden="true">
                      {#each yTicks as value (value)}<span
                          style={`bottom:${(value / axisMax) * 100}%`}
                        ></span>{/each}
                    </div>
                    {#each report.series as item, index (item.date)}
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
                            >{number(item.count)}
                            {item.count === 1 ? ui('record') : ui('records')}</strong
                          >
                        </span>
                      </button>
                    {/each}
                  </div>
                  <div class="x-axis" aria-hidden="true">
                    {#each xTicks as item, index (item.date)}<span
                        class:first-tick={index === 0}
                        class:last-tick={index === xTicks.length - 1 && index > 0}
                        style={`left:${item.position}%`}
                        title={shortDate(item.date)}>{axisDate(item.date)}</span
                      >{/each}
                  </div>
                </div>
              </div>
            </div>
            <div class="x-axis-title">{ui('Date')}</div>
          </div>
        {:else}<div class="empty-chart">
            <ChartNoAxesCombined size={30} /><strong>{ui('No records in this period')}</strong><span
              >{ui('Try another date range or date property.')}</span
            >
          </div>{/if}
        <button
          class="text-action"
          aria-expanded={chartTable}
          onclick={() => (chartTable = !chartTable)}
          >{chartTable ? ui('Hide data') : ui('View data')}</button
        >
        {#if chartTable}<div class="series-table">
            <table>
              <thead
                ><tr><th>{report.interval} {ui('beginning')}</th><th>{ui('Records')}</th></tr
                ></thead
              ><tbody
                >{#each report.series as item (item.date)}<tr
                    ><td>{shortDate(item.date)}</td><td>{number(item.count)}</td></tr
                  >{/each}</tbody
              >
            </table>
          </div>{/if}
      </section>
      <section class="chart-panel breakdown crm-panel">
        <div class="panel-heading crm-control-toolbar">
          <h3>{ui(report.group_label)}</h3>
          <div class="chart-control">
            <SearchableSelect
              label={ui('Breakdown')}
              value={report.group_by}
              options={chosen.groups.map((item) => ({ value: item.key, label: ui(item.label) }))}
              disabled={busy}
              onchange={(value) => update({ group_by: value })}
            />
          </div>
        </div>
        <div class="breakdown-list">
          {#each report.breakdown as item (item.key)}<div class="group-row">
              <div>
                <span title={ui(item.label)}>{ui(item.label)}</span><strong
                  >{number(item.count)}
                  <small>{Math.round((item.count / report.summary.count) * 100)}%</small></strong
                >
              </div>
              <div class="track"><div style={`width:${(item.count / maxGroup) * 100}%`}></div></div>
            </div>{:else}<p class="empty-small">{ui('No data for these filters.')}</p>{/each}
        </div>
      </section>
    </div>
    {#if report.group_by !== (report.object === 'events' ? 'event_status' : ['tasks', 'tickets'].includes(report.object) ? 'status' : 'stage')}
      <section class="state-panel crm-panel">
        <h3>{ui('Current stages')}</h3>
        <div class="state-grid">
          {#each report.state_breakdown || [] as state (state.key)}
            <button
              class="state-item"
              disabled={busy || !state.count}
              onclick={() => update({ stage: state.key })}
              aria-label={`${ui(state.label)}: ${number(state.count)}`}
            >
              <span>{ui(state.label)}</span><strong>{number(state.count)}</strong>
              <span class="track"
                ><span
                  style={`width:${report.summary.count ? (state.count / report.summary.count) * 100 : 0}%`}
                ></span></span
              >
            </button>
          {/each}
        </div>
      </section>
    {/if}
    <section class="records-panel crm-panel">
      <div class="panel-heading crm-control-toolbar">
        <h3>{ui('Included records')} <span>{number(report.summary.count)}</span></h3>
        <span>{ui(report.date_label)}</span>
      </div>
      <div class="records-scroll">
        <table>
          <thead
            ><tr
              ><th>{ui('Name')}</th><th
                >{report.object === 'events' ? ui('Status') : ui('Stage')}</th
              ><th>{report.object === 'events' ? ui('Host') : ui('Owner')}</th
              >{#if report.object === 'deals'}<th>{ui('Amount')}</th>{/if}<th
                >{report.date_label}</th
              ></tr
            ></thead
          ><tbody
            >{#each report.records as item (item.id)}<tr
                ><td
                  ><a class="record-link" href={resolve(asInternalPath(item.url))}
                    >{item.name || 'Unnamed record'}</a
                  ></td
                ><td>{item.state ? ui(item.state) : '—'}</td><td
                  >{item.owners.join(', ') || ui('Unassigned')}</td
                >{#if report.object === 'deals'}<td
                    >{item.amount === null ? '—' : money(item.amount, item.currency)}
                    {item.currency}</td
                  >{/if}<td class="record-date">{recordDate(item.date)}</td></tr
              >{:else}<tr
                ><td colspan={report.object === 'deals' ? 5 : 4} class="empty-small"
                  >{ui('No records match this report.')}</td
                ></tr
              >{/each}</tbody
          >
        </table>
      </div>
      <div class="pagination crm-control-toolbar">
        {#if report.can_export}<a
            class="v2-btn export"
            href={resolve(asInternalPath(exportUrl))}
            download><Download size={15} />{ui('Export report')}</a
          >{/if}
        <span>{ui('Page')} {report.page} {ui('of')} {number(report.pages)}</span><button
          class="v2-btn"
          aria-label={ui('Previous page')}
          disabled={busy || report.page <= 1}
          onclick={() => update({ page: report.page - 1 })}><ChevronLeft size={16} /></button
        ><button
          class="v2-btn"
          aria-label={ui('Next page')}
          disabled={busy || report.page >= report.pages}
          onclick={() => update({ page: report.page + 1 })}><ChevronRight size={16} /></button
        >
      </div>
    </section>
  {/if}
</div>

<style>
  .reports {
    min-height: 0;
    overflow: auto;
    flex: 1;
    color: var(--crm-text);
  }
  .report-controls {
    display: flex;
    flex-wrap: nowrap;
    align-items: end;
    gap: var(--crm-space-3);
    padding: var(--crm-space-3) var(--crm-space-4);
  }
  .filter-field {
    display: grid;
    gap: 4px;
    flex: 1 1 0;
    min-width: 0;
    font-size: var(--crm-text-xs);
  }
  .chart-control {
    width: 155px;
  }
  .metrics {
    grid-template-columns: repeat(var(--metric-columns), minmax(0, 1fr));
  }
  .export {
    margin-right: auto;
  }
  .state-panel {
    padding: var(--crm-space-4);
    margin-bottom: var(--crm-space-4);
  }
  .state-panel h3 {
    font-size: var(--crm-text-sm);
    margin: 0 0 12px;
  }
  .state-grid {
    display: flex;
    gap: var(--crm-space-4);
    overflow-x: auto;
  }
  .state-item {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 8px;
    min-width: 130px;
    flex: 1;
    text-align: left;
    font-size: var(--crm-text-xs);
    padding: 4px;
    border-radius: var(--crm-radius-sm);
  }
  .state-item:hover:not(:disabled) {
    background: var(--crm-surface-subtle);
  }
  .state-item:focus-visible {
    outline: 2px solid var(--crm-focus);
  }
  .state-item .track {
    grid-column: 1 / -1;
  }
  .state-item .track > span {
    display: block;
    height: 100%;
    background: var(--crm-primary);
    border-radius: inherit;
  }
  .period-heading {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin: var(--crm-space-3) 0;
  }
  .period-heading h2 {
    font-size: var(--crm-text-sm);
    font-weight: 650;
    margin: 0;
    display: flex;
    gap: var(--crm-space-3);
    align-items: baseline;
    flex-wrap: wrap;
  }
  .period-heading h2 span,
  .period-heading > span {
    font-size: var(--crm-text-sm);
    font-weight: 400;
    color: var(--v2-slate);
  }
  .charts {
    display: grid;
    grid-template-columns: minmax(0, 1.6fr) minmax(0, 1fr);
    gap: var(--crm-space-4);
    margin: var(--crm-space-4) 0;
  }
  .chart-panel {
    padding: 0 var(--crm-space-5) var(--crm-space-5);
    min-width: 0;
  }
  .panel-heading {
    display: flex;
    gap: var(--crm-space-3);
    align-items: center;
    justify-content: space-between;
    padding: var(--crm-space-4) var(--crm-space-5);
    min-height: 3.5rem;
    margin: 0 calc(-1 * var(--crm-space-5)) var(--crm-space-4);
    border-bottom: 1px solid var(--crm-border-soft);
  }
  .panel-heading h3 {
    font-size: var(--crm-text-sm);
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
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
    margin: var(--crm-space-1) 0 0;
  }
  .time-chart {
    --plot-height: 190px;
    --tooltip-space: 52px;
  }
  .y-axis-title,
  .x-axis-title {
    font-size: var(--crm-text-xs);
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
    font-size: var(--crm-text-xs);
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
    border-top: 1px dashed var(--crm-border-soft);
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
    outline: 2px solid var(--crm-focus);
    outline-offset: -2px;
  }
  .bar {
    display: block;
    width: 100%;
    max-width: 64px;
    height: var(--bar-height);
    background: var(--crm-brand-gradient);
    border-radius: var(--crm-radius-sm) var(--crm-radius-sm) 0 0;
  }
  .bar-column:hover .bar,
  .bar-column:focus-visible .bar {
    background: var(--crm-primary-active);
  }
  .bar-tooltip {
    display: none;
    position: absolute;
    bottom: calc(var(--bar-height) + 8px);
    left: 50%;
    transform: translateX(-50%);
    background: var(--crm-nav-bg);
    color: var(--crm-nav-text);
    border-radius: var(--crm-radius-md);
    padding: 7px 10px;
    white-space: nowrap;
    box-shadow: var(--crm-shadow-lg);
    pointer-events: none;
    text-align: left;
    line-height: 1.4;
  }
  .bar-tooltip > span {
    display: block;
    font-size: var(--crm-text-xs);
    color: var(--crm-nav-muted);
  }
  .bar-tooltip strong {
    display: block;
    font-size: var(--crm-text-xs);
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
    font-size: var(--crm-text-xs);
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
    font-size: var(--crm-text-xs);
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
    font-size: var(--crm-text-xs);
  }
  .empty-chart strong {
    color: var(--crm-text);
    font-size: var(--crm-text-sm);
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
    gap: var(--crm-space-2);
    font-size: var(--crm-text-xs);
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
    font-size: var(--crm-text-xs);
    margin-left: 9px;
  }
  .track {
    height: 5px;
    background: var(--v2-line);
    border-radius: var(--crm-radius-sm);
  }
  .track > div {
    height: 100%;
    border-radius: var(--crm-radius-sm);
    background: var(--crm-brand-gradient);
  }
  .records-panel {
    overflow: hidden;
  }
  .records-panel > .panel-heading {
    padding: 18px var(--crm-space-5);
    margin: 0;
  }
  tbody tr:nth-child(even) {
    background: var(--crm-surface);
  }
  tbody tr:hover {
    background: var(--crm-surface-subtle);
  }
  .metric {
    overflow-wrap: anywhere;
  }
  .panel-heading {
    flex-wrap: wrap;
  }
  .records-scroll {
    overflow: auto;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    text-align: left;
    font-size: var(--crm-text-sm);
  }
  th {
    color: var(--v2-slate);
    font-weight: 650;
    white-space: nowrap;
    background: var(--crm-surface-secondary);
    font-size: var(--crm-text-xs);
  }
  th,
  td {
    padding: var(--crm-space-3) var(--crm-space-4);
    border-top: 1px solid var(--crm-border-soft);
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
    text-decoration: none;
    text-underline-offset: 4px;
  }
  .record-link:hover {
    text-decoration: underline;
    color: var(--crm-text-muted);
  }
  .pagination {
    display: flex;
    justify-content: flex-end;
    gap: var(--crm-space-2);
    padding: var(--crm-space-3) var(--crm-space-4);
    align-items: center;
    border-top: 1px solid var(--v2-line);
  }
  .pagination span {
    font-size: var(--crm-text-xs);
    margin-right: 10px;
    color: var(--v2-slate);
  }
  .empty-small {
    color: var(--v2-slate);
    padding: 25px 18px;
    font-size: var(--crm-text-sm);
  }
  .series-table {
    max-height: 260px;
    overflow: auto;
    margin-top: var(--crm-space-3);
  }
  .series-table th {
    position: sticky;
    top: 0;
  }
  .v2-btn {
    gap: 7px;
  }
  button:disabled {
    opacity: 0.6;
  }
  button:focus-visible,
  a:focus-visible {
    outline: 2px solid var(--crm-focus);
    outline-offset: 3px;
  }

  .records-panel > .panel-heading {
    border-bottom: 0;
  }
  .records-scroll {
    position: relative;
  }
</style>
