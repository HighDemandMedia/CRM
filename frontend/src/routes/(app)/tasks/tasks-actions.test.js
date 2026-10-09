import { describe, expect, it, vi } from 'vitest';
vi.mock('$lib/server/v2/tasks.js', () => ({
  listTasks: vi.fn(),
  setTaskDone: vi.fn(),
  updateTask: vi.fn()
}));
vi.mock('$lib/server/v2/org-people.js', () => ({
  getOrgPeopleAndTeams: vi.fn(),
  resolveMe: vi.fn()
}));
import { setTaskDone } from '$lib/server/v2/tasks.js';
import { actions } from './+page.server.js';

const event = () => {
  const form = new FormData();
  form.set('id', 'test-task');
  form.set('done', 'true');
  // This action reads only request and cookies; the API client is mocked above.
  return /** @type {Parameters<typeof actions.toggle>[0]} */ (
    /** @type {unknown} */ ({ request: { formData: async () => form }, cookies: {} })
  );
};

describe('task completion feedback', () => {
  it('returns readable validation feedback instead of an object', async () => {
    vi.mocked(setTaskDone).mockRejectedValueOnce(
      Object.assign(new Error('status: Required fields are missing.'), {
        status: 400,
        body: { errors: { status: ['Required fields are missing.'] } }
      })
    );
    const result = await actions.toggle(event());
    expect(result).toMatchObject({
      status: 400,
      data: { error: 'status: Required fields are missing.' }
    });
  });
  it('keeps access-denied feedback and does not report success', async () => {
    vi.mocked(setTaskDone).mockRejectedValueOnce({ status: 403 });
    const result = await actions.toggle(event());
    expect(result).toMatchObject({
      status: 403,
      data: { error: 'That task is not yours to change.' }
    });
  });
  it('keeps successful completion behavior', async () => {
    vi.mocked(setTaskDone).mockResolvedValueOnce({});
    expect(await actions.toggle(event())).toEqual({ done: true });
  });
});
