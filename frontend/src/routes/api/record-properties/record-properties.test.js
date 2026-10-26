import { beforeEach, describe, expect, it, vi } from 'vitest';
vi.mock('$lib/api-helpers.js', () => ({ apiRequest: vi.fn() }));
import { apiRequest } from '$lib/api-helpers.js';
import { POST } from './+server.js';
const id = '8576db6d-cb6b-5c81-aca3-a3d896ac645e';
const api = vi.mocked(apiRequest);
const cookies = {
  get: vi.fn(),
  getAll: vi.fn(),
  set: vi.fn(),
  delete: vi.fn(),
  serialize: vi.fn()
};
const send = (values, target = 'Contact', system = true) =>
  POST(
    /** @type {any} */ ({
      cookies,
      request: new Request('http://localhost/api/record-properties', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, target, values, system })
      })
    })
  );
beforeEach(() => vi.clearAllMocks());
describe('single property PATCH boundary', () => {
  it('sends only the changed field through the existing contact adapter', async () => {
    expect((await send({ city: 'Miami' })).status).toBe(200);
    expect(apiRequest).toHaveBeenCalledExactlyOnceWith(
      `/contacts/${id}/`,
      { method: 'PATCH', body: { city: 'Miami' } },
      { cookies }
    );
  });
  it('preserves multiple assignees and the existing single-owner contract', async () => {
    await send({ assigned_to: ['a', 'b'] });
    expect(api.mock.calls[0][1].body).toEqual({ assigned_to: ['a', 'b'] });
    await send({ assigned_to: 'a' }, 'Account');
    expect(api.mock.calls[1][1].body).toEqual({ assigned_to: ['a'] });
  });
  it('reuses company tag and URL normalization without changing associations', async () => {
    await send({ tags: ['tag'], website: 'example.com' }, 'Account');
    expect(api.mock.calls[0][1].body).toEqual({
      tag_ids: ['tag'],
      website: 'https://example.com'
    });
  });
  it('rejects unknown and read-only system properties before reaching the API', async () => {
    for (const values of [
      { org: 'other' },
      { created_by: 'other' },
      { city: 'Miami', unexpected: true },
      {}
    ])
      expect((await send(values)).status).toBe(400);
    expect((await send({ city: 'Miami' }, 'Task')).status).toBe(400);
    expect(apiRequest).not.toHaveBeenCalled();
  });
  it('retains custom field namespace and API authorization failures', async () => {
    await send({ custom_score: 0 }, 'Contact', false);
    expect(api.mock.calls[0][1].body).toEqual({ custom_fields: { custom_score: 0 } });
    api.mockRejectedValueOnce(Object.assign(new Error('Not permitted.'), { status: 403 }));
    const response = await send({ city: 'Miami' });
    expect(response.status).toBe(403);
    expect(await response.json()).toMatchObject({ error: 'Not permitted.' });
  });
  it('returns stage requirements without treating the rejected stage as saved', async () => {
    const issue = {
      code: 'missing_properties',
      message: 'Complete required fields.',
      fields: [{ key: 'email' }]
    };
    api.mockRejectedValueOnce(
      Object.assign(new Error('Required'), {
        status: 400,
        body: { errors: { stage_requirements: issue } }
      })
    );
    const response = await send({ stage: 'QUALIFIED' });
    expect(response.status).toBe(400);
    expect(await response.json()).toMatchObject({ stageRequirements: issue });
  });
});
