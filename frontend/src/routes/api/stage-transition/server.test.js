import { describe, it, expect, vi, beforeEach } from 'vitest';
vi.mock('$lib/api-helpers.js', () => ({ apiRequest: vi.fn() }));
import { apiRequest } from '$lib/api-helpers.js';
vi.mock('$lib/server/v2/org-people.js', () => ({ getOrgPeopleAndTeams: vi.fn() }));
import { getOrgPeopleAndTeams } from '$lib/server/v2/org-people.js';
import { GET, POST } from './+server.js';
const id = '11111111-1111-4111-8111-111111111111';
/** @returns {any} */
const event = (body) => ({
  cookies: {},
  request: new Request('http://localhost/api/stage-transition', {
    method: 'POST',
    body: JSON.stringify(body)
  })
});
beforeEach(() => vi.clearAllMocks());
describe('stage completion', () => {
  it.each([
    ['Contact', 'contacts'],
    ['Account', 'accounts'],
    ['Opportunity', 'opportunities'],
    ['Task', 'tasks'],
    ['Case', 'cases']
  ])('uses the existing authorized update endpoint for %s', async (target, endpoint) => {
    vi.mocked(apiRequest).mockResolvedValue({});
    const values = {
      stage: 'QUALIFIED',
      email: 'test@example.com',
      custom_fields: { custom_score: 0 }
    };
    expect((await POST(event({ target, id, values }))).status).toBe(200);
    expect(apiRequest).toHaveBeenCalledWith(
      `/${endpoint}/${id}/`,
      { method: 'PATCH', body: values },
      { cookies: {} }
    );
  });
  it('keeps structured requirements when completion is rejected', async () => {
    const issue = {
      code: 'missing_properties',
      fields: [{ key: 'email', label: 'Email' }],
      message: 'Complete Email'
    };
    vi.mocked(apiRequest).mockRejectedValue({
      status: 400,
      body: { errors: { stage_requirements: issue } }
    });
    const response = await POST(event({ target: 'Contact', id, values: { stage: 'QUALIFIED' } }));
    expect(response.status).toBe(400);
    expect((await response.json()).stageRequirements).toEqual(issue);
  });
  it('rejects unsupported routes', async () => {
    expect((await POST(event({ target: 'Unknown', id, values: {} }))).status).toBe(400);
    expect(apiRequest).not.toHaveBeenCalled();
  });
});

describe('stage and property owner choices', () => {
  it.each([
    ['Contact', 'contacts'],
    ['Account', 'companies'],
    ['Opportunity', 'deals'],
    ['Task', 'tasks'],
    ['Case', 'tickets']
  ])('uses the assignment policy for %s', async (target, module) => {
    vi.mocked(getOrgPeopleAndTeams).mockResolvedValue({
      people: [{ id: 'self', name: 'Test member', email: 'member@example.test' }],
      teams: []
    });
    const cookies = {};
    const response = await GET(
      /** @type {any} */ ({
        cookies,
        url: new URL(
          `http://localhost/api/stage-transition?relation=Profile&target=${target}&q=member`
        )
      })
    );
    expect(await response.json()).toEqual({ options: [{ value: 'self', label: 'Test member' }] });
    expect(getOrgPeopleAndTeams).toHaveBeenCalledWith(cookies, { module, action: 'reassign' });
  });
  it('does not request unrestricted people for a missing object', async () => {
    const response = await GET(
      /** @type {any} */ ({
        cookies: {},
        url: new URL('http://localhost/api/stage-transition?relation=Profile')
      })
    );
    expect(await response.json()).toEqual({ options: [] });
    expect(getOrgPeopleAndTeams).not.toHaveBeenCalled();
  });
});
