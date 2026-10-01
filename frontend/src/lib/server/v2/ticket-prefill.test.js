import { it, expect, vi, beforeEach } from 'vitest';
const apiRequest = vi.fn();
vi.mock('$lib/api-helpers.js', () => ({ apiRequest: (...args) => apiRequest(...args) }));
const { getTicketFormOptions } = await import('./tickets.js');
beforeEach(() => {
  apiRequest.mockReset();
  apiRequest.mockImplementation(async (path) =>
    path.startsWith('/cases/')
      ? {
          accounts_list: [{ id: 'company-a', name: 'Company A' }],
          contacts_list: [{ id: 'contact-a', first_name: 'Contact', last_name: 'A' }]
        }
      : { opportunities: [] }
  );
});
it('preselects the visible contact or company from the originating profile', async () => {
  const contact = await getTicketFormOptions(
    { cookies: /** @type {any} */ ({}) },
    null,
    'contact-a'
  );
  expect(contact.defaults.contacts).toEqual(['contact-a']);
  expect(contact.defaults.account).toBe('');
  const company = await getTicketFormOptions({ cookies: /** @type {any} */ ({}) }, 'company-a');
  expect(company.defaults.account).toBe('company-a');
  expect(company.defaults.contacts).toEqual([]);
});
it('does not preselect IDs absent from the authorized choice lists', async () => {
  const result = await getTicketFormOptions(
    { cookies: /** @type {any} */ ({}) },
    'other-company',
    'other-contact'
  );
  expect(result.defaults.account).toBe('');
  expect(result.defaults.contacts).toEqual([]);
});
