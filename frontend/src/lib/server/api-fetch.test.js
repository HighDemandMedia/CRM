import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { apiFetch } from './api-fetch.js';

const transportError = (code) => new TypeError('fetch failed', { cause: { code } });
beforeEach(() => vi.spyOn(console, 'warn').mockImplementation(() => {}));
afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

it.each(['ECONNRESET', 'UND_ERR_SOCKET', 'EAI_AGAIN'])(
  'recovers a read after %s without changing its auth or deadline',
  async (code) => {
    const response = new Response('{}');
    const fetch = vi.fn().mockRejectedValueOnce(transportError(code)).mockResolvedValue(response);
    vi.stubGlobal('fetch', fetch);
    const options = {
      headers: { Authorization: 'Bearer private' },
      signal: AbortSignal.timeout(30000)
    };
    expect(await apiFetch('https://api.example.test/api/profile/', options)).toBe(response);
    expect(fetch).toHaveBeenCalledTimes(2);
    expect(fetch.mock.calls[0][1]).toBe(options);
    expect(fetch.mock.calls[1][1]).toBe(options);
    expect(JSON.stringify(vi.mocked(console.warn).mock.calls)).not.toMatch(/private|https/);
  }
);

it('stops after one retry and returns a service-unavailable status', async () => {
  const fetch = vi.fn().mockRejectedValue(transportError('ECONNRESET'));
  vi.stubGlobal('fetch', fetch);
  await expect(apiFetch('https://api.example.test', {})).rejects.toMatchObject({ status: 503 });
  expect(fetch).toHaveBeenCalledTimes(2);
});

it.each(['POST', 'PATCH', 'DELETE'])('never repeats a %s operation', async (method) => {
  const fetch = vi.fn().mockRejectedValue(transportError('ECONNRESET'));
  vi.stubGlobal('fetch', fetch);
  await expect(apiFetch('https://api.example.test', { method })).rejects.toMatchObject({
    status: 503
  });
  expect(fetch).toHaveBeenCalledTimes(1);
});

it.each([401, 403, 429, 500])(
  'leaves HTTP %s handling to the API helper without retries',
  async (status) => {
    const response = new Response('{}', { status });
    const fetch = vi.fn().mockResolvedValue(response);
    vi.stubGlobal('fetch', fetch);
    expect(await apiFetch('https://api.example.test', {})).toBe(response);
    expect(fetch).toHaveBeenCalledTimes(1);
  }
);

it('does not retry certificate errors or disclose their details', async () => {
  const fetch = vi.fn().mockRejectedValue(transportError('CERT_HAS_EXPIRED'));
  vi.stubGlobal('fetch', fetch);
  await expect(apiFetch('https://api.example.test', {})).rejects.toMatchObject({ status: 503 });
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(console.warn).toHaveBeenCalledWith('CRM API transport failure', {
    method: 'GET',
    code: 'FETCH_FAILED',
    attempt: 1
  });
});

it('preserves programming errors', async () => {
  const failure = new TypeError('Invalid URL');
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(failure));
  await expect(apiFetch('invalid', {})).rejects.toBe(failure);
  expect(console.warn).not.toHaveBeenCalled();
});

it('honors an expired deadline without retrying', async () => {
  const controller = new AbortController();
  controller.abort();
  const failure = transportError('ECONNRESET');
  const fetch = vi.fn().mockRejectedValue(failure);
  vi.stubGlobal('fetch', fetch);
  await expect(apiFetch('https://api.example.test', { signal: controller.signal })).rejects.toBe(
    failure
  );
  expect(fetch).toHaveBeenCalledTimes(1);
});
