<script>
  import { resolve } from '$app/paths';
  import { asInternalPath } from '$lib/utils/paths.js';
  import HelpHeader from '$lib/help/HelpHeader.svelte';
  import { ArrowLeft, ArrowUpRight } from '@lucide/svelte';
  let { data } = $props();
</script>

<HelpHeader />
<div class="article-scroll">
  <div class="article-layout">
    <article>
      <a class="back" href={resolve('/help/knowledge')}><ArrowLeft size={15} />All guides</a><span
        class="category">{data.article.category}</span
      >
      <h1>{data.article.title}</h1>
      <p class="summary">{data.article.summary}</p>
      {#each data.article.sections as section, index}<section id={`section-${index}`}>
          <h2>{section.title}</h2>
          {#if section.text}<p>{section.text}</p>{/if}{#if section.steps}<ol>
              {#each section.steps as step}<li>{step}</li>{/each}
            </ol>{/if}
        </section>{/each}
      <div class="support">
        <span>Need help with this?</span><a href={resolve('/help')}
          >Contact support <ArrowUpRight size={15} /></a
        >
      </div>
    </article>
    <aside>
      <h2>In this guide</h2>
      <nav aria-label="In this guide">
        {#each data.article.sections as section, index}<a href={`#section-${index}`}
            >{section.title}</a
          >{/each}
      </nav>
      {#if data.related.length}<h2 class="related">Related guides</h2>
        {#each data.related as article}<a
            class="related-link"
            href={resolve(asInternalPath(`/help/knowledge/${article.slug}`))}
            >{article.title}<ArrowUpRight size={13} /></a
          >{/each}{/if}
    </aside>
  </div>
</div>

<style>
  .article-scroll {
    overflow: auto;
    min-height: 0;
    flex: 1;
    scroll-behavior: smooth;
  }
  .article-layout {
    max-width: 1100px;
    margin: 0 auto;
    padding: 28px 28px 50px;
    display: grid;
    grid-template-columns: minmax(0, 730px) 220px;
    gap: 45px;
    align-items: start;
  }
  .back {
    display: flex;
    align-items: center;
    gap: 8px;
    width: fit-content;
    color: var(--v2-slate);
    font-size: 12px;
    text-decoration: none;
    margin-bottom: 27px;
  }
  .category {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.7px;
    color: var(--v2-slate);
  }
  h1 {
    font-size: 28px;
    font-weight: 650;
    line-height: 1.25;
    margin: 12px 0;
  }
  .summary {
    font-size: 15px;
    color: var(--v2-slate);
    line-height: 1.6;
    padding-bottom: 25px;
    border-bottom: 1px solid var(--v2-line);
  }
  section {
    margin-top: 29px;
    scroll-margin-top: 20px;
  }
  section h2 {
    font-size: 17px;
    font-weight: 600;
    margin: 0 0 12px;
  }
  section p,
  li {
    font-size: 14px;
    line-height: 1.9;
    color: var(--v2-ink, #343137);
  }
  ol {
    padding-left: 22px;
    list-style: decimal;
  }
  li {
    padding-left: 5px;
    margin-bottom: 11px;
  }
  aside {
    position: sticky;
    top: 25px;
    border-left: 1px solid var(--v2-line);
    padding-left: 20px;
    margin-top: 45px;
  }
  aside h2 {
    font-size: 12px;
    font-weight: 600;
    margin: 0 0 12px;
  }
  aside nav {
    display: grid;
    gap: 12px;
  }
  aside a {
    font-size: 12px;
    line-height: 1.5;
    color: var(--v2-slate);
    text-decoration: none;
  }
  aside a:hover {
    color: var(--v2-ink, #343137);
  }
  .related {
    margin-top: 30px;
  }
  .related-link {
    display: flex;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 14px;
  }
  .related-link :global(svg) {
    flex-shrink: 0;
  }
  .support {
    display: flex;
    gap: 14px;
    align-items: center;
    flex-wrap: wrap;
    border-top: 1px solid var(--v2-line);
    margin-top: 35px;
    padding-top: 20px;
    font-size: 13px;
    color: var(--v2-slate);
  }
  .support a {
    display: flex;
    gap: 6px;
    align-items: center;
    text-decoration: underline;
    text-underline-offset: 4px;
    color: var(--v2-ink, #343137);
  }
  a:focus-visible {
    outline: 2px solid #81778c;
    outline-offset: 3px;
  }
  @media (max-width: 1000px) {
    .article-layout {
      grid-template-columns: 1fr;
    }
    aside {
      display: none;
    }
  }
  @media (max-width: 600px) {
    .article-layout {
      padding: 23px 16px;
    }
    h1 {
      font-size: 24px;
    }
  }
</style>
