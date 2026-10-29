import { beforeEach, expect, it, vi } from 'vitest';
vi.mock('$lib/server/api-origin.js', () => ({ API_ORIGIN: 'https://api.test' }));
vi.mock('$lib/server/proxy-identity.js', () => ({
  clientIdentityHeaders: vi.fn(() => ({ 'X-CRM-Client-Signature': 'test-signature' }))
}));
import { clientIdentityHeaders } from '$lib/server/proxy-identity.js';
import { load, actions } from './+page.server.js';
beforeEach(() => vi.clearAllMocks());

it('opening an email link only reads the invitation, without accepting it', async () => {
  const fetch = vi
    .fn()
    .mockResolvedValue(Response.json({ title: 'Demo', response: 'needsAction' }));
  const setHeaders = vi.fn();
  const result = await load(
    /** @type {any} */ ({
      url: new URL('https://crm.test/appointment-response?token=demo&response=accepted'),
      fetch,
      setHeaders
    })
  );
  expect(result.selected).toBe('accepted');
  expect(fetch).toHaveBeenCalledExactlyOnceWith(
    'https://api.test/api/appointment-response/?token=demo'
  );
  expect(setHeaders).toHaveBeenCalledWith({
    'Cache-Control': 'private, no-store',
    'Referrer-Policy': 'no-referrer'
  });
});

it('distinguishes expired invitations from temporary service failures', async () => {
  const context = {
    url: new URL('https://crm.test/appointment-response?token=demo'),
    fetch: vi.fn(),
    setHeaders: vi.fn()
  };
  context.fetch.mockResolvedValue(new Response('', { status: 410 }));
  expect(await load(/** @type {any} */ (context))).toMatchObject({
    unavailable: true,
    invitation: null
  });
  context.fetch.mockResolvedValue(new Response('', { status: 503 }));
  await expect(load(/** @type {any} */ (context))).rejects.toMatchObject({ status: 503 });
});

it('records the explicitly confirmed response using signed visitor context', async () => {
  const form = new FormData();
  form.set('token', 'demo');
  form.set('response', 'tentative');
  const fetch = vi.fn().mockResolvedValue(Response.json({ response: 'tentative' }));
  const getClientAddress = () => '198.51.100.10';
  const result = await actions.default(
    /** @type {any} */ ({
      request: new Request('https://crm.test/appointment-response', { method: 'POST', body: form }),
      fetch,
      getClientAddress
    })
  );
  expect(result).toEqual({ saved: true, response: 'tentative' });
  expect(clientIdentityHeaders).toHaveBeenCalledWith(
    '/api/appointment-response/',
    '{"token":"demo","response":"tentative"}',
    getClientAddress
  );
  expect(fetch.mock.calls[0][1]).toMatchObject({
    method: 'POST',
    headers: { 'X-CRM-Client-Signature': 'test-signature' }
  });
});
