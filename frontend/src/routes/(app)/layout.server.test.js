import { beforeEach, describe, expect, it, vi } from 'vitest';
vi.mock('$lib/api-helpers.js', () => ({ apiRequest: vi.fn() }));
import { apiRequest } from '$lib/api-helpers.js';
import { load } from './+layout.server.js';

beforeEach(() => {
  vi.mocked(apiRequest).mockReset().mockResolvedValue({});
});

function event(canPreview) {
  return /** @type {any} */ ({
    locals: { org: { id: 'org', name: 'Example' }, profile: { can_preview: canPreview } },
    cookies: { get: vi.fn() }
  });
}

describe('initial CRM shell requests', () => {
  it.each([[true, 8], [false, 5]])('loads only rendered counters for preview=%s', async (preview, expected) => {
    await load(event(preview));
    const endpoints = vi.mocked(apiRequest).mock.calls.map(([path]) => path);
    expect(endpoints).toHaveLength(expected);
    expect(endpoints.some(path => path.startsWith('/opportunities/'))).toBe(false);
    expect(endpoints.some(path => path.startsWith('/tasks/'))).toBe(false);
    expect(endpoints.some(path => path.startsWith('/notifications/'))).toBe(false);
    expect(endpoints).toContain('/permissions/me/');
    expect(endpoints).toContain('/property-layout/');
    expect(endpoints).toContain('/pipeline-settings/?include_rules=false');
    if (!preview) {
      expect(endpoints.some(path => path.startsWith('/leads/'))).toBe(false);
      expect(endpoints.some(path => path.startsWith('/invoices/'))).toBe(false);
    }
  });
});
