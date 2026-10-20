import agreement from '$lib/server/legal/terms.json';

export function load({ cookies, url, setHeaders }) {
  setHeaders({ 'Cache-Control': 'private, no-store', 'X-Robots-Tag': 'noindex, nofollow' });
  const language = (url.searchParams.get('lang') || cookies.get('crm_language') || 'en').startsWith(
    'es'
  )
    ? 'es'
    : 'en';
  return {
    language,
    version: agreement.version,
    draft: agreement.draft,
    document: agreement.documents[language]
  };
}
