import { expect, it } from 'vitest';
import { contactChanges } from './contact-autosave.js';
it('sends only changed fields and preserves untouched relationships', () => {
  const before = { name: 'Ana', city: 'Miami', assigned_to: 'owner', tags: ['b', 'a'] };
  expect(contactChanges(before, { ...before, city: 'Boston', tags: ['a', 'b'] })).toEqual({
    city: 'Boston'
  });
});
it('supports clearing values and removing all tags', () => {
  expect(contactChanges({ email: 'a@example.com', tags: ['a'] }, { email: '', tags: [] })).toEqual({
    email: '',
    tags: []
  });
  expect(contactChanges({ appointment_at: null }, { appointment_at: '' })).toEqual({});
});
