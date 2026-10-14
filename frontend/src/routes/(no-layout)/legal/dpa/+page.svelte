<script>
  import '../../../../app.css';
  import { resolve } from '$app/paths';
  import { legalLinks } from '$lib/legal.js';
  let { data } = $props();
  const es = $derived(data.language === 'es');
  const privacy = $derived(legalLinks(data.language).privacy);
</script>

<svelte:head>
  <title>{data.document.title} · High Demand Media</title>
  <meta name="robots" content="noindex, nofollow" />
</svelte:head>

<main class="agreement" lang={data.language}>
  <header>
    <p>High Demand Media</p>
    <nav aria-label={es ? 'Idioma' : 'Language'}>
      <a href={resolve('/legal/dpa?lang=en')} aria-current={!es ? 'page' : undefined}>EN</a>
      <a href={resolve('/legal/dpa?lang=es')} aria-current={es ? 'page' : undefined}>ES</a>
    </nav>
  </header>
  {#if data.draft}<p class="draft" role="note">
      {es ? 'Borrador para revisión — todavía no vigente' : 'Draft for review — not yet effective'}
    </p>{/if}
  <article>
    <h1>{data.document.title}</h1>
    <p class="meta">
      {es ? 'Versión' : 'Version'}: {data.version} ·
      <a href="mailto:info@highdemandmedia.com">info@highdemandmedia.com</a>
    </p>
    {#each data.document.sections as section, index (section.heading)}
      <section>
        <h2>{index + 1}. {section.heading}</h2>
        <p>{section.text}</p>
      </section>
    {/each}
    <p>
      <a href={`${privacy}#providers`} target="_blank" rel="external noopener noreferrer"
        >{es ? 'Privacidad y proveedores del CRM' : 'CRM privacy and providers'}</a
      >
    </p>
  </article>
</main>

<style>
  .agreement {
    width: min(100% - 2rem, 52rem);
    margin: 2rem auto;
    line-height: 1.65;
    color: var(--crm-text);
  }
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    margin-bottom: 1.5rem;
  }
  nav {
    display: flex;
    gap: 1rem;
  }
  a {
    text-decoration: underline;
    text-underline-offset: 0.2em;
  }
  a[aria-current] {
    font-weight: 700;
  }
  article {
    padding: clamp(1.25rem, 4vw, 3rem);
    background: var(--crm-surface);
    border: 1px solid var(--crm-border);
    border-radius: var(--crm-radius-lg);
    overflow-wrap: anywhere;
  }
  h1 {
    font-size: var(--crm-text-2xl);
    line-height: 1.25;
  }
  h2 {
    font-size: var(--crm-text-lg);
    margin: 1.75rem 0 0.5rem;
  }
  p {
    margin: 0.75rem 0;
  }
  .meta {
    color: var(--crm-text-muted);
    font-size: var(--crm-text-sm);
  }
  .draft {
    padding: 1rem;
    border: 1px solid var(--crm-border);
    border-radius: var(--crm-radius-md);
    background: var(--crm-surface-secondary);
  }
</style>
