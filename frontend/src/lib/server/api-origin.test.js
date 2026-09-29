import { afterEach, expect, it, vi } from 'vitest';
const environments = vi.hoisted(() => ({
  private: { DJANGO_INTERNAL_API_URL: '' },
  public: { PUBLIC_DJANGO_API_URL: 'https://api.example.com/' }
}));
vi.mock('$env/dynamic/private', () => ({ env: environments.private }));
vi.mock('$env/dynamic/public', () => ({ env: environments.public }));
afterEach(() => {
  environments.private.DJANGO_INTERNAL_API_URL = '';
  vi.unstubAllGlobals();
  vi.resetModules();
});
it('falls back to the public origin', async () => {
  const { API_ORIGIN } = await import('./api-origin.js');
  expect(API_ORIGIN).toBe('https://api.example.com');
});
it('sends authenticated server requests privately without changing the public URL', async () => {
  environments.private.DJANGO_INTERNAL_API_URL = ' http://crm-api:10000/ ';
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ results: [] })));
  vi.stubGlobal('fetch', fetch);
  const { apiRequest } = await import('$lib/api-helpers.js');
  await apiRequest(
    '/contacts/?board=true',
    {},
    { cookies: /** @type {any} */ ({ get: () => 'test-session-token' }) }
  );
  expect(fetch).toHaveBeenCalledWith(
    'http://crm-api:10000/api/contacts/?board=true',
    expect.objectContaining({
      headers: expect.objectContaining({ Authorization: 'Bearer test-session-token' })
    })
  );
  expect(environments.public.PUBLIC_DJANGO_API_URL).toBe('https://api.example.com/');
});

it('retains public origins for generated browser links', async () => {
  environments.private.DJANGO_INTERNAL_API_URL = 'http://crm-api:10000';
  const { apiOriginFor } = await import('./api-origin.js');
  expect(apiOriginFor('/webforms/123/')).toBe('https://api.example.com');
  expect(apiOriginFor('/org/settings/')).toBe('https://api.example.com');
  expect(apiOriginFor('/org/ui-context/')).toBe('http://crm-api:10000');
});
