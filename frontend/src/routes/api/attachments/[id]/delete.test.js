import { afterEach, describe, expect, it, vi } from 'vitest';
import { DELETE } from './+server.js';

/** @returns {any} Minimal request fixture; unused SvelteKit services are omitted. */
function event({ token = 'test-token', origin = 'http://localhost:5173' } = {}) {
  const url = new URL('http://localhost:5173/api/attachments/file-id');
  return {
    cookies: { get: () => token },
    params: { id: 'file-id' },
    url,
    request: new Request(url, { method: 'DELETE', headers: { origin } })
  };
}

afterEach(() => vi.restoreAllMocks());

describe('attachment deletion proxy', () => {
  it('rejects unauthenticated and cross-origin requests before reaching the API', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch');
    expect((await DELETE(event({ token: '' }))).status).toBe(401);
    expect((await DELETE(event({ origin: 'https://another-site.example' }))).status).toBe(403);
    expect(fetch).not.toHaveBeenCalled();
  });

  it('forwards deletion with the session token', async () => {
    const fetch = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(Response.json({ message: 'Attachment deleted.' }));
    const response = await DELETE(event());
    expect(response.status).toBe(200);
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/attachments/file-id/'),
      expect.objectContaining({
        method: 'DELETE',
        headers: expect.objectContaining({ Authorization: 'Bearer test-token' })
      })
    );
  });

  it.each([403, 404, 503])('preserves a backend %s without claiming success', async (status) => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      Response.json({ detail: 'Deletion refused.' }, { status })
    );
    const response = await DELETE(event());
    expect(response.status).toBe(status);
    expect(await response.json()).toEqual({ message: 'Deletion refused.' });
  });
});
