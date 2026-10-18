import { createHash, createHmac } from 'node:crypto';
import { isIP } from 'node:net';
import { env } from '$env/dynamic/private';

/**
 * Sign the exact JSON bytes sent to Django, never browser-supplied IP headers.
 * getClientAddress is resolved by adapter-node's verified ingress configuration.
 * @param {string} path
 * @param {string} body
 * @param {(() => string) | undefined} getClientAddress
 * @returns {Record<string, string>}
 */
export function clientIdentityHeaders(path, body, getClientAddress) {
  const key = env.CRM_PROXY_SIGNING_KEY;
  if (!key) return {};
  if (!/^[0-9a-f]{64}$/i.test(key)) throw new Error('Invalid proxy identity configuration');
  const address = getClientAddress?.();
  if (!address || !isIP(address) || address.includes('%')) {
    throw new Error('Client address is unavailable');
  }
  const timestamp = String(Math.floor(Date.now() / 1000));
  const payload = [
    'crm-client-v1',
    timestamp,
    'POST',
    path,
    address,
    createHash('sha256').update(body).digest('hex')
  ].join('\n');
  return {
    'X-CRM-Client-IP': address,
    'X-CRM-Client-Time': timestamp,
    'X-CRM-Client-Signature': createHmac('sha256', Buffer.from(key, 'hex'))
      .update(payload)
      .digest('hex')
  };
}

/**
 * Keep Axios from reserializing signed bytes. No signing key means existing
 * local development behavior; hosted activation is explicit and coordinated.
 * @param {string} path
 * @param {Record<string, unknown>} data
 * @param {(() => string) | undefined} getClientAddress
 */
export function signedJson(path, data, getClientAddress) {
  const body = JSON.stringify(data);
  return {
    body,
    headers: {
      'Content-Type': 'application/json',
      ...clientIdentityHeaders(path, body, getClientAddress)
    }
  };
}
