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
