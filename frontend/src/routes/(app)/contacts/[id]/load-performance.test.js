import { expect, it, vi } from 'vitest';
vi.mock('$lib/server/v2/contacts.js', () => ({ getContact: vi.fn(), EDITABLE_FIELDS: [] }));
vi.mock('$lib/server/v2/creation-forms.js', () => ({
  getCreationSchema: vi.fn().mockResolvedValue({ fields: [] })
}));
import { getCreationSchema } from '$lib/server/v2/creation-forms.js';
import { getContact } from '$lib/server/v2/contacts.js';
import { load } from './+page.server.js';
it('opens the record without waiting for edit options and reuses route people', async () => {
  vi.mocked(getContact).mockResolvedValue(/** @type {any} */ ({ contact: { id: 'record' } }));
  const depends = vi.fn();
  const data = await load(
    /** @type {any} */ ({
      cookies: {},
      depends,
      params: { id: 'record' },
      parent: async () => ({ people: [{ id: 'owner' }], meId: 'owner' })
    })
  );
  expect(getContact).toHaveBeenCalledExactlyOnceWith({ cookies: {} }, 'record');
  if (!data) throw new Error('Expected contact');
  expect(depends).toHaveBeenCalledWith('crm:record:Contact:record');
  expect(getCreationSchema).toHaveBeenCalledExactlyOnceWith({ cookies: {} }, 'Contact');
  expect(data.propertySchema).toEqual({ fields: [] });
  expect(data.hosts).toEqual([{ id: 'owner' }]);
});
