<script>
  import { resolve } from '$app/paths';
  import { ArrowUpRight, FileText } from '@lucide/svelte';
  import HelpHeader from '$lib/help/HelpHeader.svelte';
  import { useI18n } from '$lib/i18n/context.js';
  import { legalLinks } from '$lib/legal.js';

  const { ui, locale } = useI18n();
  let { data } = $props();
  const links = $derived(legalLinks(locale()));
</script>

<HelpHeader />
<div class="legal-scroll">
  <section aria-labelledby="legal-title">
    <h2 id="legal-title">{ui('Legal information')}</h2>
    <ul>
      <li>
        <a href={links.terms} target="_blank" rel="external noopener noreferrer"
          ><FileText size={20} /><span>{ui('Terms of service')}</span><ArrowUpRight size={18} /></a
        >
      </li>
      <li>
        <a href={links.privacy} target="_blank" rel="external noopener noreferrer"
          ><FileText size={20} /><span>{ui('Privacy policy')}</span><ArrowUpRight size={18} /></a
        >
      </li>
      {#if data.permissions?.is_admin === true}
        <li>
          <a
            href={resolve(`/legal/dpa?lang=${locale().startsWith('es') ? 'es' : 'en'}`)}
            target="_blank"
            rel="noopener noreferrer"
            ><FileText size={20} /><span>{ui('Data Processing Agreement')}</span><ArrowUpRight
              size={18}
            /></a
          >
        </li>
      {/if}
    </ul>
  </section>
</div>

<style>
  .legal-scroll {
    overflow: auto;
    min-height: 0;
    flex: 1;
  }
  section {
    max-width: 50rem;
    padding: var(--crm-space-6);
  }
  h2 {
    margin: 0 0 var(--crm-space-5);
    font-size: var(--crm-text-xl);
  }
  ul {
    list-style: none;
    padding: 0;
    margin: 0;
    border: 1px solid var(--v2-line);
    border-radius: var(--crm-radius-md);
    background: var(--crm-surface);
  }
  li + li {
    border-top: 1px solid var(--v2-line);
  }
  a {
    display: flex;
    align-items: center;
    gap: var(--crm-space-3);
    padding: var(--crm-space-4);
    color: var(--crm-text);
    text-decoration: none;
    border-radius: var(--crm-radius-md);
  }
  a:hover {
    background: var(--v2-hover);
  }
  a:focus-visible {
    outline: 2px solid var(--crm-focus);
    outline-offset: 2px;
  }
  span {
    flex: 1;
    min-width: 0;
    overflow-wrap: anywhere;
  }
  a :global(svg) {
    flex-shrink: 0;
  }
</style>
