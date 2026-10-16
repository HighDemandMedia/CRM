import { expect, it, vi } from 'vitest';
vi.mock('$lib/server/v2/contacts.js', () => ({ getContact: vi.fn(), EDITABLE_FIELDS: [] }));
import { getContact } from '$lib/server/v2/contacts.js';
import { load } from './+page.server.js';
it('opens the record without waiting for edit options and reuses route people', async () => {
  vi.mocked(getContact).mockResolvedValue(/** @type {any} */ ({ contact: { id: 'record' } }));
  const data = await load(
    /** @type {any} */ ({
      cookies: {},
      params: { id: 'record' },
      parent: async () => ({ people: [{ id: 'owner' }], meId: 'owner' })
    })
  );
  expect(getContact).toHaveBeenCalledExactlyOnceWith({ cookies: {} }, 'record');
  if (!data) throw new Error('Expected contact');
  expect(data.hosts).toEqual([{ id: 'owner' }]);
});
