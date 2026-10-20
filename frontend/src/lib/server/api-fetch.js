import { error as httpError } from '@sveltejs/kit';
import { setTimeout as delay } from 'node:timers/promises';

const TRANSIENT_CODES = new Set([
  'ECONNRESET',
  'ECONNREFUSED',
  'EPIPE',
  'EAI_AGAIN',
  'ETIMEDOUT',
  'UND_ERR_SOCKET',
  'UND_ERR_CONNECT_TIMEOUT'
]);

/** Retry a failed read once, sharing the original deadline and authentication. */
export async function apiFetch(/** @type {string} */ url, /** @type {RequestInit} */ options) {
  const method = (options.method || 'GET').toUpperCase();
  for (let attempt = 1; ; attempt++) {
    try {
      return await fetch(url, options);
    } catch (err) {
      if (options.signal?.aborted) throw err;
      const cause = /** @type {any} */ (err)?.cause?.code;
      const transient = TRANSIENT_CODES.has(cause);
      const transport = transient || (err instanceof TypeError && err.message === 'fetch failed');
      if (!transport) throw err;

      // Never log the URL, error object, headers or body: they may contain private data.
      console.warn('CRM API transport failure', {
        method,
        code: transient ? cause : 'FETCH_FAILED',
        attempt
      });
      if (method === 'GET' && transient && attempt === 1) {
        await delay(150, undefined, { signal: options.signal ?? undefined });
        continue;
      }
      // Writes may have succeeded before the connection failed; never replay them.
      httpError(
        503,
        method === 'GET'
          ? 'The service is temporarily unavailable. Please try again shortly.'
          : 'Connection interrupted. Check whether your change was saved before retrying.'
      );
    }
  }
}
