import { beforeEach, expect, it, vi } from 'vitest';
vi.mock('$lib/api-helpers.js', () => ({ apiRequest: vi.fn() }));
import { apiRequest } from '$lib/api-helpers.js';
import { load } from './+page.server.js';
import { load as loadOptions } from './+layout.server.js';

beforeEach(() => {
  vi.mocked(apiRequest).mockReset();
});

it('starts the ordinary ticket list while shell/options are still loading', async () => {
  const parent = vi.fn(() => {
    throw new Error('Must not reload layout options');
  });
  vi.mocked(apiRequest).mockResolvedValue({ results: [], count: 0 });
  const pending = load(
    /** @type {any} */ ({ cookies: {}, url: new URL('http://localhost/tickets'), parent })
  );
  expect(apiRequest).toHaveBeenCalledOnce();
  const result = await pending;
  expect(result).toMatchObject({ tickets: [] });
  expect(parent).not.toHaveBeenCalled();
  expect(apiRequest).toHaveBeenCalledOnce();
});

it('uses configured stages for the open-ticket preset', async () => {
  vi.mocked(apiRequest).mockResolvedValue({ results: [], count: 0 });
  await load(
    /** @type {any} */ ({
      cookies: {},
      url: new URL('http://localhost/tickets?all=0'),
      parent: async () => ({
        people: [],
        tags: [],
        pipelineConfig: {
          Case: {
            stages: [
              { key: 'CustomOpen', label: 'Custom open' },
              { key: 'Closed', label: 'Closed' }
            ]
          }
        }
      })
    })
  );
  expect(vi.mocked(apiRequest).mock.calls[0][0]).toContain('status=CustomOpen');
  expect(vi.mocked(apiRequest).mock.calls[0][0]).not.toContain('status=Closed');
});

it('requests compact tags and permission-scoped people once per module layout', async () => {
  vi.mocked(apiRequest).mockImplementation(async (url) =>
    url.startsWith('/tags') ? { tags: [{ id: 'tag' }] } : { profiles: [] }
  );
  const depends = vi.fn();
  const result = await loadOptions(
    /** @type {any} */ ({ cookies: { get: () => undefined }, locals: {}, depends })
  );
  expect(depends).toHaveBeenCalledWith('crm:ticket-options');
  expect(apiRequest).toHaveBeenCalledWith(
    '/users/get-teams-and-users/?module=tickets',
    {},
    expect.anything()
  );
  expect(vi.mocked(apiRequest).mock.calls.find(([url]) => url.startsWith('/tags'))[0]).toContain(
    'compact=true'
  );
  if (!result) throw new Error('Expected options');
  expect(result.tags).toEqual([{ id: 'tag' }]);
});
