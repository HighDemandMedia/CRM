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
    padding: 28px 28px 40px;
    margin: 0 auto;
  }
  .intro {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 22px;
    flex-wrap: wrap;
  }
  h2 {
    font-size: 21px;
    font-weight: 650;
    margin: 0;
  }
  .intro p {
    font-size: 13px;
    color: var(--v2-slate);
    margin: 8px 0 0;
  }
  .search {
    display: flex;
    align-items: center;
    gap: 9px;
    min-width: 260px;
    padding: 11px 13px;
    background: #fff;
    border: 1px solid var(--v2-line);
    border-radius: 9px;
    color: var(--v2-slate);
  }
  .search input {
    min-width: 0;
    width: 100%;
    outline: 0;
    background: none;
    font-size: 13px;
  }
  .search:focus-within {
    outline: 2px solid #81778c;
  }
  .categories {
    display: flex;
    flex-wrap: wrap;
    gap: 7px;
    margin: 24px 0;
  }
  .categories button {
    font-size: 12px;
    padding: 8px 12px;
    border-radius: 7px;
    color: var(--v2-slate);
    border: 1px solid transparent;
  }
  .categories button.active {
    background: #eae6ee;
    color: #3d3545;
    border-color: #dbd5e1;
  }
  .articles {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(270px, 1fr));
    gap: 15px;
  }
  .article-card {
    display: block;
    background: #fff;
    border: 1px solid var(--v2-line);
    border-radius: 11px;
    padding: 20px;
    text-decoration: none;
    color: inherit;
  }
  .article-card:hover {
    border-color: #a69caf;
  }
  .category {
    text-transform: uppercase;
    letter-spacing: 0.6px;
    font-size: 10px;
    color: var(--v2-slate);
  }
  .article-card h3 {
    display: flex;
    justify-content: space-between;
    gap: 14px;
    font-size: 15px;
    font-weight: 600;
    margin: 12px 0 9px;
    line-height: 1.45;
  }
  .article-card h3 :global(svg) {
    flex-shrink: 0;
    color: var(--v2-slate);
  }
  .article-card p {
    font-size: 12px;
    line-height: 1.6;
    margin: 0;
    color: var(--v2-slate);
  }
  .contact-prompt {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    align-items: center;
    border-top: 1px solid var(--v2-line);
    padding-top: 23px;
    margin-top: 27px;
    font-size: 13px;
    color: var(--v2-slate);
  }
  .contact-prompt a {
    display: flex;
    align-items: center;
    gap: 6px;
    color: var(--v2-ink, #343137);
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
    font-size: 16px;
    margin: 12px 0;
  }
  .empty p {
    font-size: 13px;
  }
  a:focus-visible,
  button:focus-visible {
    outline: 2px solid #81778c;
    outline-offset: 3px;
  }
  @media (max-width: 600px) {
    .knowledge {
      padding: 22px 16px;
    }
    .search {
      width: 100%;
    }
    .articles {
      grid-template-columns: 1fr;
    }
  }
</style>
