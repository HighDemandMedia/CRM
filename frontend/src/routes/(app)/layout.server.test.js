import { beforeEach, describe, expect, it, vi } from 'vitest';
vi.mock('$lib/api-helpers.js', () => ({ apiRequest: vi.fn() }));
import { apiRequest } from '$lib/api-helpers.js';
import { load } from './+layout.server.js';
const context = {
  terminology: { 'account.plural': 'Companies' },
  is_super_admin: true,
  permissions: { rules: { contacts: { view: 'own' } } },
  property_layout: { Contact: { order: ['first_name'] } },
  pipelines: { Contact: { stages: [] } }
};

beforeEach(() => {
  vi.mocked(apiRequest).mockReset();
});
function event(canPreview) {
  return /** @type {any} */ ({
    locals: { org: { id: 'org', name: 'Example' }, profile: { can_preview: canPreview } },
    cookies: { get: vi.fn(), set: vi.fn() }
  });
}

describe('CRM shell critical path', () => {
  it.each([
    [true, 1],
    [false, 1]
  ])('renders before optional counts finish for preview=%s', async (preview, count) => {
    /** @type {(value: any) => void} */
    let finishCounts = () => {};
    const pendingCounts = new Promise((resolve) => {
      finishCounts = resolve;
    });
    vi.mocked(apiRequest).mockImplementation((path) =>
      path === '/org/ui-context/' ? Promise.resolve(context) : pendingCounts
    );
    const shell = await load(event(preview));
    if (!shell) throw new Error('Expected shell data');
    expect(shell.permissions).toEqual(context.permissions);
    expect(shell.propertyLayout).toEqual(context.property_layout);
    expect(shell.pipelineConfig).toEqual(context.pipelines);
    expect(shell.isSuperAdmin).toBe(true);
    expect(shell.counts).toBeInstanceOf(Promise);
    expect(apiRequest).toHaveBeenCalledTimes(1 + count);
    finishCounts({});
    await shell.counts;
  });
  it('keeps failed counters from breaking the page', async () => {
    vi.mocked(apiRequest).mockImplementation((path) =>
      path === '/org/ui-context/' ? Promise.resolve(context) : Promise.reject(new Error('offline'))
    );
    const shell = await load(event(true));
    if (!shell) throw new Error('Expected shell data');
    expect(await shell.counts).toEqual({});
  });
  it('does not silently fabricate permissions when required configuration fails', async () => {
    vi.mocked(apiRequest).mockRejectedValue(new Error('unauthorized'));
    await expect(load(event(false))).rejects.toThrow('unauthorized');
    expect(apiRequest).toHaveBeenCalledTimes(1);
  });
});

describe('invitation setup navigation', () => {
  it.each([
    ['profile', '/contacts', '/profile'],
    ['profile_organization', '/settings/organization', '/profile'],
    ['organization', '/profile', '/settings/organization'],
    ['organization', '/pipeline', '/settings/organization']
  ])('resumes %s before opening %s', async (step, pathname, destination) => {
    vi.mocked(apiRequest).mockResolvedValue({
      ...context,
      permissions: { is_admin: step === 'organization' },
      setup_step: step
    });
    await expect(
      load({ ...event(false), url: new URL(`https://crm.example.com${pathname}`) })
    ).rejects.toMatchObject({ status: 303, location: destination });
    expect(apiRequest).toHaveBeenCalledTimes(1);
  });
  it.each([
    ['complete', '/contacts'],
    ['profile', '/profile'],
    ['profile_organization', '/profile'],
    ['organization', '/settings/organization']
  ])('allows %s at %s', async (step, pathname) => {
    vi.mocked(apiRequest).mockResolvedValue({
      ...context,
      permissions: { is_admin: step === 'organization' },
      setup_step: step
    });
    const result = await load({
      ...event(false),
      url: new URL(`https://crm.example.com${pathname}`)
    });
    expect(result).toHaveProperty('org');
    if (!result) throw new Error('Expected shell data');
    if (!result) throw new Error('Expected shell data');
    await result.counts;
  });
});

it.each([
  ['ADMIN', false, 'USER'],
  ['USER', true, 'ADMIN']
])(
  'uses fresh Settings access instead of the old %s token role',
  async (oldRole, admin, expected) => {
    vi.mocked(apiRequest).mockResolvedValue({
      ...context,
      permissions: { ...context.permissions, is_admin: admin }
    });
    const input = event(false);
    input.locals.profile.role = oldRole;
    const result = await load(input);
    if (!result) throw new Error('Expected shell data');
    expect(result.role).toBe(expected);
    if (!result) throw new Error('Expected shell data');
    await result.counts;
  }
);

describe('Settings direct navigation', () => {
  it.each([
    '/settings/organization',
    '/settings/organization/edit',
    '/settings/custom-fields',
    '/settings/pipelines',
    '/settings/tags',
    '/settings/web-forms/123',
    '/team',
    '/settings/roles'
  ])('denies ordinary members at %s', async (pathname) => {
    vi.mocked(apiRequest).mockResolvedValue(context);
    await expect(
      load({ ...event(false), url: new URL(`https://crm.example.com${pathname}`) })
    ).rejects.toMatchObject({ status: 403 });
  });
  it('allows a delegated section without opening other settings', async () => {
    vi.mocked(apiRequest).mockResolvedValue({
      ...context,
      permissions: { settings_access: { tags: 'read' } }
    });
    const result = await load({
      ...event(false),
      url: new URL('https://crm.example.com/settings/tags')
    });
    if (!result) throw new Error('Expected shell data');
    await result.counts;
    await expect(
      load({ ...event(false), url: new URL('https://crm.example.com/settings/organization') })
    ).rejects.toMatchObject({ status: 403 });
  });
});
