import { describe, it, expect, vi, beforeEach } from 'vitest';
vi.mock('$lib/api-helpers.js', () => ({ apiRequest: vi.fn() }));
import { apiRequest } from '$lib/api-helpers.js';
import { actions } from './+page.server.js';
const id = 'e45c8eb6-f7e0-4d7d-a455-8093e7bfa3b3';
const cookies = { get: vi.fn() };
/** @param {string} stage @param {string} [contactId] @returns {Promise<any>} */
async function move(stage, contactId = id) {
  const body = new FormData();
  body.set('id', contactId);
  body.set('stage', stage);
  body.set('name', 'Must not overwrite');
  body.set('assigned_to', 'Must not overwrite');
  return actions.moveStage(
    /** @type {any} */ ({
      cookies,
      request: new Request('http://localhost/contacts?/moveStage', { method: 'POST', body })
    })
  );
}
beforeEach(() => vi.resetAllMocks());
describe('pipeline stage moves', () => {
  it('patches only the stage using the current session', async () => {
    vi.mocked(apiRequest).mockResolvedValue({});
    expect(await move('QUALIFIED')).toEqual({ moved: true });
    expect(apiRequest).toHaveBeenCalledWith(
      `/contacts/${id}/`,
      { method: 'PATCH', body: { stage: 'QUALIFIED' } },
      { cookies }
    );
  });
  it.each([''])('rejects invalid stage %s without writing', async (stage) => {
    expect((await move(stage)).status).toBe(400);
    expect(apiRequest).not.toHaveBeenCalled();
  });
  it('rejects a contact path instead of an id', async () => {
    expect((await move('LEAD', '../other')).status).toBe(400);
    expect(apiRequest).not.toHaveBeenCalled();
  });
  it('delegates validation of custom stage keys to the API', async () => {
    vi.mocked(apiRequest).mockRejectedValue(
      Object.assign(new Error('Unknown stage'), { status: 400 })
    );
    expect((await move('custom-stage')).status).toBe(400);
    expect(apiRequest).toHaveBeenCalled();
  });
  it('does not report success when the API denies the update', async () => {
    vi.mocked(apiRequest).mockRejectedValue(new Error('Permission denied'));
    const result = await move('LOST');
    expect(result.status).toBe(400);
    expect(result.data.error).toBeTruthy();
    expect(result.data.moved).toBeUndefined();
  });
});
