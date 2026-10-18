import { isIP } from 'node:net';
import { env } from '$env/dynamic/private';

/**
 * Short-lived, operator-enabled ingress check. Logs only bounded IP metadata
 * for a matching HEAD /login probe, never cookies, credentials or request bodies.
 * No diagnostic data is returned to the caller. Remove the env ID after use.
 * @param {import('@sveltejs/kit').RequestEvent} event
 */
export function logProxyProbe(event) {
  const id = env.CRM_PROXY_DIAGNOSTIC_ID;
  if (!id || !/^[a-zA-Z0-9-]{16,80}$/.test(id)) return;
  if (
    event.url.pathname !== '/login' ||
    event.request.method !== 'HEAD' ||
    event.request.headers.get('x-crm-proxy-probe') !== id
  )
    return;
  const forwarded = event.request.headers.get('x-forwarded-for') || '';
  const chain =
    forwarded.length <= 2048
      ? forwarded
          .split(',')
          .slice(-8)
          .map((value) => {
            const address = value.trim();
            return isIP(address) && !address.includes('%') ? address : 'invalid';
          })
      : ['oversized'];
  let resolved = 'unavailable';
  try {
    resolved = event.getClientAddress();
  } catch {
    /* Missing adapter setting is diagnostic evidence. */
  }
  console.info(
    JSON.stringify({
      event: 'crm.proxy_probe',
      probe: id,
      host: event.url.hostname,
      forwarded: chain,
      resolved: isIP(resolved) ? resolved : 'unavailable'
    })
  );
}
