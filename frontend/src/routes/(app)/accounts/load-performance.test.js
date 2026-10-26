import { expect, it, vi } from 'vitest';
vi.mock('$lib/server/v2/accounts.js', () => ({ listAccounts: vi.fn(), updateAccount: vi.fn() }));
import { listAccounts } from '$lib/server/v2/accounts.js';
import { load } from './+page.server.js';

it('loads company records without repeating server layout reads', async () => {
  const parent = vi.fn(() => {
    throw new Error('Must reuse inherited layout data');
  });
  vi.mocked(listAccounts).mockResolvedValue(
    /** @type {any} */ ({
      results: [],
      totals: { count: 0 },
      contacts: [],
      industries: [],
      countries: []
    })
  );
  const result = await load(
    /** @type {any} */ ({
      cookies: {},
      depends: vi.fn(),
      url: new URL('http://localhost/accounts'),
      parent
    })
  );
  expect(listAccounts).toHaveBeenCalledOnce();
  expect(parent).not.toHaveBeenCalled();
  expect(result).toMatchObject({ companies: [] });
});
