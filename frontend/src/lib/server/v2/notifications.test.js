import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiRequest } from '$lib/api-helpers.js';
vi.mock('$lib/api-helpers.js', () => ({ apiRequest: vi.fn() }));

import { resolvedLink, getNotifications } from './notifications.js';

/**
 * `Notification.link` is a value read out of the database, and it becomes an
 * href. These cases are the reason it is parsed rather than followed.
 */
describe('resolvedLink', () => {
  const id = '4d60686d-bd3d-4e33-b114-ab36f194a6cd';

  it('normalises both CRM ticket spellings to the v2 route', () => {
    expect(resolvedLink(`/tickets/${id}`)).toBe(`/tickets/${id}`);
    expect(resolvedLink(`/cases/${id}`)).toBe(`/tickets/${id}`);
  });

  it('normalises product support to /help, including rows written as /support', () => {
    expect(resolvedLink(`/help/${id}`)).toBe(`/help/${id}`);
    expect(resolvedLink(`/support/${id}`)).toBe(`/help/${id}`);
  });

  it('tolerates a trailing slash on either shape', () => {
    expect(resolvedLink(`/tickets/${id}/`)).toBe(`/tickets/${id}`);
    expect(resolvedLink(`/support/${id}/`)).toBe(`/help/${id}`);
  });

  it.each([
    ['https://evil.example/help/1', 'an absolute URL'],
    ['//evil.example/help/1', 'a protocol-relative URL'],
    ['javascript:alert(1)', 'a javascript: URL'],
    ['/help/1/../../admin', 'a traversal attempt'],
    ['/help/', 'a help path with no id'],
    ['/settings', 'an unrelated internal path'],
    ['', 'an empty string'],
    [null, 'null'],
    [{ toString: () => '/help/1' }, 'a non-string that stringifies']
  ])('refuses %s (%s)', (link, _description) => {
    expect(resolvedLink(/** @type {any} */ (link))).toBe('');
  });

  it('escapes an id so it cannot break out of the path', () => {
    expect(resolvedLink('/help/a b')).toBe('/help/a%20b');
  });
});

describe('notification history pagination', () => {
  beforeEach(() => {
    vi.mocked(apiRequest).mockReset();
  });
  it('loads all statuses by default in batches of 20', async () => {
    vi.mocked(apiRequest).mockResolvedValue({ count: 45, unread_count: 4, results: [] });
    const data = await getNotifications({ cookies: /** @type {any} */ ({}) });
    expect(apiRequest).toHaveBeenCalledWith(
      '/notifications/?limit=20&offset=0',
      {},
      { cookies: {} }
    );
    expect(data.pagination).toEqual({ page: 1, size: 20, status: 'all', pages: 3 });
  });
  it('requests read history and page offset on the server', async () => {
    vi.mocked(apiRequest).mockResolvedValue({ count: 45, unread_count: 4, results: [] });
    await getNotifications({
      cookies: /** @type {any} */ ({}),
      url: new URL('http://localhost/notifications?status=read&page=2')
    });
    expect(apiRequest).toHaveBeenCalledWith(
      '/notifications/?limit=20&offset=20&read=true',
      {},
      { cookies: {} }
    );
  });
  it('normalizes invalid page and filter parameters', async () => {
    vi.mocked(apiRequest).mockResolvedValue({ count: 0, unread_count: 0, results: [] });
    const data = await getNotifications({
      cookies: /** @type {any} */ ({}),
      url: new URL('http://localhost/notifications?status=invalid&page=-1')
    });
    expect(data.pagination.page).toBe(1);
    expect(data.pagination.status).toBe('all');
  });
});

it('opens the Contact linked to a website submission', () => {
  expect(resolvedLink('/contacts/abc-123')).toBe('/contacts/abc-123');
  expect(resolvedLink('/contacts/abc/../../team')).toBe('');
});
