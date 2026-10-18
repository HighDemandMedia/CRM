import { afterEach, expect, it, vi } from 'vitest';
vi.mock('$env/dynamic/private', () => ({ env: {} }));
import { env } from '$env/dynamic/private';
import { logProxyProbe } from './proxy-diagnostics.js';
const id = 'crm-proxy-diagnostic-test';
function event(method = 'HEAD', probe = id) {
  return /** @type {any} */ ({
    url: new URL('https://crm.example.test/login'),
    request: new Request('https://crm.example.test/login', {
      method,
      headers: {
        'x-crm-proxy-probe': probe,
        'x-forwarded-for': 'spoofed, 198.51.100.10, 192.0.2.1',
        cookie: 'secret-cookie',
        authorization: 'secret-token'
      }
    }),
    getClientAddress: () => '10.0.0.1'
  });
}
afterEach(() => {
  delete env.CRM_PROXY_DIAGNOSTIC_ID;
  vi.restoreAllMocks();
});
it('is silent unless explicitly enabled with a matching HEAD probe', () => {
  const log = vi.spyOn(console, 'info').mockImplementation(() => {});
  logProxyProbe(event());
  env.CRM_PROXY_DIAGNOSTIC_ID = id;
  logProxyProbe(event('POST'));
  logProxyProbe(event('HEAD', 'wrong'));
  expect(log).not.toHaveBeenCalled();
});
it('logs bounded IP evidence without tokens, cookies, bodies or response changes', () => {
  env.CRM_PROXY_DIAGNOSTIC_ID = id;
  const log = vi.spyOn(console, 'info').mockImplementation(() => {});
  logProxyProbe(event());
  expect(JSON.parse(log.mock.calls[0][0])).toEqual({
    event: 'crm.proxy_probe',
    probe: id,
    host: 'crm.example.test',
    forwarded: ['invalid', '198.51.100.10', '192.0.2.1'],
    resolved: '10.0.0.1'
  });
  expect(log.mock.calls[0][0]).not.toContain('secret');
});
