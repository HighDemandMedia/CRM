import { beforeEach, describe, expect, it, vi } from 'vitest';
import { apiRequest } from '$lib/api-helpers.js';
import { actions } from './+page.server.js';
import { savePasswordSession } from '$lib/server/password-session.js';
vi.mock('$lib/api-helpers.js', () => ({ apiRequest: vi.fn() }));
vi.mock('$lib/server/password-session.js', () => ({ savePasswordSession: vi.fn() }));
const event = (fields) => ({
  cookies: { get: () => undefined },
  request: {
    formData: async () => {
      const data = new FormData();
      for (const [key, value] of Object.entries(fields)) data.set(key, value);
      return data;
    }
  }
});
describe('organization details', () => {
  beforeEach(() => {
    vi.mocked(apiRequest).mockReset();
    vi.mocked(savePasswordSession).mockReset();
  });
  it('only submits organization property fields and keeps omitted settings unchanged', async () => {
    vi.mocked(apiRequest).mockResolvedValue({});
    const result = await actions.save(
      /** @type {any} */ (
        event({ name: ' New name ', api_key: 'not-allowed', csat_enabled: 'false' })
      )
    );
    expect(result).toEqual({ saved: true });
    expect(apiRequest).toHaveBeenCalledWith(
      '/org/settings/',
      { method: 'PATCH', body: { name: 'New name' } },
      expect.anything()
    );
  });
  it('reports backend permission refusal instead of claiming success', async () => {
    vi.mocked(apiRequest).mockRejectedValue({ status: 403 });
    const result = await actions.save(/** @type {any} */ (event({ name: 'New name' })));
    expect(/** @type {any} */ (result).status).toBe(403);
  });
  it('rejects malformed organization IDs before switching', async () => {
    const result = await actions.switchOrg(/** @type {any} */ (event({ org_id: 'invalid' })));
    expect(/** @type {any} */ (result).status).toBe(400);
    expect(apiRequest).not.toHaveBeenCalled();
  });
  it('returns through the authorized switch and replaces the entire account session', async () => {
    const id = 'b6eccd13-013a-498f-82f9-883776192c02';
    const input = event({ org_id: id });
    const result = { access_token: 'new-access', refresh_token: 'new-refresh' };
    vi.mocked(apiRequest).mockResolvedValue(result);
    await expect(actions.switchOrg(/** @type {any} */ (input))).rejects.toMatchObject({
      status: 303,
      location: '/'
    });
    expect(apiRequest).toHaveBeenCalledWith(
      '/auth/switch-org/',
      { method: 'POST', body: { org_id: id } },
      { cookies: input.cookies }
    );
    expect(savePasswordSession).toHaveBeenCalledWith(input.cookies, {
      ...result,
      current_org: { id }
    });
  });
  it('keeps the current session if return access has been revoked', async () => {
    vi.mocked(apiRequest).mockRejectedValue({ status: 403 });
    const result = await actions.switchOrg(
      /** @type {any} */ (event({ org_id: 'b6eccd13-013a-498f-82f9-883776192c02' }))
    );
    expect(result).toMatchObject({ status: 403, data: { scope: 'switch' } });
    expect(savePasswordSession).not.toHaveBeenCalled();
  });
});
