import { expect, it, vi } from 'vitest';

const apiRequest = vi.fn();
vi.mock('$lib/api-helpers.js', () => ({ apiRequest: (...args) => apiRequest(...args) }));
const { getContact } = await import('./contacts.js');
const event = /** @type {any} */ ({ cookies: {} });

it('keeps legacy attachment downloads after their first audited edit', async () => {
  apiRequest.mockResolvedValue({
    contact_obj: { id: 'contact', name: 'Demo' },
    attachments: [{ id: 'file', file_name: 'renamed.pdf', created_at: '2026-09-09T12:00:00Z' }],
    history: [
      {
        id: 'edit',
        description: 'Attachment updated',
        created_at: '2026-09-09T13:00:00Z',
        actor: 'owner@example.com',
        resource: { type: 'Attachment', id: 'file' }
      }
    ]
  });
  const data = await getContact(event, 'contact');
  expect(data.attachments.some((row) => row.id === 'file' && row.href)).toBe(true);
  expect(data.activity).toEqual([]);
});

it('shows an audited note once and keeps the original creator', async () => {
  apiRequest.mockResolvedValue({
    contact_obj: {
      id: 'contact',
      name: 'Demo',
      created_at: '2026-09-09T12:00:00Z',
      created_by_email: 'creator@example.com'
    },
    comments: [{ id: 'note', comment: 'Called', commented_on: '2026-09-09T13:00:00Z' }],
    history: [
      {
        id: 'note-event',
        description: 'Note added',
        created_at: '2026-09-09T13:00:00Z',
        actor: 'owner@example.com',
        resource: { type: 'Note', id: 'note' },
        changes: { Note: { before: null, after: 'Called' } }
      }
    ]
  });
  const data = await getContact(event, 'contact');
  expect(data.notes).toHaveLength(1);
  expect(data.activity).toEqual([]);
});
