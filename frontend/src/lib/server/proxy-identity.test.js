import { afterEach, beforeEach, expect, it, vi } from 'vitest';
vi.mock('$env/dynamic/private', () => ({ env: {} }));
import { env } from '$env/dynamic/private';
import { signedJson, clientIdentityHeaders } from './proxy-identity.js';

beforeEach(() => {
  env.CRM_PROXY_SIGNING_KEY = 'ab'.repeat(32); // Public test vector only.
  vi.spyOn(Date, 'now').mockReturnValue(1800000000000);
});
afterEach(() => {
  delete env.CRM_PROXY_SIGNING_KEY;
  vi.restoreAllMocks();
});

it('signs exact JSON bytes with a stable cross-language contract', () => {
  const result = signedJson(
    '/api/auth/password/login/',
    {
      email: 'demo@example.test',
      password: 'fictional'
    },
    () => '198.51.100.10'
  );
  expect(result.body).toBe('{"email":"demo@example.test","password":"fictional"}');
  expect(result.headers).toEqual({
    'Content-Type': 'application/json',
    'X-CRM-Client-IP': '198.51.100.10',
    'X-CRM-Client-Time': '1800000000',
    'X-CRM-Client-Signature': '4f01d76d8f1564a6d68bbe811512d71362cf404e102219670fc2ff006f4912a4'
  });
  expect(JSON.stringify(result)).not.toContain(env.CRM_PROXY_SIGNING_KEY);
});
it('binds visitor, body and route to the signature', () => {
  const sign = (path, body, ip) =>
    clientIdentityHeaders(path, body, () => ip)['X-CRM-Client-Signature'];
  expect(
    new Set([
      sign('/api/auth/password/login/', '{}', '198.51.100.10'),
      sign('/api/auth/password/login/', '{}', '198.51.100.11'),
      sign('/api/auth/password/register/', '{}', '198.51.100.10'),
      sign('/api/auth/password/login/', '{"x":1}', '198.51.100.10')
    ]).size
  ).toBe(4);
});
it.each(['', 'junk', '1.1.1.1,2.2.2.2', 'fe80::1%eth0'])('rejects invalid IP %s', (ip) => {
  expect(() => signedJson('/api/auth/password/login/', {}, () => ip)).toThrow();
});
it('does not silently downgrade when configured but the adapter cannot resolve an address', () => {
  expect(() => signedJson('/api/auth/password/login/', {}, undefined)).toThrow();
  env.CRM_PROXY_SIGNING_KEY = 'weak-key';
  expect(() => signedJson('/api/auth/password/login/', {}, () => '127.0.0.1')).toThrow();
});
it('preserves local unsigned development without a key', () => {
  delete env.CRM_PROXY_SIGNING_KEY;
  expect(signedJson('/api/auth/password/login/', {}, undefined)).toEqual({
    body: '{}',
    headers: { 'Content-Type': 'application/json' }
  });
});
