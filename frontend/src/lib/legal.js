const LEGAL_ORIGIN = 'https://highdemandmedia.com';

export function legalLinks(locale = 'en') {
  const suffix = locale.startsWith('es') ? '-es' : '';
  return {
    terms: `/legal/terms?lang=${suffix ? 'es' : 'en'}`,
    privacy: `${LEGAL_ORIGIN}/crm-privacy${suffix}.html`,
    dpa: `/legal/dpa?lang=${suffix ? 'es' : 'en'}`
  };
}

export function legalFormValues(form) {
  return {
    legal_version: String(form.get('legal_version') || ''),
    legal_locale: String(form.get('legal_locale') || ''),
    accept_terms: form.get('accept_terms') === 'on',
    organization_authority:
      form.get('accept_terms') === 'on' && form.get('organization_authority') === 'on'
  };
}
