import { it, expect, vi } from 'vitest';
vi.mock('$lib/api-helpers.js', () => ({ apiRequest: vi.fn() }));
import { apiRequest } from '$lib/api-helpers.js';
import { POST as contacts } from '../../../routes/(app)/contacts/export/+server.js';
import { POST as companies } from '../../../routes/(app)/accounts/export/+server.js';
import { POST as deals } from '../../../routes/(app)/pipeline/export/+server.js';
import { POST as tasks } from '../../../routes/(app)/tasks/export/+server.js';
import { POST as tickets } from '../../../routes/(app)/tickets/export/+server.js';
it.each([
  ['contacts', contacts],
  ['companies', companies],
  ['deals', deals],
  ['tasks', tasks],
  ['tickets', tickets]
])('checks %s export permission before reading records', async (module, handler) => {
  vi.mocked(apiRequest)
    .mockReset()
    .mockRejectedValue(Object.assign(new Error('Denied'), { status: 403 }));
  await expect(
    handler(
      /** @type {any} */ ({
        cookies: /** @type {any} */ ({}),
        url: new URL('http://localhost/export?scope=all'),
        request: new Request('http://localhost/export', { method: 'POST', body: new FormData() })
      })
    )
  ).rejects.toMatchObject({ status: 403 });
  expect(apiRequest).toHaveBeenCalledTimes(1);
  expect(vi.mocked(apiRequest).mock.calls[0][0]).toBe(`/roles/export/${module}/`);
});
