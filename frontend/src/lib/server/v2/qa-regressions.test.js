import { expect, it, vi, beforeEach } from 'vitest';
vi.mock('$lib/api-helpers.js', () => ({ apiRequest: vi.fn() }));
import { apiRequest } from '$lib/api-helpers.js';
import { getTaskFormOptions } from './tasks.js';
import { getDeal, listDeals } from './deals.js';
import { getContact } from './contacts.js';
import { money } from '$lib/v2/format.js';

const cookies = {
  get: vi.fn(),
  getAll: vi.fn(() => []),
  set: vi.fn(),
  delete: vi.fn(),
  serialize: vi.fn(() => '')
};

beforeEach(() => vi.clearAllMocks());

it.each([
  ['qa@example.com', '+12025550196'],
  ['qa@example.com', null],
  [null, '+12025550196'],
  [null, null]
])('preserves associated contact details: email=%s, phone=%s', async (email, phone) => {
  vi.mocked(apiRequest).mockResolvedValue({
    opportunity_obj: { id: 'DEA-0001' },
    contacts: [{ id: 'CON-0001', first_name: 'QA', email, phone }]
  });
  const result = await getDeal({ cookies }, 'DEA-0001');
  expect(result.contacts[0]).toMatchObject({
    id: 'CON-0001',
    email: email ?? '',
    phone: phone ?? ''
  });
});

it.each(['USD', 'EUR', null])('preserves an associated deal currency: %s', async (currency) => {
  vi.mocked(apiRequest).mockResolvedValue({
    contact_obj: { id: 'CON-0001' },
    opportunities: [{ id: 'DEA-0001', amount: '125.00', currency }]
  });
  const result = await getContact({ cookies }, 'CON-0001');
  expect(result.deals[0]).toMatchObject({ amount: 125, currency: currency ?? '' });
});

it('uses saved task assignee names and falls back to email only when blank', async () => {
  vi.mocked(apiRequest).mockResolvedValue({
    users: [
      { id: '1', user__name: 'QA Admin', user__email: 'admin@example.com' },
      { id: '2', user__name: '', user__email: 'member@example.com' }
    ]
  });
  const options = await getTaskFormOptions({ cookies });
  expect(options.owners.map((p) => p.name)).toEqual(['QA Admin', 'member@example.com']);
});

it('does not invent USD for historical deals with no saved currency', async () => {
  vi.mocked(apiRequest).mockResolvedValue({
    opportunities: [{ id: '1', amount: '12000', currency: null }]
  });
  const result = await listDeals({ cookies });
  expect(result.results[0].currency).toBe('');
  expect(money(result.results[0].amount, result.results[0].currency)).toBe(
    '12,000 (currency not set)'
  );
  expect(money(12000, '', 'es-US')).toBe('12,000 (moneda sin configurar)');
  expect(money(12000, 'EUR')).toContain('€');
});
