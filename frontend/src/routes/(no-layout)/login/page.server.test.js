import { afterEach, describe, expect, it, vi } from 'vitest';
vi.mock('axios', () => ({ default: { post: vi.fn() } }));
vi.mock('$env/dynamic/private', () => ({ env: { NODE_ENV: 'production' } }));
import axios from 'axios';
import { actions } from './+page.server.js';

afterEach(() => vi.restoreAllMocks());

function input() {
  const form = new FormData();
  form.set('email', 'test@example.com');
  form.set('password', 'test-password-not-real');
  return {
    request: { formData: async () => form },
    cookies: { set: vi.fn(), delete: vi.fn(), get: vi.fn() }
  };
}

describe('password sign-in action', () => {
  it.each(['', {}, { access_token: 'token' }])(
    'rejects an incomplete session response without setting cookies',
    async (body) => {
      vi.spyOn(console, 'error').mockImplementation(() => {});
      vi.mocked(axios.post).mockResolvedValue({ data: body });
      const event = input();
      const result = await actions.password(event);
      expect(result.status).toBe(400);
      expect(result.data.error).toBe('Sign-in is unavailable. Please try again.');
      expect(event.cookies.set).not.toHaveBeenCalled();
    }
  );
  it('reports a timeout safely and preserves the email for retry', async () => {
    const log = vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.mocked(axios.post).mockRejectedValue({
      message: 'timeout',
      code: 'ECONNABORTED',
      config: { data: { password: 'test-password-not-real' } }
    });
    const result = await actions.password(input());
    expect(result.data.email).toBe('test@example.com');
    expect(JSON.stringify(log.mock.calls)).not.toContain('test-password-not-real');
  });
  it('stores a valid session and redirects to the CRM', async () => {
    vi.mocked(axios.post).mockResolvedValue({
      data: {
        access_token: 'access',
        refresh_token: 'refresh',
        current_org: { id: 'org' }
      }
    });
    const event = input();
    await expect(actions.password(event)).rejects.toMatchObject({ status: 303, location: '/' });
    expect(event.cookies.set).toHaveBeenCalledWith(
      'jwt_access',
      'access',
      expect.objectContaining({ httpOnly: true, secure: true })
    );
  });
});
