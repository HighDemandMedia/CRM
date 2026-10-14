const LEGAL_ORIGIN = 'https://highdemandmedia.com';

export function legalLinks(locale = 'en') {
  const suffix = locale.startsWith('es') ? '-es' : '';
  return {
    terms: `${LEGAL_ORIGIN}/crm-terms${suffix}.html`,
    privacy: `${LEGAL_ORIGIN}/crm-privacy${suffix}.html`,
    dpa: `/legal/dpa?lang=${suffix ? 'es' : 'en'}`
  };
}

export function legalFormValues(form) {
  return {
    legal_version: String(form.get('legal_version') || ''),
    legal_locale: String(form.get('legal_locale') || ''),
    accept_terms: form.get('accept_terms') === 'on',
    organization_authority: form.get('organization_authority') === 'on'
  };
}
