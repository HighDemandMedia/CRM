import { describe, expect, it, vi } from 'vitest';
vi.mock('$lib/server/v2/tasks.js', () => ({
  createTask: vi.fn(),
  getTaskFormOptions: vi.fn(async () => ({
    owners: [],
    accounts: [{ id: 'company-1', name: 'Company' }],
    contacts: [{ id: 'contact-1', name: 'Contact' }]
  }))
}));
vi.mock('$lib/server/v2/creation-forms.js', () => ({
  createConfigured: vi.fn(),
  getCreationSchema: vi.fn(async () => null)
}));
import { load } from './+page.server.js';
import {
  initialCreationValues,
  creationPayload
} from '$lib/components/creation/creation-values.js';

function event(query) {
  return /** @type {Parameters<typeof load>[0]} */ (
    /** @type {unknown} */ ({ url: new URL(`https://crm.test/tasks/new${query}`) })
  );
}

describe('task creation from a record', () => {
  it('preselects accessible records and preserves them in configured form submission', async () => {
    const data = await load(event('?account=company-1&contact=contact-1'));
    expect(data.defaults).toEqual({ account: 'company-1', contacts: ['contact-1'] });
    const fields = [{ key: 'associations' }];
    const values = initialCreationValues('Task', fields, data);
    expect(creationPayload('Task', fields, values)).toMatchObject(data.defaults);
  });
  it.each(['?account=other-org&contact=hidden', ''])(
    'does not preselect unknown or absent records: %s',
    async (query) => {
      const data = await load(event(query));
      expect(data.defaults).toEqual({ account: '', contacts: [] });
    }
  );
});
