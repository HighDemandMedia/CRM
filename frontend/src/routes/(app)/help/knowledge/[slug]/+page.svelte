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
    gap: var(--crm-space-2);
    width: fit-content;
    color: var(--v2-slate);
    font-size: var(--crm-text-xs);
    text-decoration: none;
    margin-bottom: 27px;
  }
  .category {
    font-size: var(--crm-text-xs);
    text-transform: uppercase;
    letter-spacing: 0.7px;
    color: var(--v2-slate);
  }
  h1 {
    font-size: var(--crm-text-2xl);
    font-weight: 650;
    line-height: 1.25;
    margin: var(--crm-space-3) 0;
  }
  .summary {
    font-size: var(--crm-text-sm);
    color: var(--v2-slate);
    line-height: 1.6;
    padding-bottom: 25px;
    border-bottom: 1px solid var(--v2-line);
  }
  section {
    margin-top: 29px;
    scroll-margin-top: var(--crm-space-5);
  }
  section h2 {
    font-size: var(--crm-text-base);
    font-weight: 600;
    margin: 0 0 var(--crm-space-3);
  }
  section p,
  li {
    font-size: var(--crm-text-sm);
    line-height: 1.9;
    color: var(--v2-ink, var(--crm-text));
  }
  ol {
    padding-left: var(--crm-space-6);
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
    padding-left: var(--crm-space-5);
    margin-top: 45px;
  }
  aside h2 {
    font-size: var(--crm-text-xs);
    font-weight: 600;
    margin: 0 0 var(--crm-space-3);
  }
  aside nav {
    display: grid;
    gap: var(--crm-space-3);
  }
  aside a {
    font-size: var(--crm-text-xs);
    line-height: 1.5;
    color: var(--v2-slate);
    text-decoration: none;
  }
  aside a:hover {
    color: var(--v2-ink, var(--crm-text));
  }
  .related {
    margin-top: 30px;
  }
  .related-link {
    display: flex;
    justify-content: space-between;
    gap: var(--crm-space-2);
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
    padding-top: var(--crm-space-5);
    font-size: var(--crm-text-sm);
    color: var(--v2-slate);
  }
  .support a {
    display: flex;
    gap: 6px;
    align-items: center;
    text-decoration: underline;
    text-underline-offset: 4px;
    color: var(--v2-ink, var(--crm-text));
  }
  a:focus-visible {
    outline: 2px solid var(--crm-focus);
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
      padding: 23px var(--crm-space-4);
    }
    h1 {
      font-size: var(--crm-text-xl);
    }
  }
</style>
