import { afterEach, expect, it, vi } from 'vitest';
vi.mock('$lib/server/api-origin.js', () => ({ apiOriginFor: () => 'https://api.example.test' }));
import { apiRequest } from './api-helpers.js';
const cookies = /** @type {any} */ ({ get: () => undefined });
afterEach(() => vi.unstubAllGlobals());
it('bounds requests and consumes JSON', async () => {
  const fetch = vi.fn().mockResolvedValue(new Response('{"ok":true}'));
  vi.stubGlobal('fetch', fetch);
  expect(await apiRequest('/contacts/', {}, cookies)).toEqual({ ok: true });
  expect(fetch.mock.calls[0][1].signal).toBeInstanceOf(AbortSignal);
});
it('reports an incomplete upstream response without a JSON crash', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('')));
  await expect(apiRequest('/contacts/', {}, cookies)).rejects.toMatchObject({ status: 502 });
});
it('keeps no-content and authorization responses distinct', async () => {
  vi.stubGlobal(
    'fetch',
    vi
      .fn()
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(new Response('{"detail":"Forbidden"}', { status: 403 }))
  );
  expect(await apiRequest('/contacts/', {}, cookies)).toBeNull();
  await expect(apiRequest('/contacts/', {}, cookies)).rejects.toMatchObject({ status: 403 });
});
it('does not retry writes after a timeout', async () => {
  const controller = new AbortController();
  controller.abort();
  const timeout = vi.spyOn(AbortSignal, 'timeout').mockReturnValue(controller.signal);
  const fetch = vi.fn().mockRejectedValue(new DOMException('Timeout', 'TimeoutError'));
  vi.stubGlobal('fetch', fetch);
  try {
    await expect(
      apiRequest('/contacts/', { method: 'POST', body: {} }, cookies)
    ).rejects.toMatchObject({ status: 504 });
    expect(fetch).toHaveBeenCalledTimes(1);
  } finally {
    timeout.mockRestore();
  }
});
it('rejects oversized multipart attachments before forwarding any data', async () => {
  const fetch = vi.fn();
  vi.stubGlobal('fetch', fetch);
  const body = new FormData();
  body.set('contact_attachment', new File([new Uint8Array(25 * 1024 * 1024 + 1)], 'too-large.bin'));
  await expect(
    apiRequest('/contacts/id/', { method: 'POST', body }, cookies)
  ).rejects.toMatchObject({ status: 400, message: 'Files must be 25 MB or smaller.' });
  expect(fetch).not.toHaveBeenCalled();
});
