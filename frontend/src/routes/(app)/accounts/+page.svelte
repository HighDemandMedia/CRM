<script>
  import ListPagination from '$lib/v2/components/ListPagination.svelte';
  import ExportDialog from '$lib/v2/components/ExportDialog.svelte';
  import {
    browserStorage,
    preferenceKey,
    readPreference,
    writePreference,
    columnWidths
  } from '$lib/v2/list-preferences.js';
  import { listViewPreference } from '$lib/v2/list-view-preference.svelte.js';
  import { useI18n } from '$lib/i18n/context.js';
  const { ui, count, relativeDays, money } = useI18n();

  import { can } from '$lib/v2/permissions.js';
  import { showStageRequirements } from '$lib/components/pipelines/feedback.js';
  import PipelineTotal from '$lib/v2/components/PipelineTotal.svelte';
  import PipelineCardSummary from '$lib/v2/components/PipelineCardSummary.svelte';
  import '$lib/v2/styles/pipeline.css';
  import '$lib/v2/styles/list-view.css';
  import { pipelineTone } from '$lib/v2/pipeline-view.js';
  import { listColumns, columnValue } from '$lib/v2/list-columns.js';
  import { columnSelection } from '$lib/v2/column-selection.svelte.js';
  import ColumnPicker from '$lib/v2/components/ColumnPicker.svelte';
  import StageProgress from '$lib/v2/components/StageProgress.svelte';
  import { resolve } from '$app/paths';
  import { page } from '$app/state';
  import { goto, invalidateAll } from '$app/navigation';
  import { deserialize } from '$app/forms';
  let dragging = $state('');
  let insertionIndex = $state(-1);
  /** @type {HTMLCanvasElement | null} */
  let dragPreview = null;
  let suppressSort = false;
  let clock = $state(Date.now());
  import { onMount, untrack } from 'svelte';

  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import { advancedCompanyFilters as companyFilterDefinitions } from '$lib/v2/company-filter-fields.js';
  import { companyColumns as legacyFields } from '$lib/v2/company-columns.js';

  import { Plus, List, Columns3 } from '@lucide/svelte';

  /** @type {{ data: any }} */
  let { data } = $props();
  let advancedContactFilters = $derived(
    companyFilterDefinitions.map((field) =>
      field.key === 'contacts'
        ? { ...field, options: data.contacts.map((contact) => [contact.id, contact.name]) }
        : field.key === 'industry'
          ? { ...field, options: data.industries }
          : field.key === 'country'
            ? { ...field, options: data.countries }
            : field
    )
  );
  let draggedContact = $state('');
  let draggedStage = $state('');
  let dropStage = $state('');
  let movingContact = $state('');
  let moveError = $state('');
  let moveStatus = $state('');
  function endContactDrag() {
    draggedContact = '';
    draggedStage = '';
    dropStage = '';
  }
  /** @param {DragEvent} event @param {string} id @param {string} stage */
  function startContactDrag(event, id, stage) {
    if (movingContact) {
      event.preventDefault();
      return;
    }
    draggedContact = id;
    draggedStage = stage;
    if (event.dataTransfer) {
      event.dataTransfer.effectAllowed = 'move';
      event.dataTransfer.setData('text/plain', id);
    }
  }
  /** @param {DragEvent} event @param {string} stage */
  function overStage(event, stage) {
    if (!draggedContact || movingContact || stage === draggedStage) return;
    event.preventDefault();
    if (event.dataTransfer) event.dataTransfer.dropEffect = 'move';
    dropStage = stage;
    const board = /** @type {HTMLElement} */ (event.currentTarget).closest('.contact-board');
    if (board) {
      const bounds = board.getBoundingClientRect();
      if (event.clientX > bounds.right - 40) board.scrollLeft += 18;
      else if (event.clientX < bounds.left + 40) board.scrollLeft -= 18;
    }
  }
  /** @param {DragEvent} event @param {string} stage */
  function dropContact(event, stage) {
    event.preventDefault();
    const id = draggedContact;
    const source = draggedStage;
    endContactDrag();
    if (id && stage !== source) void moveContact(id, stage);
  }
  /** @param {string} id @param {string} stage */
  async function moveContact(id, stage) {
    if (movingContact) return;
    movingContact = id;
    moveError = '';
    moveStatus = 'Saving stage…';
    let saved = false;
    try {
      const body = new FormData();
      body.set('id', id);
      body.set('stage', stage);
      const response = await fetch('?/moveStage', {
        method: 'POST',
        body,
        headers: { 'x-sveltekit-action': 'true' }
      });
      const result = deserialize(await response.text());
      if (result.type !== 'success') {
        if (showStageRequirements(result, 'Account', id, { stage })) {
          moveStatus = '';
          return;
        }
        moveError =
          result.type === 'failure'
            ? String(result.data?.error ?? 'Could not move this company.')
            : 'Could not move this company. Refresh the page and try again.';
        moveStatus = '';
        return;
      }
      saved = true;
      await invalidateAll();
      moveStatus = `Company moved to ${data.board.find((item) => item.value === stage)?.label ?? stage}.`;
    } catch {
      moveStatus = '';
      moveError = saved
        ? 'Stage saved, but the board could not refresh. Reload the page.'
        : 'Could not confirm the change. Reload the page before trying again.';
    } finally {
      movingContact = '';
    }
  }
  let filterValues = $state(/** @type {Record<string,string>} */ ({}));
  let filtersUpdating = false;
  let filterVersion = 0;
  /** @type {ReturnType<typeof setTimeout> | undefined} */
  let filterTimer;
  let filterError = $state('');
  /** @param {number} [delay] */
  function updateFilters(delay = 0) {
    clearTimeout(filterTimer);
    const version = ++filterVersion;
    filtersUpdating = true;
    filterTimer = setTimeout(async () => {
      const url = new URL(page.url);
      url.search = '';
      for (const key of ['view', 'sort', 'direction', 'inactive', 'page_size']) {
        const value = page.url.searchParams.get(key);
        if (value) url.searchParams.set(key, value);
      }
      for (const [key, value] of Object.entries(filterValues)) {
        if (value.trim()) url.searchParams.set(key, value.trim());
      }
      filterError = '';
      try {
        await goto(resolve('/accounts') + url.search, {
          replaceState: true,
          keepFocus: true,
          noScroll: true
        });
      } catch {
        filterError = 'Could not update filters. Please try again.';
      } finally {
        if (version === filterVersion) filtersUpdating = false;
      }
    }, delay);
  }
  /** @param {Event} event */
  function filterInput(event) {
    const input = /** @type {HTMLInputElement | HTMLSelectElement} */ (event.target);
    if (!input.name) return;
    filterValues[input.name] = input.value;
    updateFilters(
      input instanceof HTMLSelectElement || input.type === 'date' || !input.value ? 0 : 350
    );
  }
  /** @param {string} key */
  function removeFilter(key) {
    advancedKeys = advancedKeys.filter((item) => item !== key);
    delete filterValues[key];
    delete filterValues[`${key}__gte`];
    delete filterValues[`${key}__lte`];
    updateFilters();
  }
  let advancedKeys = $state(/** @type {string[]} */ ([]));
  $effect(() => {
    const url = page.url;
    if (untrack(() => filtersUpdating)) return;
    const supported = [
      'search',
      'contacts',
      'stage',
      ...advancedContactFilters.flatMap((field) =>
        field.type?.endsWith('range') ? [`${field.key}__gte`, `${field.key}__lte`] : [field.key]
      )
    ];
    filterValues = Object.fromEntries(
      supported.map((key) => [key, url.searchParams.get(key) ?? ''])
    );
    advancedKeys = advancedContactFilters
      .filter((field) =>
        field.type?.endsWith('range')
          ? page.url.searchParams.get(`${field.key}__gte`) ||
            page.url.searchParams.get(`${field.key}__lte`)
          : page.url.searchParams.get(field.key)
      )
      .map((field) => field.key);
  });
  const catalog = $derived(listColumns('Account', page.data.propertyLayout?.Account, legacyFields));
  const fields = $derived(catalog.map((c) => [c.key, c.system ? ui(c.label) : c.label]));
  listViewPreference(
    () => `${page.data.accountId}.${page.data.accountUser?.email}.Account`,
    () => page.url
  );
  const selection = columnSelection(
    () => catalog,
    () => `${page.data.accountId}.${page.data.accountUser?.email}.Account`
  );
  const selected = $derived(selection.selected);
  let ready = $state(false);
  /** @type {Record<string, number>} */
  let widths = $state({});
  let orderedFields = $derived(
    selected
      .map((key) => fields.find((field) => field[0] === key))
      .filter((field) => field !== undefined)
  );
  let totalWidth = $derived(selected.reduce((sum, key) => sum + (widths[key] ?? 160), 120));
  const widthKey = $derived(
    preferenceKey('widths', `${page.data.accountId}.${page.data.accountUser?.email}.Account`)
  );
  $effect(() => {
    const key = widthKey;
    const storage = browserStorage();
    widths = columnWidths(readPreference(storage, key, {}));
    function sync(event) {
      if (event.storageArea === storage && (event.key === key || event.key === null))
        widths = columnWidths(readPreference(storage, key, {}));
    }
    window.addEventListener('storage', sync);
    return () => window.removeEventListener('storage', sync);
  });
  onMount(() => {
    const timer = setInterval(() => {
      if (data.view === 'pipeline' && !document.hidden) clock = Date.now();
    }, 86400000);
    ready = true;
    return () => {
      clearInterval(timer);
      clearTimeout(filterTimer);
      dragPreview?.remove();
    };
  });
  /** @param {string[]} next */
  function saveColumns(next) {
    selection.set(next);
  }
  /** @param {string} key */
  function toggleColumn(key) {
    saveColumns(
      selected.includes(key) ? selected.filter((value) => value !== key) : [...selected, key]
    );
  }
  /** @param {string} key @param {number} direction */
  function moveColumn(key, direction) {
    const next = [...selected];
    const index = next.indexOf(key);
    const target = index + direction;
    if (index < 0 || target < 0 || target >= next.length) return;
    next.splice(index, 1);
    next.splice(target, 0, key);
    saveColumns(next);
  }
  /** @param {DragEvent} event @param {string} key */
  function startColumnDrag(event, key) {
    dragging = key;
    insertionIndex = selected.indexOf(key);
    suppressSort = true;
    if (event.dataTransfer) {
      event.dataTransfer.effectAllowed = 'move';
      event.dataTransfer.setData('text/plain', key);
      createDragPreview(event, key);
    }
  }
  /** @param {DragEvent} event @param {string} key */
  function createDragPreview(event, key) {
    dragPreview?.remove();
    const header = /** @type {HTMLElement} */ (event.currentTarget).closest('th');
    const width = Math.min(widths[key] ?? 160, 480);
    const height = 42;
    const canvas = document.createElement('canvas');
    canvas.width = width + 40;
    canvas.height = height + 40;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.shadowColor = 'rgba(15, 23, 42, 0.3)';
    ctx.shadowBlur = 14;
    ctx.shadowOffsetY = 6;
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(20, 20, width, height);
    ctx.shadowColor = 'transparent';
    ctx.fillStyle = '#eaf3ff';
    ctx.fillRect(20, 20, width, 42);
    ctx.strokeStyle = '#3b82f6';
    ctx.strokeRect(20.5, 20.5, width - 1, height - 1);
    ctx.save();
    ctx.beginPath();
    ctx.rect(30, 20, width - 20, height);
    ctx.clip();
    const font = getComputedStyle(document.body).fontFamily;
    ctx.font = `600 13px ${font}`;
    ctx.fillStyle = '#1e3a5f';
    ctx.fillText(fields.find((field) => field[0] === key)?.[1] ?? key, 34, 46);
    ctx.restore();
    canvas.style.cssText = 'position:fixed;left:-10000px;top:0;pointer-events:none;';
    document.body.appendChild(canvas);
    dragPreview = canvas;
    event.dataTransfer?.setDragImage(
      canvas,
      Math.min(
        width / 2 + 20,
        Math.max(20, event.clientX - (header?.getBoundingClientRect().left ?? event.clientX) + 20)
      ),
      36
    );
  }
  /** @param {DragEvent} event */
  function previewPosition(event) {
    if (!dragging) return;
    event.preventDefault();
    if (event.dataTransfer) event.dataTransfer.dropEffect = 'move';
    const region = /** @type {HTMLElement} */ (event.currentTarget);
    const headers = Array.from(region.querySelectorAll('th[data-column]'));
    const index = headers.findIndex((header) => {
      const rect = header.getBoundingClientRect();
      return event.clientX < rect.left + rect.width / 2;
    });
    insertionIndex = index < 0 ? selected.length : index;
    const bounds = region.getBoundingClientRect();
    if (event.clientX > bounds.right - 30) region.scrollLeft += 18;
    else if (event.clientX < bounds.left + 30) region.scrollLeft -= 18;
  }
  /** @param {DragEvent} event */
  function dropColumn(event) {
    if (!dragging) return;
    previewPosition(event);
    const source = selected.indexOf(dragging);
    if (source >= 0 && insertionIndex >= 0) {
      const next = selected.filter((key) => key !== dragging);
      next.splice(insertionIndex > source ? insertionIndex - 1 : insertionIndex, 0, dragging);
      saveColumns(next);
    }
    finishDrag();
  }
  /** @param {DragEvent} event */
  function leaveColumns(event) {
    const region = /** @type {HTMLElement} */ (event.currentTarget);
    if (!region.contains(/** @type {Node | null} */ (event.relatedTarget))) insertionIndex = -1;
  }
  function finishDrag() {
    dragging = '';
    insertionIndex = -1;
    dragPreview?.remove();
    dragPreview = null;
    setTimeout(() => {
      suppressSort = false;
    }, 250);
  }
  /** @param {string} key */
  function sortBy(key) {
    if (suppressSort) return;
    const direction =
      page.url.searchParams.get('sort') === key && page.url.searchParams.get('direction') !== 'desc'
        ? 'desc'
        : 'asc';
    goto(link({ sort: key, direction, offset: null }));
  }
  function saveWidths() {
    writePreference(browserStorage(), widthKey, widths);
  }
  /** @param {string} key @param {number} width */
  function resizeColumn(key, width) {
    if (!Number.isFinite(width)) return;
    widths[key] = Math.min(2000, Math.max(60, Math.round(width)));
    saveWidths();
  }
  /** @param {string} key */
  function fitColumn(key) {
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    if (!context) return 160;
    context.font = '600 13px ' + getComputedStyle(document.body).fontFamily;
    const label = fields.find((field) => field[0] === key)?.[1] ?? key;
    let size = context.measureText(label).width;
    context.font = '600 14px ' + getComputedStyle(document.body).fontFamily;
    for (const contact of data.companies) {
      size = Math.max(
        size,
        context.measureText(String(cell(contact, key)).replace(/\s+/g, ' ')).width
      );
    }
    return Math.max(96, Math.ceil(size) + 40);
  }
  $effect(() => {
    if (!ready || data.view !== 'list') return;
    let changed = false;
    for (const key of selected) {
      if (!widths[key]) {
        widths[key] = fitColumn(key);
        changed = true;
      }
    }
    if (changed) saveWidths();
  });
  function fitVisible() {
    for (const key of selected) widths[key] = fitColumn(key);
    saveWidths();
  }
  /** @param {PointerEvent} event @param {string} key */
  function startResize(event, key) {
    if (event.button !== 0) return;
    event.preventDefault();
    const handle = /** @type {HTMLElement} */ (event.currentTarget);
    const startX = event.clientX;
    const startWidth = widths[key] ?? 160;
    handle.setPointerCapture(event.pointerId);
    const move = (/** @type {PointerEvent} */ e) => {
      widths[key] = Math.min(2000, Math.max(60, Math.round(startWidth + e.clientX - startX)));
    };
    const end = () => {
      handle.removeEventListener('pointermove', move);
      handle.removeEventListener('pointerup', end);
      handle.removeEventListener('pointercancel', end);
      handle.removeEventListener('lostpointercapture', end);
      saveWidths();
    };
    handle.addEventListener('pointermove', move);
    handle.addEventListener('pointerup', end);
    handle.addEventListener('pointercancel', end);
    handle.addEventListener('lostpointercapture', end);
  }
  /** @param {Record<string, string | null>} changes */
  function link(changes) {
    const url = new URL(page.url);
    for (const [key, value] of Object.entries(changes)) {
      if (value === null) url.searchParams.delete(key);
      else url.searchParams.set(key, value);
    }
    return resolve('/accounts') + url.search;
  }
  /** @param {any} contact @param {string} key */
  function cell(contact, key) {
    if (key === 'annual_revenue')
      return contact.annual_revenue === null
        ? '—'
        : money(contact.annual_revenue, contact.currency);
    if (key === 'contacts')
      return (
        contact.contacts
          .map((c) => c.name || [c.first_name, c.last_name].filter(Boolean).join(' '))
          .join(', ') || '—'
      );
    if (key === 'pages') return contact.pages.map((p) => `${p.name}: ${p.url}`).join(', ') || '—';
    if (key === 'account') return contact.account?.name || contact.organization || '—';
    if (key === 'owner')
      return contact.owner
        ? `${contact.owner}${contact.owner_count > 1 ? ` +${contact.owner_count - 1}` : ''}`
        : 'Unassigned';
    if (key === 'is_active' || key === 'do_not_call') return contact[key] ? 'Yes' : 'No';
    if (key.startsWith('custom_fields.')) return columnValue(contact, key, catalog);
    if (key.endsWith('_at')) return contact[key] ? relativeDays(contact[key]) : '—';
    return columnValue(contact, key, catalog);
  }
</script>

<PageHeader compact title={ui('Companies')}>
  {#snippet sub()}<span class="v2-num">{count(data.totals.count)}</span>
    {data.totals.count === 1 ? ui('company') : ui('companies')}{#if data.view === 'pipeline'}
      &nbsp;· <PipelineTotal
        currency={data.org.currency}
        values={data.totals.money_totals}
        label={ui('Total annual revenue')}
      />{/if}{/snippet}
  {#snippet actions()}
    {#if can(page.data.permissions, 'companies', 'create')}<a
        class="v2-btn v2-btn-primary"
        href={resolve('/accounts/new')}><Plus />{ui('New company')}</a
      >{/if}
  {/snippet}
</PageHeader>

<form
  class="contact-filters object-toolbar"
  method="GET"
  action={resolve('/accounts')}
  oninput={filterInput}
  onsubmit={(event) => {
    event.preventDefault();
    updateFilters();
  }}
>
  <input type="hidden" name="view" value={data.view} />
  {#each ['sort', 'direction', 'inactive', 'page_size'] as key}
    {#if page.url.searchParams.get(key)}<input
        type="hidden"
        name={key}
        value={page.url.searchParams.get(key)}
      />{/if}
  {/each}
  <label
    >{ui('Search')}<input
      class="v2-input"
      type="search"
      name="search"
      placeholder={ui('Search companies…')}
      value={filterValues.search ?? ''}
    /></label
  >
  <label
    >{ui('Stage')}<select class="v2-input" name="stage" value={filterValues.stage ?? ''}>
      <option value="">{ui('All stages')}</option>
      {#each data.stages as stage}<option value={stage.value}>{stage.label}</option>{/each}
    </select></label
  >
  <details class="advanced-filters">
    <summary class="v2-btn"
      >{ui('Filters')}{advancedKeys.length ? ` (${advancedKeys.length})` : ''}</summary
    >
    <div class="advanced-panel">
      <label
        >{ui('Add filter')}<select
          class="v2-input"
          aria-label={ui('Add filter')}
          value=""
          onchange={(event) => {
            if (event.currentTarget.value)
              advancedKeys = [...advancedKeys, event.currentTarget.value];
            event.currentTarget.value = '';
          }}
        >
          <option value="">{ui('Choose a property')}</option>
          {#each advancedContactFilters.filter((field) => !advancedKeys.includes(field.key)) as field}
            <option value={field.key}>{ui(field.label)}</option>
          {/each}
        </select></label
      >
      {#each advancedKeys as key (key)}
        {@const field = advancedContactFilters.find((item) => item.key === key)}
        {#if field}
          <div class="advanced-row">
            {#if field.type?.endsWith('range')}
              <fieldset>
                <legend>{ui(field.label)}</legend>
                <label
                  >{ui('From')}<input
                    class="v2-input"
                    type={field.type === 'number-range' ? 'number' : 'date'}
                    name={`${key}__gte`}
                    aria-label={`${ui(field.label)} from`}
                    value={filterValues[`${key}__gte`] ?? ''}
                  /></label
                >
                <label
                  >{ui('To')}<input
                    class="v2-input"
                    type={field.type === 'number-range' ? 'number' : 'date'}
                    name={`${key}__lte`}
                    aria-label={`${ui(field.label)} to`}
                    value={filterValues[`${key}__lte`] ?? ''}
                  /></label
                >
              </fieldset>
            {:else if field.options}
              <label
                >{ui(field.label)}<select
                  class="v2-input"
                  name={key}
                  value={filterValues[key] ?? ''}
                >
                  <option value="">{ui('Any')}</option>
                  {#each field.options as [value, label]}<option {value}>{label}</option>{/each}
                </select></label
              >
            {:else}
              <label
                >{ui(field.label)}<input
                  class="v2-input"
                  name={key}
                  value={filterValues[key] ?? ''}
                /></label
              >
            {/if}
            <button
              class="v2-btn"
              type="button"
              aria-label={`Remove ${ui(field.label)} filter`}
              onclick={() => removeFilter(key)}>×</button
            >
          </div>
        {/if}
      {/each}
    </div>
  </details>
  {#if data.view === 'list'}
    {#if can(page.data.permissions, 'companies', 'export')}<ExportDialog
        endpoint={resolve('/accounts/export')}
        columns={selected}
        rows={data.companies}
        filename="companies.csv"
      />{/if}
  {/if}
  <div class="view-actions">
    <nav class="view-toggle" aria-label={ui('Company views')}>
      <a
        class="v2-btn view-icon"
        class:v2-btn-primary={data.view === 'list'}
        aria-label={ui('List view')}
        title={ui('List view')}
        aria-current={data.view === 'list' ? 'page' : undefined}
        href={link({ view: 'list' })}><List size={18} /></a
      >
      <a
        class="v2-btn view-icon"
        class:v2-btn-primary={data.view === 'pipeline'}
        aria-label={ui('Pipeline view')}
        title={ui('Pipeline view')}
        aria-current={data.view === 'pipeline' ? 'page' : undefined}
        href={link({ view: 'pipeline' })}><Columns3 size={18} /></a
      >
    </nav>
    {#if data.view === 'list'}
      <ColumnPicker
        {fields}
        {selected}
        onToggle={toggleColumn}
        onShowAll={selection.showAll}
        onReset={selection.reset}
      />
    {/if}
  </div>
</form>

{#if filterError}<p role="alert">{filterError}</p>{/if}

<div
  class="v2-scroll"
  class:pipeline-scroll={data.view === 'pipeline'}
  class:list-scroll={data.view !== 'pipeline'}
>
  {#if data.view === 'pipeline'}
    {#if moveError}<p class="table-hint" role="alert">{moveError}</p>{/if}
    <p class="table-hint v2-sub" role="status">{moveStatus}</p>
    <div class="contact-board hdm-board" aria-label={ui('Companies by stage')}>
      {#each data.board as stage (stage.value)}
        <section
          class="stage-column pipeline-column"
          data-tone={pipelineTone(stage.label)}
          class:drop-target={dropStage === stage.value}
          aria-label={stage.label}
          ondragover={(event) => overStage(event, stage.value)}
          ondrop={(event) => dropContact(event, stage.value)}
          ondragleave={(event) => {
            if (!event.currentTarget.contains(/** @type {Node | null} */ (event.relatedTarget)))
              dropStage = '';
          }}
        >
          <header class="pipeline-header">
            <h2>{stage.label}</h2>
            <div class="pipeline-stage-totals">
              <PipelineTotal
                currency={data.org.currency}
                values={stage.moneyTotals}
                label={ui('Total annual revenue')}
              /><span class="pipeline-stage-count">{count(stage.count)}</span>
            </div>
          </header>
          <div class="pipeline-cards">
            {#each stage.contacts as contact (contact.id)}
              <article
                class="contact-card pipeline-card compact-pipeline-card"
                class:card-dragging={draggedContact === contact.id}
                class:card-saving={movingContact === contact.id}
                aria-busy={movingContact === contact.id}
                draggable={!movingContact && can(page.data.permissions, 'companies', 'stage')}
                ondragstart={(event) => startContactDrag(event, contact.id, stage.value)}
                ondragend={endContactDrag}
              >
                <PipelineCardSummary
                  name={contact.name}
                  tags={contact.tags}
                  href={`/accounts/${contact.id}`}
                  email={contact.email}
                  phone={contact.phone}
                  values={contact.annual_revenue === null
                    ? []
                    : [{ amount: contact.annual_revenue, currency: contact.currency }]}
                  valueLabel="Annual revenue"
                  lastActivity={contact.last_activity_at}
                  stageEntered={contact.stage_entered_at}
                  now={clock}
                />
              </article>
            {:else}<p class="pipeline-empty">{ui('No companies')}</p>{/each}
          </div>
          <footer>
            {#if stage.offset > 0}<a
                class="v2-btn"
                aria-label={`Previous ${stage.label} page`}
                href={link({
                  [`${stage.value}_offset`]: String(Math.max(0, stage.offset - data.pageSize))
                })}>{ui('Previous')}</a
              >{/if}
            {#if stage.offset + data.pageSize < stage.count}<a
                class="v2-btn"
                aria-label={`Next ${stage.label} page`}
                href={link({ [`${stage.value}_offset`]: String(stage.offset + data.pageSize) })}
                >{ui('Next')}</a
              >{/if}
          </footer>
        </section>
      {/each}
    </div>
  {:else}
    <!-- svelte-ignore a11y_no_noninteractive_tabindex (Keyboard users need to focus this overflow region to scroll the table.) -->
    <div
      class="contact-table-scroll hdm-list"
      ondragover={previewPosition}
      ondrop={dropColumn}
      ondragleave={leaveColumns}
      role="region"
      aria-label={ui('Company list, horizontally scrollable')}
      tabindex="0"
    >
      <table class="contact-grid" style:width={`${totalWidth}px`}>
        <colgroup
          >{#each orderedFields as [key]}<col style:width={`${widths[key] ?? 160}px`} />{/each}<col
            style:width="120px"
          /></colgroup
        >
        <thead
          ><tr>
            {#each orderedFields as [key, label] (key)}
              <th
                scope="col"
                data-column={key}
                data-field={key}
                class:drag-source={dragging === key}
                class:insert-before={dragging !== '' && insertionIndex === selected.indexOf(key)}
                class:insert-after={dragging !== '' &&
                  insertionIndex === selected.length &&
                  selected.indexOf(key) === selected.length - 1}
                aria-sort={page.url.searchParams.get('sort') === key
                  ? page.url.searchParams.get('direction') === 'desc'
                    ? 'descending'
                    : 'ascending'
                  : 'none'}
              >
                <button
                  class="column-heading"
                  class:dragging={dragging === key}
                  draggable="true"
                  title={legacyFields.some(([id]) => id === key)
                    ? ui('Click to sort; drag to reorder. Alt + arrow keys also move the column.')
                    : ui('Drag to reorder. Alt + arrow keys also move the column.')}
                  onclick={() => {
                    if (legacyFields.some(([id]) => id === key)) sortBy(key);
                  }}
                  ondragstart={(event) => startColumnDrag(event, key)}
                  ondragend={finishDrag}
                  onkeydown={(event) => {
                    if (event.altKey && ['ArrowLeft', 'ArrowRight'].includes(event.key)) {
                      event.preventDefault();
                      moveColumn(key, event.key === 'ArrowLeft' ? -1 : 1);
                    }
                  }}
                >
                  {label}{page.url.searchParams.get('sort') === key
                    ? page.url.searchParams.get('direction') === 'desc'
                      ? ' ↓'
                      : ' ↑'
                    : ''}
                </button>
                <button
                  class="resize-handle"
                  aria-label={ui('Resize {label}', { label })}
                  title={ui('Drag to resize; arrow keys adjust width; double-click to fit content')}
                  onpointerdown={(event) => startResize(event, key)}
                  ondblclick={() => resizeColumn(key, fitColumn(key))}
                  onkeydown={(event) => {
                    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
                      event.preventDefault();
                      resizeColumn(
                        key,
                        (widths[key] ?? 160) + (event.key === 'ArrowRight' ? 10 : -10)
                      );
                    }
                  }}
                ></button>
              </th>
            {/each}<th scope="col">{ui('Actions')}</th>
          </tr></thead
        >
        <tbody>
          {#each data.companies as contact (contact.id)}
            <tr>
              {#each orderedFields as [key] (key)}
                <td
                  class="contact-cell"
                  data-field={key}
                  title={String(cell(contact, key))}
                  class:drag-source={dragging === key}
                  class:insert-before={dragging !== '' && insertionIndex === selected.indexOf(key)}
                  class:insert-after={dragging !== '' &&
                    insertionIndex === selected.length &&
                    selected.indexOf(key) === selected.length - 1}
                >
                  {#if key === 'name'}<a
                      class="v2-row-link v2-table-primary"
                      href={resolve(`/accounts/${contact.id}`)}
                      >{contact.name || `Company · ${contact.id.slice(0, 8)}`}</a
                    >
                  {:else if key === 'stage_label'}<StageProgress
                      stage={contact.stage}
                      label={contact.stage_label}
                      stages={data.stages}
                    />
                  {:else if key === 'email' && contact.email}<a href={`mailto:${contact.email}`}
                      >{contact.email}</a
                    >
                  {:else}{cell(contact, key)}{/if}
                </td>
              {/each}
              <td class="list-row-actions"
                ><a aria-label={`Open ${contact.name}`} href={resolve(`/accounts/${contact.id}`)}
                  >{ui('Open')}</a
                >
                {#if can(page.data.permissions, 'companies', 'edit')}<a
                    aria-label={`Edit ${contact.name}`}
                    href={resolve(`/accounts/${contact.id}/edit`)}>{ui('Edit')}</a
                  >{/if}</td
              >
            </tr>
          {:else}<tr><td colspan={selected.length + 1}>{ui('No companies on this page.')}</td></tr
            >{/each}
        </tbody>
      </table>
    </div>
    <ListPagination
      offset={data.offset}
      pageSize={data.pageSize}
      total={data.totals.count}
      shown={data.companies.length}
    />
  {/if}
</div>

<style>
  .advanced-filters {
    position: relative;
  }
  .advanced-filters summary {
    cursor: pointer;
    list-style: none;
  }
  .advanced-filters summary::-webkit-details-marker {
    display: none;
  }
  .advanced-panel {
    position: absolute;
    z-index: 20;
    top: calc(100% + 8px);
    right: 0;
    padding: var(--crm-space-4);
    width: min(430px, calc(100vw - 48px));
    max-height: 65vh;
    overflow-y: auto;
    background: var(--v2-card, white);
    border: 1px solid var(--v2-line);
    border-radius: var(--crm-radius-md);
    box-shadow: var(--crm-shadow-lg);
    display: grid;
    gap: var(--crm-space-3);
  }
  .advanced-row {
    display: flex;
    gap: var(--crm-space-2);
    align-items: end;
  }
  .advanced-row > label,
  .advanced-row > fieldset {
    flex: 1;
    min-width: 0;
  }
  .advanced-row input {
    min-width: 0;
  }
  @media (max-width: 720px) {
    .advanced-panel {
      position: fixed;
      left: 24px;
      right: 24px;
      top: 20vh;
    }
  }

  .contact-filters label {
    display: flex;
    flex-direction: column;
    gap: var(--crm-space-1);
    font-size: var(--crm-text-xs);
  }
  .contact-filters fieldset {
    display: flex;
    gap: var(--crm-space-2);
    padding: var(--crm-space-2);
    border: 1px solid var(--v2-line);
    border-radius: var(--crm-radius-sm);
  }
  .contact-filters legend {
    font-size: var(--crm-text-xs);
  }
  .contact-filters .v2-input {
    width: auto;
    max-width: 100%;
  }

  .stage-column.drop-target {
    outline: 2px solid var(--crm-info);
    outline-offset: -2px;
    background: var(--crm-info-bg);
  }
  .contact-card[draggable='true'] {
    cursor: grab;
  }
  .contact-card.card-dragging {
    opacity: 0.45;
  }
  .contact-card.card-saving {
    opacity: 0.6;
    cursor: progress;
  }
  .contact-grid .drag-source {
    background: var(--crm-info-bg);
    opacity: 0.5;
  }
  .contact-grid .insert-before {
    box-shadow: inset 3px 0 0 var(--crm-info);
  }
  .contact-grid .insert-after {
    box-shadow: inset -3px 0 0 var(--crm-info);
  }

  .table-hint {
    padding: 0 var(--crm-space-6);
    font-size: var(--crm-text-xs);
  }
  .contact-table-scroll {
    overflow: auto;
    max-width: 100%;
    min-width: 0;
    border: 1px solid var(--v2-line);
    border-radius: var(--crm-radius-md);
  }
  .contact-grid {
    table-layout: fixed;
    border-collapse: collapse;
    background: var(--v2-card);
    font-size: var(--crm-text-sm);
  }
  .contact-grid th,
  .contact-grid td {
    box-sizing: border-box;
    padding: 10px 14px;
    text-align: left;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    border-right: 1px solid var(--v2-line-soft);
    border-bottom: 1px solid var(--v2-line-soft);
  }
  .contact-grid th {
    position: relative;
    font-size: var(--crm-text-sm);
    font-weight: 600;
    color: var(--v2-slate);
  }
  .column-heading {
    width: 100%;
    border: 0;
    padding: 0;
    text-align: left;
    font: inherit;
    color: inherit;
    background: transparent;
    cursor: grab;

    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .contact-grid td {
    height: 44px;
  }
  .contact-grid tbody tr:hover {
    background: var(--v2-hover);
  }
  .contact-cell > a {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .contact-grid a {
    color: inherit;
  }
  .column-heading.dragging {
    opacity: 0.4;
  }
  .resize-handle {
    position: absolute;
    right: 0;
    top: 0;
    bottom: 0;
    width: 9px;
    border: 0;
    padding: 0;
    background: transparent;
    cursor: col-resize;
    touch-action: none;
  }
  .resize-handle:hover,
  .resize-handle:focus-visible {
    background: var(--v2-slate);
    opacity: 0.45;
  }

  .view-actions {
    display: flex;
    align-items: center;
    gap: var(--crm-space-2);
    margin-left: auto;
  }
  .view-toggle {
    display: inline-flex;
    gap: 2px;
  }
  .view-icon {
    width: 36px;
    height: 36px;
    padding: 0;
    justify-content: center;
  }
  .contact-cell {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .contact-board {
    display: flex;
    align-items: flex-start;
    gap: var(--crm-space-4);
    overflow-x: auto;
    padding: var(--crm-space-4) var(--crm-space-6) var(--crm-space-8);
    min-height: 400px;
  }
  .stage-column {
    min-height: 300px;
    flex: 0 0 290px;
    background: var(--crm-canvas);
    border: 1px solid var(--crm-border);
    border-radius: var(--crm-radius-md);
    padding: var(--crm-space-3);
  }
  .stage-column header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 14px;
  }
  .stage-column h2 {
    font-size: var(--crm-text-sm);
    font-weight: 650;
    margin: 0;
  }
  .contact-card {
    background: var(--crm-surface);
    border: 1px solid var(--crm-border);
    border-radius: var(--crm-radius-md);
    padding: 14px;
    margin-bottom: var(--crm-space-3);
  }
  footer {
    display: flex;
    gap: var(--crm-space-2);
    align-items: center;
    flex-wrap: wrap;
  }
</style>
