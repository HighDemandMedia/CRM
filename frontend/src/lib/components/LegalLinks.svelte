<script>
  import { useI18n } from '$lib/i18n/context.js';
  import { legalLinks } from '$lib/legal.js';
  const { ui, locale } = useI18n();
  const links = $derived(legalLinks(locale()));
</script>

<nav class="legal-links" aria-label={ui('Legal information')}>
  <a href={links.privacy} target="_blank" rel="external noopener noreferrer">{ui('Privacy')}</a>
  <a href={links.terms} target="_blank" rel="external noopener noreferrer">{ui('Terms')}</a>
</nav>

<style>
  .legal-links {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 0.5rem 1rem;
    margin-block: 1.25rem;
    font-size: var(--crm-text-sm);
  }
  a {
    color: var(--crm-text-muted);
    text-decoration: underline;
    text-underline-offset: 0.2em;
    padding-block: 0.25rem;
  }
</style>
