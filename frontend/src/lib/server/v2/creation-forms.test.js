import { beforeEach, describe, expect, it, vi } from 'vitest';
const apiRequest = vi.fn();
vi.mock('$lib/api-helpers.js', () => ({ apiRequest: (...args) => apiRequest(...args) }));
const { createConfigured } = await import('./creation-forms.js');
const { createContact } = await import('./contacts.js');
const { createAccount } = await import('./accounts.js');
const { createDeal } = await import('./deals.js');
const { createTask } = await import('./tasks.js');
const { createTicket } = await import('./tickets.js');
const event = /** @type {any} */ ({ cookies: {} });
beforeEach(() => apiRequest.mockReset());
function form(values) {
  const body = new FormData();
  body.set('_creation_values', JSON.stringify(values));
  return body;
}
describe('configured creation actions', () => {
  it.each([
    ['contacts', createContact],
    ['accounts', createAccount],
    ['opportunities', createDeal],
    ['tasks', createTask],
    ['cases', createTicket]
  ])('forwards custom properties through the %s allowlist', async (path, create) => {
    await create(event, { custom_fields: { ref: 'A' }, org: 'untrusted', created_by: 'untrusted' });
    expect(apiRequest).toHaveBeenLastCalledWith(
      `/${path}/`,
      { method: 'POST', body: { custom_fields: { ref: 'A' } } },
      event
    );
  });
  it('retains values and refreshes fields after an API rejection', async () => {
    const values = { name: 'Person', custom_fields: { ref: 'invalid' } };
    const schema = { selected: [{ key: 'email', required: true }], fields: [] };
    apiRequest.mockResolvedValue(schema);
    const create = vi.fn().mockRejectedValue({
      status: 400,
      body: { errors: { custom_fields: { ref: ['Invalid reference'] } } }
    });
    const result = await createConfigured(event, form(values), create, '/contacts');
    expect(result.data).toMatchObject({
      values,
      creationSchema: schema,
      fieldErrors: { 'custom_fields.ref': 'Invalid reference' }
    });
  });
  it('rejects malformed values before making an API write', async () => {
    const create = vi.fn();
    expect((await createConfigured(event, form([]), create, '/contacts')).status).toBe(400);
    expect(create).not.toHaveBeenCalled();
  });
  it('redirects to the created record', async () => {
    await expect(
      createConfigured(event, form({ name: 'Person' }), async () => ({ id: 'a' }), '/contacts')
    ).rejects.toMatchObject({ status: 303, location: '/contacts/a' });
  });
});
