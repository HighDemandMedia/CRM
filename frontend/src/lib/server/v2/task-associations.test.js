import { beforeEach, describe, expect, it, vi } from 'vitest';
const apiRequest = vi.fn();
vi.mock('$lib/api-helpers.js', () => ({ apiRequest: (...args) => apiRequest(...args) }));
const { getTaskFormOptions, createTask, updateTask } = await import('./tasks.js');
const { getTaskEditor, saveTaskEditor } = await import('./task-editor.js');
const { load, actions } = await import('../../../routes/(app)/tasks/new/+page.server.js');
const event = /** @type {any} */ ({ cookies: {}, params: { id: 'task-a' } });
const contact = {
  id: 'contact-a',
  first_name: 'Claudia',
  last_name: 'Test',
  email: 'claudia@example.test'
};

beforeEach(() => {
  apiRequest.mockReset();
  apiRequest.mockImplementation(async (url) =>
    url === '/tasks/?limit=1' ? { contacts_list: [contact], accounts_list: [], users: [] } : {}
  );
});

describe('task contact associations', () => {
  it('includes contact names and emails in both creation and edit pickers', async () => {
    const expected = { id: contact.id, name: 'Claudia Test', email: contact.email };
    expect((await getTaskFormOptions(event)).contacts).toEqual([expected]);
    const creation = await load(event);
    if (!creation) throw new Error('Expected task creation options');
    expect(creation.parents.contact).toEqual([expected]);
    const editor = await getTaskEditor(event, { contacts: [contact] });
    expect(editor.parents.contact).toEqual([expected]);
    expect(editor.form.contacts).toEqual([contact.id]);
  });
  it('keeps the selected contact preview if the options request fails', async () => {
    apiRequest.mockRejectedValue(new Error('Unavailable'));
    const editor = await getTaskEditor(event, { contacts: [contact] });
    expect(editor.parents.contact[0]).toMatchObject({ name: 'Claudia Test', email: contact.email });
    expect(editor.form.contacts).toEqual([contact.id]);
  });
  it('sends contacts alongside a company through the create adapter', async () => {
    await createTask(event, {
      title: 'Follow up',
      contacts: ['contact-a', 'contact-b'],
      account: 'company-a',
      org: 'untrusted'
    });
    expect(apiRequest).toHaveBeenLastCalledWith(
      '/tasks/',
      {
        method: 'POST',
        body: { title: 'Follow up', contacts: ['contact-a', 'contact-b'], account: 'company-a' }
      },
      { cookies: event.cookies }
    );
  });
  it('preserves contacts on unrelated updates and supports an explicit clear', async () => {
    await updateTask(event, 'task-a', { title: 'Changed' });
    expect(apiRequest.mock.lastCall[1].body).not.toHaveProperty('contacts');
    await updateTask(event, 'task-a', { contacts: [] });
    expect(apiRequest.mock.lastCall[1].body.contacts).toEqual([]);
  });
  it('submits and deduplicates selected contacts from the creation form', async () => {
    const form = new FormData();
    form.set('title', 'Follow up');
    form.append('contacts', 'contact-a');
    form.append('contacts', 'contact-a');
    await expect(
      actions.create({ ...event, request: { formData: async () => form } })
    ).rejects.toMatchObject({ status: 303, location: '/tasks' });
    expect(apiRequest.mock.lastCall[1].body.contacts).toEqual(['contact-a']);
  });
  it.each([{ ids: ['contact-a', 'contact-b'] }, { ids: [] }])(
    'saves selected contacts or removes them explicitly: $ids',
    async ({ ids }) => {
      const form = new FormData();
      form.set('title', 'Follow up');
      form.set('contacts_present', '1');
      for (const id of ids) form.append('contacts', id);
      await saveTaskEditor({ ...event, request: { formData: async () => form } });
      expect(apiRequest.mock.lastCall[1].body.contacts).toEqual(ids);
    }
  );
});
