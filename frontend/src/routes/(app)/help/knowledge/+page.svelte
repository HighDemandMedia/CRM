<script>
  import { resolve } from '$app/paths';
  import { asInternalPath } from '$lib/utils/paths.js';
  import HelpHeader from '$lib/help/HelpHeader.svelte';
  import { articles, categories } from '$lib/help/articles.js';
  import { Search, ArrowUpRight, BookOpen } from '@lucide/svelte';
  let query = $state(''),
    category = $state('All');
  let filtered = $derived(
    articles.filter(
      (article) =>
        (category === 'All' || article.category === category) &&
        [
          article.title,
          article.summary,
          ...article.sections.flatMap((section) => [
            section.title,
            section.text || '',
            ...(section.steps || [])
          ])
        ]
          .join(' ')
          .toLowerCase()
          .includes(query.trim().toLowerCase())
    )
  );
</script>

<HelpHeader />
<div class="knowledge-scroll">
  <div class="knowledge">
    <div class="intro">
      <div>
        <h2>Learn your CRM</h2>
        <p>Guides for the High Demand Media workflows, settings and tools.</p>
      </div>
      <label class="search"
        ><Search size={17} /><input
          type="search"
          aria-label="Search guides"
          placeholder="Search guides…"
          bind:value={query}
        /></label
      >
    </div>
    <div class="categories" role="group" aria-label="Guide categories">
      {#each ['All', ...categories] as item}<button
          class:active={category === item}
          aria-pressed={category === item}
          onclick={() => (category = item)}>{item}</button
        >{/each}
    </div>
    <div class="articles">
      {#each filtered as article}<a
          class="article-card"
          href={resolve(asInternalPath(`/help/knowledge/${article.slug}`))}
          ><span class="category">{article.category}</span>
          <h3>{article.title}<ArrowUpRight size={16} /></h3>
          <p>{article.summary}</p></a
        >{:else}<div class="empty">
          <BookOpen size={26} />
          <h3>No guides found</h3>
          <p>Try another word or category.</p>
        </div>{/each}
    </div>
    <div class="contact-prompt">
      <span>Still need assistance?</span><a href={resolve('/help')}
        >Ask the High Demand Media team <ArrowUpRight size={15} /></a
      >
    </div>
  </div>
</div>

<style>
  .knowledge-scroll {
    overflow: auto;
    min-height: 0;
    flex: 1;
  }
  .knowledge {
    max-width: 1200px;
    padding: 28px 28px var(--crm-space-10);
    margin: 0 auto;
  }
  .intro {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--crm-space-6);
    flex-wrap: wrap;
  }
  h2 {
    font-size: var(--crm-text-xl);
    font-weight: 650;
    margin: 0;
  }
  .intro p {
    font-size: var(--crm-text-sm);
    color: var(--v2-slate);
    margin: var(--crm-space-2) 0 0;
  }
  .search {
    display: flex;
    align-items: center;
    gap: 9px;
    min-width: 260px;
    padding: 11px 13px;
    background: var(--crm-surface);
    border: 1px solid var(--v2-line);
    border-radius: var(--crm-radius-md);
    color: var(--v2-slate);
  }
  .search input {
    min-width: 0;
    width: 100%;
    outline: 0;
    background: none;
    font-size: var(--crm-text-sm);
  }
  .search:focus-within {
    outline: 2px solid var(--crm-focus);
  }
  .categories {
    display: flex;
    flex-wrap: wrap;
    gap: 7px;
    margin: var(--crm-space-6) 0;
  }
  .categories button {
    font-size: var(--crm-text-xs);
    padding: var(--crm-space-2) var(--crm-space-3);
    border-radius: var(--crm-radius-md);
    color: var(--v2-slate);
    border: 1px solid transparent;
  }
  .categories button.active {
    background: var(--crm-surface-selected);
    color: var(--crm-text);
    border-color: var(--crm-border);
  }
  .articles {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(270px, 1fr));
    gap: 15px;
  }
  .article-card {
    display: block;
    background: var(--crm-surface);
    border: 1px solid var(--v2-line);
    border-radius: var(--crm-radius-lg);
    padding: var(--crm-space-5);
    text-decoration: none;
    color: inherit;
  }
  .article-card:hover {
    border-color: var(--crm-text-muted);
  }
  .category {
    text-transform: uppercase;
    letter-spacing: 0.6px;
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
  }
  .article-card h3 {
    display: flex;
    justify-content: space-between;
    gap: 14px;
    font-size: var(--crm-text-sm);
    font-weight: 600;
    margin: var(--crm-space-3) 0 9px;
    line-height: 1.45;
  }
  .article-card h3 :global(svg) {
    flex-shrink: 0;
    color: var(--v2-slate);
  }
  .article-card p {
    font-size: var(--crm-text-xs);
    line-height: 1.6;
    margin: 0;
    color: var(--v2-slate);
  }
  .contact-prompt {
    display: flex;
    flex-wrap: wrap;
    gap: var(--crm-space-3);
    align-items: center;
    border-top: 1px solid var(--v2-line);
    padding-top: 23px;
    margin-top: 27px;
    font-size: var(--crm-text-sm);
    color: var(--v2-slate);
  }
  .contact-prompt a {
    display: flex;
    align-items: center;
    gap: 6px;
    color: var(--v2-ink, var(--crm-text));
    text-decoration: underline;
    text-underline-offset: 4px;
  }
  .empty {
    grid-column: 1/-1;
    padding: 55px;
    text-align: center;
    color: var(--v2-slate);
  }
  .empty :global(svg) {
    margin: auto;
  }
  .empty h3 {
    font-size: var(--crm-text-base);
    margin: var(--crm-space-3) 0;
  }
  .empty p {
    font-size: var(--crm-text-sm);
  }
  a:focus-visible,
  button:focus-visible {
    outline: 2px solid var(--crm-focus);
    outline-offset: 3px;
  }
  @media (max-width: 600px) {
    .knowledge {
      padding: var(--crm-space-6) var(--crm-space-4);
    }
    .search {
      width: 100%;
    }
    .articles {
      grid-template-columns: 1fr;
    }
  }
</style>
