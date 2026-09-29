import { env as privateEnv } from '$env/dynamic/private';
import { env as publicEnv } from '$env/dynamic/public';

// Only server requests use the private address. Browser URLs and asset links
// continue to use PUBLIC_DJANGO_API_URL; never return this value in page data.
export const API_ORIGIN = (
  privateEnv.DJANGO_INTERNAL_API_URL?.trim() ||
  publicEnv.PUBLIC_DJANGO_API_URL ||
  ''
).replace(/\/+$/, '');

// These endpoints generate browser-facing absolute links from the request host
// (form embeds and organization logos). Keep their canonical public origin.
/** @param {string} endpoint */
export function apiOriginFor(endpoint) {
  if (endpoint.startsWith('/webforms/') || endpoint.startsWith('/org/settings/')) {
    return (publicEnv.PUBLIC_DJANGO_API_URL || API_ORIGIN).replace(/\/+$/, '');
  }
  return API_ORIGIN;
}
