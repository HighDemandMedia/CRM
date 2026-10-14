import { beforeEach, expect, it, vi } from 'vitest';
vi.mock('$lib/api-helpers.js', () => ({ apiRequest: vi.fn() }));
vi.mock('$lib/server/invitation.js', () => ({ previewInvitation: vi.fn() }));
import { apiRequest } from '$lib/api-helpers.js';
import { previewInvitation } from '$lib/server/invitation.js';
import { load } from './+page.server.js';
const event = (values = {}, user = null) =>
  /** @type {any} */ ({
    cookies: { get: (key) => values[key] },
    locals: { user },
    url: new URL('https://crm.example.com/legal/dpa?lang=es'),
    setHeaders: vi.fn()
  });
beforeEach(() => vi.resetAllMocks());
it('does not disclose the document to anonymous visitors', async () => {
  await expect(load(event())).rejects.toMatchObject({ status: 403 });
  expect(apiRequest).not.toHaveBeenCalled();
});
it('lets a verified initial administrator read the DPA before accepting', async () => {
  vi.mocked(previewInvitation).mockResolvedValue({
    legal: { organization_authority_required: true }
  });
  const input = event({ crm_invitation: 'valid-invite' });
  const result = await load(input);
  if (!result) throw new Error('Expected agreement data');
  expect(result.document.title).toBe('Acuerdo de tratamiento de datos del CRM');
  expect(result.language).toBe('es');
  expect(input.setHeaders).toHaveBeenCalledWith(
    expect.objectContaining({ 'Cache-Control': 'private, no-store' })
  );
  expect(result).not.toHaveProperty('token');
});
it('denies ordinary team invitations', async () => {
  vi.mocked(previewInvitation).mockResolvedValue({
    legal: { organization_authority_required: false }
  });
  await expect(load(event({ crm_invitation: 'team-invite' }))).rejects.toMatchObject({
    status: 403
  });
});
it('denies expired or revoked invitations', async () => {
  vi.mocked(previewInvitation).mockRejectedValue({ response: { status: 400 } });
  await expect(load(event({ crm_invitation: 'expired' }))).rejects.toMatchObject({ status: 403 });
});
it.each([true, false])('uses live admin permission after sign-in (%s)', async (admin) => {
  vi.mocked(apiRequest).mockResolvedValue({ permissions: { is_admin: admin } });
  const result = load(event({}, { role: 'ADMIN' }));
  if (admin) {
    const data = await result;
    if (!data) throw new Error('Expected agreement data');
    expect(data.document.sections.length).toBeGreaterThan(0);
  } else await expect(result).rejects.toMatchObject({ status: 403 });
});
it('fails closed when permission verification is unavailable', async () => {
  vi.mocked(apiRequest).mockRejectedValue({ status: 503 });
  await expect(load(event({}, { role: 'ADMIN' }))).rejects.toMatchObject({ status: 503 });
});
