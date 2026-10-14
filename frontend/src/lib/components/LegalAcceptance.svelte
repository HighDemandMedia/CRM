<script>
  import { resolve } from '$app/paths';
  import { useI18n } from '$lib/i18n/context.js';
  import { legalLinks } from '$lib/legal.js';
  /** @type {{ requirements?: {version?: string, organization_authority_required?: boolean} }} */
  let { requirements = {} } = $props();
  const { ui, locale } = useI18n();
  const language = $derived(locale().startsWith('es') ? 'es' : 'en');
  const links = $derived(legalLinks(language));
</script>

{#if requirements.version}
  <div class="legal-acceptance">
    <input type="hidden" name="legal_version" value={requirements.version} />
    <input type="hidden" name="legal_locale" value={language} />
    <label>
      <input type="checkbox" name="accept_terms" required />
      <span
        >{ui('I accept the')}
        <a href={links.terms} target="_blank" rel="external noopener noreferrer"
          >{ui('CRM Terms of Service')}</a
        >.</span
      >
    </label>
    <p>
      {ui('Read how we handle your information in our')}
      <a href={links.privacy} target="_blank" rel="external noopener noreferrer"
        >{ui('Privacy notice')}</a
      >.
    </p>
    {#if requirements.organization_authority_required}
      <label>
        <input type="checkbox" name="organization_authority" required />
        <span
          >{ui('I am authorized to accept these terms and the')}
          <a href={resolve(`/legal/dpa?lang=${language}`)} target="_blank" rel="noopener noreferrer"
            >{ui('Data Processing Agreement')}</a
          >
          {ui('on behalf of my organization')}.</span
        >
      </label>
    {/if}
  </div>
{/if}

<style>
  .legal-acceptance {
    display: grid;
    gap: 0.75rem;
    margin-block: 0.5rem 1rem;
    font-size: var(--crm-text-sm);
    line-height: 1.6;
  }
  label {
    display: flex;
    align-items: flex-start;
    gap: 0.625rem;
    cursor: pointer;
  }
  input[type='checkbox'] {
    flex: 0 0 1.125rem;
    width: 1.125rem;
    height: 1.125rem;
    margin-top: 0.2rem;
  }
  a {
    text-decoration: underline;
    text-underline-offset: 0.2em;
  }
  p {
    margin: 0;
  }
</style>
