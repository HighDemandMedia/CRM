import { describe, expect, it } from 'vitest';
import { notificationRefreshDue } from './notification-refresh.js';

describe('notification refresh scheduling', () => {
  it('loads on mount, coalesces navigation/focus, and refreshes after 15 seconds', () => {
    expect(notificationRefreshDue({ loading: false, lastSuccess: null, now: 0 })).toBe(true);
    for (const now of [0, 100, 1000, 14999])
      expect(notificationRefreshDue({ loading: false, lastSuccess: 0, now })).toBe(false);
    expect(notificationRefreshDue({ loading: false, lastSuccess: 0, now: 15000 })).toBe(true);
  });
  it('refreshes on panel opening/read mutations without duplicating in-flight work', () => {
    expect(notificationRefreshDue({ loading: false, lastSuccess: 10, now: 11, force: true })).toBe(
      true
    );
    expect(notificationRefreshDue({ loading: true, lastSuccess: null, force: true })).toBe(false);
  });
  it('does not cache failure or another account state', () => {
    expect(notificationRefreshDue({ loading: false, lastSuccess: null, now: 11 })).toBe(true);
  });
});
