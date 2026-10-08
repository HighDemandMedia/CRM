<script>
  import { page } from '$app/state';
  import { goto } from '$app/navigation';
  import { useI18n } from '$lib/i18n/context.js';
  import { PAGE_SIZES, paginationHref } from '$lib/v2/pagination.js';
  const { ui, count } = useI18n();
  let { offset, pageSize, total, shown } = $props();
</script>

<nav class="pagination" aria-label={ui('Record pages')}>
  <span class="page-summary" aria-live="polite">
    {ui('Showing')}
    {count(shown ? offset + 1 : 0)}–{count(shown ? offset + shown : 0)}
    {ui('of')}
    {count(total)}
  </span>
  <label class="page-size">
    <span class="rows-label">{ui('Rows per page')}</span>
    <select
      class="v2-input"
      value={pageSize}
      onchange={(event) =>
        goto(paginationHref(page.url, { pageSize: event.currentTarget.value, offset: 0 }), {
          noScroll: true,
          keepFocus: true
        })}
    >
      {#each PAGE_SIZES as size (size)}<option value={size}>{size}</option>{/each}
    </select>
  </label>
  {#if offset > 0}
    <a
      class="v2-btn"
      href={paginationHref(page.url, {
        offset: Math.max(0, offset - pageSize),
        pageSize: undefined
      })}>{ui('Previous')}</a
    >
  {:else}<button type="button" class="v2-btn" disabled>{ui('Previous')}</button>{/if}
  <span
    >{ui('Page')}
    {count(Math.floor(offset / pageSize) + 1)}
    {ui('of')}
    {count(Math.max(1, Math.ceil(total / pageSize)))}</span
  >
  {#if offset + pageSize < total}
    <a
      class="v2-btn"
      href={paginationHref(page.url, { offset: offset + pageSize, pageSize: undefined })}
      >{ui('Next')}</a
    >
  {:else}<button type="button" class="v2-btn" disabled>{ui('Next')}</button>{/if}
</nav>

<style>
  .pagination {
    display: flex;
    align-items: center;
    gap: var(--crm-space-2);
    flex-wrap: wrap;
    padding: var(--crm-space-2) var(--crm-space-3);
    flex: none;
    font-size: var(--crm-text-xs);
  }
  .page-summary {
    margin-right: auto;
  }
  .page-size {
    display: flex;
    align-items: center;
    gap: var(--crm-space-2);
  }
  .page-size select {
    width: auto;
    min-width: 5rem;
  }
  @media (max-width: 600px) {
    .pagination {
      padding: var(--crm-space-2) var(--crm-space-3);
    }
    .page-summary {
      flex-basis: 100%;
    }
    .rows-label {
      position: absolute;
      width: 1px;
      height: 1px;
      padding: 0;
      overflow: hidden;
      clip-path: inset(50%);
      white-space: nowrap;
    }
  }
</style>
