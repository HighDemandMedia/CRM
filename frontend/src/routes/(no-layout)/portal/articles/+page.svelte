<script>
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();

  /**
   * Built for a 390px phone first, and a stack of cards for the same reason the
   * requests list is one: a customer reads a handful of these, not a table.
   *
   * The search box is a plain GET form. It works before the page hydrates, and
   * a customer looking for an answer is exactly the person most likely to be on
   * a slow connection.
   */
  import { resolve } from '$app/paths';
  import PortalShell from '$lib/v2/components/PortalShell.svelte';

  let { data } = $props();
</script>

<svelte:head>
  <title>{ui('Help articles')}</title>
</svelte:head>

<PortalShell>
  <header class="head">
    <h1>{ui('Help articles')}</h1>
    <a class="btn" href={resolve('/portal/cases')}>{ui('Your requests')}</a>
  </header>

  <form method="GET" class="find">
    <label class="sr-only" for="search">{ui('Search help articles')}</label>
    <input id="search" name="search" value={data.search} placeholder={ui('Search for an answer')} />
    <button type="submit">{ui('Search')}</button>
  </form>

  {#if data.articles.length === 0}
    <p class="empty">
      {data.search
        ? `Nothing matches "${data.search}". Try a different word, or send us a request.`
        : ui('There are no help articles yet.')}
    </p>
  {:else}
    <ul class="list">
      {#each data.articles as article (article.id)}
        <li>
          <a href={resolve(`/portal/articles/${article.id}`)}>{article.title}</a>
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
    white-space: nowrap;
  }
  .find {
    display: flex;
    gap: var(--crm-space-2);
    margin-bottom: var(--crm-space-5);
  }
  input {
    flex: 1;
    min-width: 0;
    box-sizing: border-box;
    /* 16px stops iOS Safari zooming the viewport on focus. */
    font-size: var(--crm-text-base);
    padding: 11px;
    border: 1px solid var(--v2-rule, var(--crm-control-border));
    border-radius: var(--crm-radius-md);
  }
  .find button {
    min-height: 44px;
    padding: 0 14px;
    font-size: var(--crm-text-sm);
    border: 0;
    border-radius: var(--crm-radius-md);
    background: var(--v2-ink, var(--crm-text));
    color: var(--crm-surface);
    cursor: pointer;
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
    font-weight: 500;
  }
  .empty {
    color: var(--v2-slate, var(--crm-text-muted));
    font-size: var(--crm-text-sm);
  }
  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  }
</style>
