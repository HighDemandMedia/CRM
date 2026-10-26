import { expect, it, vi } from 'vitest';
vi.mock('$lib/server/v2/tasks.js', async (importOriginal) => ({
  ...(await importOriginal()),
  listTasks: vi.fn()
}));
import { listTasks } from '$lib/server/v2/tasks.js';
import { load } from './+page.server.js';

it('loads task records independently and reuses module options while filtering', async () => {
  vi.mocked(listTasks).mockResolvedValue(
    /** @type {any} */ ({ results: [], totals: { count: 0 }, owners: [] })
  );
  const parent = vi.fn(() => {
    throw new Error('Must not reload layout options');
  });
  const pending = load(
    /** @type {any} */ ({
      cookies: {},
      locals: { profile: { role: 'USER' } },
      url: new URL('http://localhost/tasks?priority=High'),
      parent
    })
  );
  expect(listTasks).toHaveBeenCalledOnce();
  expect(await pending).toMatchObject({ tasks: [], canDelete: false });
  expect(parent).not.toHaveBeenCalled();
});
