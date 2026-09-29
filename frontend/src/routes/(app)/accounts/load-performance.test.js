import { expect, it, vi } from 'vitest';
vi.mock('$lib/server/v2/accounts.js', () => ({ listAccounts: vi.fn(), updateAccount: vi.fn() }));
import { listAccounts } from '$lib/server/v2/accounts.js';
import { load } from './+page.server.js';

it('starts the company request without waiting for shell settings', async () => {
  /** @type {(value: any) => void} */
  let finishParent = () => {};
  const parent = vi.fn(
    () =>
      new Promise((resolve) => {
        finishParent = resolve;
      })
  );
  vi.mocked(listAccounts).mockResolvedValue(
    /** @type {any} */ ({ results: [], totals: {}, contacts: [], industries: [], countries: [] })
  );
  const pending = load(
    /** @type {any} */ ({ cookies: {}, url: new URL('http://localhost/accounts'), parent })
  );
  expect(listAccounts).toHaveBeenCalledOnce();
  expect(parent).toHaveBeenCalledOnce();
  finishParent({ pipelineConfig: {} });
  const result = await pending;
  if (!result) throw new Error('Expected company data');
  expect(result.companies).toEqual([]);
});
