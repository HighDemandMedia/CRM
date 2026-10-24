<script>
  import Notice from '$lib/components/Notice.svelte';
  import { invalidateAll } from '$app/navigation';
  import { page } from '$app/state';
  import { useI18n } from '$lib/i18n/context.js';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import ListPagination from '$lib/v2/components/ListPagination.svelte';
  import OrganizationLimitsDialog from '$lib/v2/components/OrganizationLimitsDialog.svelte';
  const { ui, count, locale } = useI18n();
  let { data, form } = $props();
  let editingLimits = $state(null);
  const capacityMessages = {
    unknown: 'Configure database capacity to enable alerts.',
    normal: 'Database below the planning threshold.',
    plan: 'Plan more database storage. Check disk usage in Render.',
    expand: 'Increase database storage soon. Check disk usage in Render.',
    critical: 'Database capacity is critical. Review and expand storage now.'
  };
  let refreshing = $state(false);
  let refreshError = $state('');
  const columns = [
    ['users', 'Users & invitations'],
    ['contacts', 'Contacts'],
    ['companies', 'Companies'],
    ['deals', 'Deals'],
    ['tasks', 'Tasks'],
    ['tickets', 'Tickets'],
    ['appointments', 'Appointments'],
    ['attachments', 'Attachments']
  ];
  const bytes = (value) => {
    if (value == null) return ui('Unavailable');
    const unit = value >= 1000000000 ? 'GB' : 'MB';
    const divisor = unit === 'GB' ? 1000000000 : 1000000;
    return `${new Intl.NumberFormat(locale(), { maximumFractionDigits: 2 }).format(value / divisor)} ${unit}`;
  };
  function used(org, key) {
    return key === 'users' ? org.reserved_users : org[key];
  }
  function limitStatus(org, key) {
    const maximum = org.limits[key];
    if (maximum == null) return '';
    if (used(org, key) >= maximum) return 'full';
    return used(org, key) >= maximum * 0.8 ? 'warning' : '';
  }
  async function refresh() {
    refreshing = true;
    refreshError = '';
    try {
      await invalidateAll();
    } catch {
      refreshError = ui('Could not load usage.');
    } finally {
      refreshing = false;
    }
  }
</script>

<svelte:head><title>{ui('Platform usage')} · HDM CRM</title></svelte:head>
<PageHeader title={ui('Platform usage')}>
  {#snippet actions()}
    <button class="v2-btn" onclick={refresh} disabled={refreshing} aria-busy={refreshing}>
      {ui(refreshing ? 'Loading…' : 'Refresh')}
    </button>
  {/snippet}
</PageHeader>
<div class="usage-page" aria-busy={refreshing}>
  {#if form?.limitsSaved}<Notice tone="success" message={ui('Limits saved.')} />{/if}
  {#if data.usageError || refreshError}
    <Notice message={ui(data.usageError || refreshError)} />
  {/if}
  {#if data.usage}
    {@const usage = data.usage}
    <div class="metrics">
      <article class="count-metric">
        <h2>{ui('Organizations')}</h2>
        <strong>{count(usage.organizations)}</strong>
      </article>
      <article class="count-metric">
        <h2>{ui('Active user accounts')}</h2>
        <strong>{count(usage.active_users)}</strong>
      </article>
      <article class="database-metric">
        <h2>{ui('Database size')}</h2>
        <span class="database-environment">{ui(usage.database.environment)}</span>
        <dl class="database-space">
          <div>
            <dt>{ui('Total')}</dt>
            <dd>
              {usage.database.total_bytes == null
                ? ui('Not configured')
                : bytes(usage.database.total_bytes)}
            </dd>
          </div>
          <div>
            <dt>{ui('Used')}</dt>
            <dd>{bytes(usage.database.bytes)}</dd>
          </div>
          <div>
            <dt>{ui('Available (estimated)')}</dt>
            <dd>{bytes(usage.database.remaining_estimated_bytes)}</dd>
          </div>
        </dl>
      </article>
    </div>
    <section
      class="capacity-alert"
      data-status={usage.database.capacity_status}
      aria-label={ui('Capacity alerts')}
    >
      <h2>
        {ui('Capacity alerts')}{#if usage.database.used_percent != null}
          · {count(usage.database.used_percent)}%{/if}
      </h2>
      <p>{ui(capacityMessages[usage.database.capacity_status] || capacityMessages.unknown)}</p>
      <p class="thresholds">{ui('Database: plan at 70% · expand at 80% · urgent at 90%.')}</p>
    </section>
    <section class="organizations" aria-label={ui('Usage by organization')}>
      <div class="table-heading">
        <h2>{ui('Usage by organization')}</h2>
        <form method="GET">
          <label class="sr-only" for="usage-search">{ui('Search organizations')}</label>
          <input
            id="usage-search"
            class="v2-input"
            name="q"
            type="search"
            maxlength="100"
            placeholder={ui('Search organizations')}
            value={page.url.searchParams.get('q') || ''}
          />
          <button class="v2-btn" type="submit">{ui('Search')}</button>
        </form>
      </div>
      <div class="table-scroll" role="region" aria-label={ui('Organization usage table')}>
        <table>
          <thead
            ><tr
              ><th scope="col">{ui('Organization')}</th><th scope="col">{ui('Status')}</th
              >{#each columns as [key, label] (key)}<th scope="col" class="number">{ui(label)}</th
                >{/each}<th scope="col">{ui('Limits')}</th></tr
            ></thead
          >
          <tbody>
            {#each usage.results as org (org.id)}
              <tr
                ><th scope="row">{org.name}</th><td>{ui(org.status)}</td
                >{#each columns as [key] (key)}<td
                    class="number"
                    data-limit={limitStatus(org, key)}
                  >
                    {count(used(org, key))}{#if org.limits[key] != null}<span class="maximum">
                        / {count(org.limits[key])}</span
                      >{/if}
                  </td>{/each}<td
                  ><button
                    type="button"
                    class="v2-btn"
                    aria-label={`${ui('Edit limits')}: ${org.name}`}
                    onclick={() => (editingLimits = org)}>{ui('Edit limits')}</button
                  ></td
                ></tr
              >
            {:else}<tr
                ><td colspan={columns.length + 3} class="empty">{ui('No organizations found.')}</td
                ></tr
              >{/each}
          </tbody>
        </table>
      </div>
      <ListPagination
        offset={usage.offset}
        pageSize={usage.page_size}
        total={usage.count}
        shown={usage.results.length}
      />
    </section>
    <section class="infrastructure" aria-label={ui('Infrastructure')}>
      <article>
        <h2>{ui('Render · Database and services')}</h2>
        <p>
          {ui('Check total disk, CPU and memory in Render.')}
        </p>
        <a
          class="v2-btn"
          href="https://dashboard.render.com/"
          target="_blank"
          rel="noopener noreferrer">{ui('Open Render')} ↗</a
        >
      </article>
      <article>
        <h2>{ui('AWS · Files and costs')}</h2>
        <p>
          {ui('File storage and monthly costs.')}
        </p>
        <a
          class="v2-btn"
          href="https://s3.console.aws.amazon.com/s3/home"
          target="_blank"
          rel="noopener noreferrer">{ui('Open S3')} ↗</a
        >
        <a
          class="v2-btn"
          href="https://console.aws.amazon.com/billing/home#/budgets"
          target="_blank"
          rel="noopener noreferrer">{ui('Open budgets')} ↗</a
        >
      </article>
    </section>
  {/if}
</div>
{#if editingLimits}
  <OrganizationLimitsDialog organization={editingLimits} onclose={() => (editingLimits = null)} />
{/if}

<style>
  .usage-page {
    flex: 1;
    min-height: 0;
    min-width: 0;
    overflow-y: auto;
    padding: var(--crm-space-4);
  }
  .metrics,
  .infrastructure {
    display: grid;
    gap: var(--crm-space-3);
  }
  .metrics {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) minmax(0, 2.5fr);
    align-items: start;
  }
  .count-metric {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--crm-space-3);
  }
  .count-metric h2 {
    margin: 0;
  }
  .database-metric h2 {
    display: inline;
    margin-right: var(--crm-space-2);
  }
  article,
  .organizations {
    border: 1px solid var(--v2-line);
    border-radius: var(--crm-radius-md);
    background: var(--crm-surface);
  }
  article {
    padding: var(--crm-space-4);
  }
  h2 {
    font-size: var(--crm-text-sm);
    font-weight: 600;
    margin: 0 0 var(--crm-space-3);
  }
  strong {
    display: block;
    font-size: var(--crm-text-xl);
    font-variant-numeric: tabular-nums;
  }
  article p {
    color: var(--v2-slate);
    font-size: var(--crm-text-sm);
    line-height: 1.6;
  }
  .database-environment {
    color: var(--v2-slate);
    font-size: var(--crm-text-sm);
  }
  .database-space {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: var(--crm-space-3);
    margin: var(--crm-space-3) 0 0;
    font-size: var(--crm-text-sm);
  }
  .database-space div {
    min-width: 0;
    overflow-wrap: anywhere;
  }
  .database-space dd {
    margin: 0;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
    margin-top: var(--crm-space-1);
  }
  .capacity-alert {
    margin-top: var(--crm-space-3);
    padding: var(--crm-space-4);
    border: 1px solid var(--v2-line);
    border-radius: var(--crm-radius-md);
    background: var(--crm-surface);
  }
  .capacity-alert h2,
  .capacity-alert p {
    margin: 0;
    font-size: var(--crm-text-sm);
    line-height: 1.6;
  }
  .capacity-alert .thresholds {
    margin-top: var(--crm-space-2);
    color: var(--v2-slate);
  }
  .capacity-alert[data-status='plan'],
  .capacity-alert[data-status='expand'] {
    background: var(--crm-warning-bg);
    color: var(--crm-warning);
    border-color: currentColor;
  }
  .capacity-alert[data-status='critical'] {
    background: var(--crm-danger-bg);
    color: var(--crm-danger);
    border-color: currentColor;
  }
  .organizations {
    margin-top: var(--crm-space-3);
    overflow: hidden;
  }
  .table-heading {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: var(--crm-space-3);
    padding: var(--crm-space-4);
  }
  .table-heading h2 {
    margin: 0;
  }
  form {
    display: flex;
    gap: var(--crm-space-2);
    max-width: 100%;
  }
  input {
    min-width: 0;
  }
  .table-scroll {
    overflow-x: auto;
  }
  table {
    border-collapse: collapse;
    width: 100%;
    font-size: var(--crm-text-xs);
  }
  th,
  td {
    text-align: left;
    padding: var(--crm-space-3);
    border-bottom: 1px solid var(--v2-line);
  }
  thead {
    background: var(--crm-canvas);
  }
  tbody th {
    min-width: 12rem;
    max-width: 20rem;
    overflow-wrap: anywhere;
  }
  .number {
    text-align: right;
    font-variant-numeric: tabular-nums;
  }
  .number[data-limit='full'] {
    color: var(--crm-danger);
    background: var(--crm-danger-bg);
    font-weight: 600;
  }
  .number[data-limit='warning'] {
    color: var(--crm-warning);
    background: var(--crm-warning-bg);
  }
  .maximum {
    white-space: nowrap;
  }
  .empty {
    padding: var(--crm-space-6);
    text-align: center;
  }
  .infrastructure {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    margin-top: var(--crm-space-3);
  }
  .infrastructure a {
    margin-top: var(--crm-space-2);
  }
  @container crm-workspace (max-width: 900px) {
    .metrics {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    .database-metric {
      grid-column: 1 / -1;
    }
  }
  @media (max-width: 767px) {
    .usage-page {
      padding: var(--crm-space-4);
    }
    .infrastructure {
      grid-template-columns: 1fr;
    }
  }
</style>
