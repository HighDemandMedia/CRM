import { beforeEach, expect, it, vi } from 'vitest';
vi.mock('$lib/api-helpers.js', () => ({ apiRequest: vi.fn() }));
import { apiRequest } from '$lib/api-helpers.js';
import { GET } from './+server.js';
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(apiRequest).mockResolvedValue({ connected: true });
});
function event(state, expected = 'valid-state') {
  return /** @type {any} */ ({
    url: new URL(`https://crm.example.com/profile/google/callback?state=${state}&code=code`),
    cookies: { get: () => expected, delete: vi.fn() }
  });
}
it('rejects missing or mismatched OAuth state before exchanging the code', async () => {
  await expect(GET(event('wrong'))).rejects.toMatchObject({
    status: 303,
    location: '/profile?google=cancelled'
  });
  expect(apiRequest).not.toHaveBeenCalled();
});
it('exchanges the code server-side and clears the state cookie', async () => {
  const input = event('valid-state');
  await expect(GET(input)).rejects.toMatchObject({
    status: 303,
    location: '/profile?google=connected'
  });
  expect(input.cookies.delete).toHaveBeenCalled();
  expect(apiRequest).toHaveBeenCalledWith(
    '/integrations/google/callback/',
    expect.objectContaining({ method: 'POST', body: { state: 'valid-state', code: 'code' } }),
    expect.anything()
  );
});
it('handles provider failure without exposing tokens or codes', async () => {
  vi.mocked(apiRequest).mockRejectedValue(new Error('secret response'));
  await expect(GET(event('valid-state'))).rejects.toMatchObject({
    status: 303,
    location: '/profile?google=failed'
  });
});
it('shows a permissions recovery message without exposing the callback payload', async () => {
  vi.mocked(apiRequest).mockRejectedValue({
    body: ['The required Google permissions were not granted. Connect again.']
  });
  await expect(GET(event('valid-state'))).rejects.toMatchObject({
    status: 303,
    location: '/profile?google=permissions'
  });
});
it('shows an expired authorization message', async () => {
  vi.mocked(apiRequest).mockRejectedValue({
    body: ['The Google authorization expired. Connect again.']
  });
  await expect(GET(event('valid-state'))).rejects.toMatchObject({
    status: 303,
    location: '/profile?google=expired'
  });
});
