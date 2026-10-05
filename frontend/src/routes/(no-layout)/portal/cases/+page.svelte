<script>
  /**
   * Built for a 390px phone first. The list is a stack of cards rather than a
   * table, because a customer has a handful of requests and a table of six
   * columns is a desktop answer to a phone question.
   */
  import { enhance } from '$app/forms';
  import { resolve } from '$app/paths';
  import PortalShell from '$lib/v2/components/PortalShell.svelte';

  let { data, form } = $props();

  let composing = $state(false);

  /**
   * Deflection: show the answer before the request is sent.
   *
   * Debounced so a normal typing speed produces one request per pause rather
   * than one per keystroke, and sequenced so a slow early response cannot
   * overwrite the results of a later query.
   */
  let summary = $state('');
  let suggestions = $state([]);
  let latestQuery = 0;
  let debounce;

  function findAnswers() {
    clearTimeout(debounce);
    const query = summary.trim();
    if (query.length < 3) {
      suggestions = [];
      return;
    }
    debounce = setTimeout(async () => {
      const ticket = ++latestQuery;
      const response = await fetch(
        `${resolve('/portal/articles/suggestions')}?q=${encodeURIComponent(query)}`
      );
      if (!response.ok) return;
      const body = await response.json();
      if (ticket === latestQuery) suggestions = body.articles ?? [];
    }, 300);
  }

  const FILTERS = [
    { value: '', label: 'All' },
    { value: 'New', label: 'New' },
    { value: 'Pending', label: 'Pending' },
    { value: 'Closed', label: 'Closed' }
  ];

  const OPEN_STATUSES = new Set(['New', 'Assigned', 'Pending']);

  function formatDate(value) {
    if (!value) return '';
    return new Date(value).toLocaleDateString(undefined, {
      day: 'numeric',
      month: 'short',
      year: 'numeric'
    });
  }
</script>

<svelte:head>
  <title>Your support requests</title>
</svelte:head>

<PortalShell>
  <header class="head">
    <h1>Your requests</h1>
    <div class="actions">
      <a class="btn" href={resolve('/portal/articles')}>Help</a>
      <button type="button" onclick={() => (composing = !composing)}>
        {composing ? 'Cancel' : 'New request'}
      </button>
    </div>
  </header>

  {#if composing}
    <form method="POST" action="?/create" use:enhance class="compose">
      <label for="name">What do you need help with?</label>
      <input
        id="name"
        name="name"
        required
        placeholder="Short summary"
        bind:value={summary}
        oninput={findAnswers}
      />

      {#if suggestions.length > 0}
        <aside class="deflect">
          <p class="deflect-head">These might already answer it</p>
          <ul>
            {#each suggestions as article (article.id)}
              <li>
                <a href={resolve(`/portal/articles/${article.id}`)}>
                  <span class="deflect-title">{article.title}</span>
                  <span class="deflect-snippet">{article.snippet}</span>
                </a>
              </li>
            {/each}
          </ul>
        </aside>
      {/if}

      <label for="description">Any detail that would help</label>
      <textarea id="description" name="description" rows="4"></textarea>

      <label for="priority">How urgent is it?</label>
      <select id="priority" name="priority">
        <option value="Low">Low</option>
        <option value="Normal" selected>Normal</option>
        <option value="High">High</option>
      </select>

      {#if form?.error}<p class="err">{form.error}</p>{/if}
      <button type="submit" class="primary">Send request</button>
    </form>
  {/if}

  <nav class="filters">
    {#each FILTERS as filter (filter.value)}
      <a
        href={resolve(filter.value ? `/portal/cases?status=${filter.value}` : '/portal/cases')}
        class:on={data.status === filter.value}
      >
        {filter.label}
      </a>
    {/each}
  </nav>

  {#if data.cases.length === 0}
    <p class="empty">
      {data.status
        ? `You have no ${data.status.toLowerCase()} requests.`
        : 'You have not sent us any requests yet.'}
    </p>
  {:else}
    <ul class="list">
      {#each data.cases as item (item.id)}
        <li>
          <a href={resolve(`/portal/cases/${item.id}`)}>
            <span class="name">{item.name}</span>
            <span class="meta">
              <span class="tag" class:open={OPEN_STATUSES.has(item.status)}>{item.status}</span>
              <span class="when">{formatDate(item.created_at)}</span>
            </span>
          </a>
        </li>
      {/each}
    </ul>
  {/if}
</PortalShell>

<style>
  .head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--crm-space-3);
    margin-bottom: 18px;
  }
  h1 {
    margin: 0;
    font-size: var(--crm-text-xl);
    font-weight: 600;
  }
  button {
    min-height: 44px;
    padding: 0 14px;
    font-size: var(--crm-text-sm);
    border: 1px solid var(--v2-rule, var(--crm-control-border));
    border-radius: var(--crm-radius-md);
    background: none;
    cursor: pointer;
  }
  .actions {
    display: flex;
    align-items: center;
    gap: var(--crm-space-2);
  }
  .btn {
    display: inline-flex;
    align-items: center;
    min-height: 44px;
    padding: 0 14px;
    font-size: var(--crm-text-sm);
    border: 1px solid var(--v2-rule, var(--crm-control-border));
    border-radius: var(--crm-radius-md);
    text-decoration: none;
    color: inherit;
  }
  .deflect {
    margin-top: 14px;
    padding: var(--crm-space-3) 14px;
    border: 1px solid var(--v2-rule, var(--crm-border));
    border-radius: var(--crm-radius-md);
    background: var(--v2-rule, var(--crm-canvas));
  }
  .deflect-head {
    margin: 0 0 var(--crm-space-2);
    font-size: var(--crm-text-sm);
    font-weight: 500;
    color: var(--v2-slate, var(--crm-text-muted));
  }
  .deflect ul {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 6px;
  }
  .deflect a {
    display: block;
    /* Padding rather than min-height: these stack, and 44px of dead space per
       row pushes the Send button off a 390px screen. */
    padding: 10px var(--crm-space-3);
    border-radius: var(--crm-radius-md);
    background: var(--v2-paper, var(--crm-surface));
    text-decoration: none;
    color: inherit;
  }
  .deflect-title {
    display: block;
    font-size: var(--crm-text-sm);
    font-weight: 500;
  }
  .deflect-snippet {
    margin-top: 2px;
    font-size: var(--crm-text-sm);
    line-height: 1.45;
    color: var(--v2-slate, var(--crm-text-muted));
    /* Snippets run to 200 characters; two lines is the most a phone can give
       them without burying the form. */
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  button.primary {
    width: 100%;
    margin-top: 14px;
    border: 0;
    background: var(--v2-ink, var(--crm-text));
    color: var(--crm-surface);
  }
  .compose {
    border: 1px solid var(--v2-rule, var(--crm-border));
    border-radius: var(--crm-radius-md);
    padding: 18px var(--crm-space-4);
    margin-bottom: var(--crm-space-5);
  }
  .compose label {
    display: block;
    margin: var(--crm-space-3) 0 6px;
    font-size: var(--crm-text-sm);
    font-weight: 500;
  }
  .compose label:first-child {
    margin-top: 0;
  }
  input,
  textarea,
  select {
    width: 100%;
    box-sizing: border-box;
    /* 16px stops iOS Safari zooming the viewport on focus. */
    font-size: var(--crm-text-base);
    padding: 11px;
    border: 1px solid var(--v2-rule, var(--crm-control-border));
    border-radius: var(--crm-radius-md);
  }
  .filters {
    display: flex;
    gap: var(--crm-space-2);
    margin-bottom: var(--crm-space-4);
    /* Four short filters fit at 390px; scrolling is the fallback, not the plan. */
    overflow-x: auto;
  }
  .filters a {
    /* inline-flex plus min-height rather than padding alone: padding put these
       at 39px, which measured under the 44px floor at 390px. */
    display: inline-flex;
    align-items: center;
    min-height: 44px;
    padding: 0 var(--crm-space-4);
    border-radius: var(--crm-radius-full);
    border: 1px solid var(--v2-rule, var(--crm-border));
    font-size: var(--crm-text-sm);
    text-decoration: none;
    color: inherit;
    white-space: nowrap;
  }
  .filters a.on {
    background: var(--v2-ink, var(--crm-text));
    color: var(--crm-surface);
    border-color: var(--v2-ink, var(--crm-text));
  }
  .list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 10px;
  }
  .list a {
    display: block;
    padding: 14px var(--crm-space-4);
    border: 1px solid var(--v2-rule, var(--crm-border));
    border-radius: var(--crm-radius-md);
    text-decoration: none;
    color: inherit;
  }
  .name {
    display: block;
    font-weight: 500;
    margin-bottom: var(--crm-space-2);
  }
  .meta {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: var(--crm-text-sm);
    color: var(--v2-slate, var(--crm-text-muted));
  }
  .tag {
    padding: 2px 9px;
    border-radius: var(--crm-radius-full);
    background: var(--v2-rule, var(--crm-surface-secondary));
  }
  .tag.open {
    background: var(--v2-moss-bg, var(--crm-success-bg));
  }
  .empty {
    color: var(--v2-slate, var(--crm-text-muted));
    font-size: var(--crm-text-sm);
  }
  .err {
    margin: 10px 0 0;
    color: var(--v2-rust, var(--crm-danger));
    font-size: var(--crm-text-sm);
  }
</style>
