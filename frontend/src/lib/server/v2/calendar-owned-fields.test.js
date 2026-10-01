import { beforeEach, expect, it, vi } from 'vitest';
vi.mock('$lib/api-helpers.js', () => ({ apiRequest: vi.fn() }));
import { apiRequest } from '$lib/api-helpers.js';
import { createContact, updateContact } from './contacts.js';
import { createAccount, updateAccount } from './accounts.js';
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(apiRequest).mockResolvedValue({});
});
it.each([
  ['contact', createContact, updateContact],
  ['company', createAccount, updateAccount]
])('%s forms never forward Calendar-owned dates', async (_, create, update) => {
  const event = {
    cookies: { get: vi.fn(), getAll: vi.fn(), set: vi.fn(), delete: vi.fn(), serialize: vi.fn() }
  };
  const values = { name: 'Calendar owner', city: 'Miami', appointment_at: '2026-10-01T10:00:00Z' };
  await create(event, values);
  expect(vi.mocked(apiRequest).mock.calls.at(-1)[1].body).not.toHaveProperty('appointment_at');
  await update(event, 'record-id', { ...values, appointment_at: null });
  expect(vi.mocked(apiRequest).mock.calls.at(-1)[1].body).not.toHaveProperty('appointment_at');
  expect(vi.mocked(apiRequest).mock.calls.at(-1)[1].body).toMatchObject({ city: 'Miami' });
});
