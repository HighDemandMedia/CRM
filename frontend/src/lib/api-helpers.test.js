import { afterEach, expect, it, vi } from 'vitest';
vi.mock('$lib/server/api-origin.js', () => ({ apiOriginFor: () => 'https://api.example.test' }));
vi.mock('$env/dynamic/private', () => ({ env: {} }));
import { env } from '$env/dynamic/private';
import { apiRequest } from './api-helpers.js';
const cookies = /** @type {any} */ ({ get: () => undefined });
afterEach(() => {
  delete env.CRM_PROXY_SIGNING_KEY;
  vi.unstubAllGlobals();
});
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

it('signs the exact password-change JSON without losing authentication', async () => {
  env.CRM_PROXY_SIGNING_KEY = 'ab'.repeat(32);
  const fetch = vi.fn().mockResolvedValue(new Response('{}'));
  vi.stubGlobal('fetch', fetch);
  await apiRequest(
    '/auth/password/change/',
    {
      method: 'POST',
      body: { password: 'fictional' },
      getClientAddress: () => '198.51.100.10'
    },
    /** @type {any} */ ({ get: () => 'test-access-token' })
  );
  expect(fetch).toHaveBeenCalledWith(
    'https://api.example.test/api/auth/password/change/',
    expect.objectContaining({
      body: '{"password":"fictional"}',
      headers: expect.objectContaining({
        Authorization: 'Bearer test-access-token',
        'X-CRM-Client-IP': '198.51.100.10',
        'X-CRM-Client-Signature': expect.stringMatching(/^[0-9a-f]{64}$/)
      })
    })
  );
});
