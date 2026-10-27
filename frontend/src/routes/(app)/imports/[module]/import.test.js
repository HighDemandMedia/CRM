import { beforeEach, describe, expect, it, vi } from 'vitest';
vi.mock('$lib/api-helpers.js', () => ({ apiRequest: vi.fn() }));
import { apiRequest } from '$lib/api-helpers.js';
import { GET, POST } from './+server.js';
const mockApi = vi.mocked(apiRequest);
const event = (module = 'contacts') =>
  /** @type {import('./$types').RequestEvent} */ (
    /** @type {unknown} */ ({ cookies: {}, params: { module } })
  );
function upload(file, action = 'preview') {
  const data = new FormData();
  data.set('file', file);
  data.set('action', action);
  return new Request('http://localhost/imports/contacts', { method: 'POST', body: data });
}
beforeEach(() => vi.resetAllMocks());
describe('CSV import proxy', () => {
  it('forwards schema reads without caching tenant data', async () => {
    mockApi.mockResolvedValue({ fields: [] });
    const response = await GET(event());
    expect(response.headers.get('cache-control')).toBe('private, no-store');
    expect(apiRequest).toHaveBeenCalledWith('/record-import/contacts/', {}, { cookies: {} });
  });
  it('rejects unsupported targets before contacting the API', async () => {
    expect((await GET(event('users'))).status).toBe(404);
    expect(apiRequest).not.toHaveBeenCalled();
  });
  it('forwards the file and preview token unchanged', async () => {
    mockApi.mockResolvedValue({ created: 1 });
    const body = new FormData();
    body.set('file', new File(['name\nTest\n'], 'test.csv'));
    body.set('action', 'commit');
    body.set('token', 'proof');
    const response = await POST({
      ...event(),
      request: new Request('http://localhost/imports/contacts', { method: 'POST', body })
    });
    expect(response.status).toBe(200);
    const forwarded = /** @type {FormData} */ (mockApi.mock.calls[0][1].body);
    expect(forwarded.get('token')).toBe('proof');
    expect(await /** @type {File} */ (forwarded.get('file')).text()).toBe('name\nTest\n');
  });
  it('rejects missing and oversized files', async () => {
    const empty = await POST({ ...event(), request: upload('not a file') });
    const large = await POST({
      ...event(),
      request: upload(new File(['a'.repeat(2 * 1024 * 1024 + 1)], 'large.csv'))
    });
    expect(empty.status).toBe(400);
    expect(large.status).toBe(400);
    expect(apiRequest).not.toHaveBeenCalled();
  });
  it('preserves permission failures and structured row errors', async () => {
    mockApi.mockRejectedValue({ status: 403, message: 'Permission denied' });
    expect((await GET(event())).status).toBe(403);
    const errors = [{ row: 2, field: 'email', message: 'Invalid email' }];
    mockApi.mockRejectedValue({ status: 400, message: 'Fix errors', body: { errors } });
    const result = await POST({ ...event(), request: upload(new File(['a'], 'test.csv')) });
    expect((await result.json()).errors).toEqual(errors);
  });
  it('does not expose internal API errors', async () => {
    mockApi.mockRejectedValue(new Error('internal database traceback'));
    expect(JSON.stringify(await (await GET(event())).json())).not.toContain('traceback');
  });
});
