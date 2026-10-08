import { beforeEach, expect, it, vi } from 'vitest';
vi.mock('$lib/api-helpers.js', () => ({ apiRequest: vi.fn() }));
import { apiRequest } from '$lib/api-helpers.js';
import { GET, POST } from './+server.js';
const id = '11111111-1111-4111-8111-111111111111';
const event = (kind = 'contact', query = '', method = 'GET') => ({
  cookies: {},
  params: { kind, id },
  url: new URL(`http://localhost/api/record-mail/contact/${id}${query}`),
  request: new Request('http://localhost', { method })
});
beforeEach(() => vi.clearAllMocks());
it('forwards only supported filters with session cookies and private caching', async () => {
  vi.mocked(apiRequest).mockResolvedValue({ results: [] });
  const response = await GET(event('company', '?q=hello&profile=other&offset=20'));
  expect(apiRequest).toHaveBeenCalledWith(
    `/integrations/google/records/company/${id}/mail/?offset=20&q=hello`,
    { method: 'GET' },
    { cookies: {} }
  );
  expect(response.headers.get('cache-control')).toBe('private, no-store');
});
it('rejects unsupported record types before contacting the API', async () => {
  expect((await GET(event('unknown'))).status).toBe(400);
  expect(apiRequest).not.toHaveBeenCalled();
});
it.each([401, 403, 404, 429, 500])(
  'preserves access failures without exposing internal errors (%s)',
  async (status) => {
    vi.mocked(apiRequest).mockRejectedValue({ status, message: 'private error' });
    const response = await GET(event());
    expect(response.status).toBe(status === 500 ? 503 : status);
    expect(await response.text()).not.toContain('private error');
  }
);
it('queues sync through the authenticated backend', async () => {
  vi.mocked(apiRequest).mockResolvedValue({ queued: true });
  expect((await POST(event('contact', '', 'POST'))).status).toBe(200);
  expect(apiRequest).toHaveBeenCalledWith(expect.any(String), { method: 'POST' }, { cookies: {} });
});
