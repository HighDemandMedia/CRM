import { normalizeLocale } from '$lib/i18n/messages.js';

export function load({ cookies }) {
  return { uiLocale: normalizeLocale(cookies.get('crm_language')) };
}
