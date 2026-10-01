import { describe, expect, it, vi } from 'vitest';
import { resolvedLink, reminderLabel, reminderDetail } from './notification-content.js';
import { announceReminders } from './reminder-alerts.js';
import { toast } from 'svelte-sonner';
vi.mock('svelte-sonner', () => ({ toast: vi.fn() }));

describe('reminder notifications', () => {
  it('opens only safe task and calendar destinations', () => {
    expect(resolvedLink('/tasks/abc-123')).toBe('/tasks/abc-123');
    expect(resolvedLink('/calendar?date=2026-10-02')).toBe('/calendar?date=2026-10-02');
    for (const link of [
      '/tasks/a/../../team',
      '/calendar?date=2026-10-02&redirect=https://evil.test',
      '//evil.test/calendar',
      '/calendar?date=evil'
    ]) {
      expect(resolvedLink(link)).toBe('');
    }
  });
  it('shows readable dates and labels', () => {
    const row = { verb: 'task.reminder', data: { due_date: '2026-10-02' } };
    expect(reminderLabel(row)).toBe('Task reminder');
    expect(reminderDetail(row)).toBe('Due Oct 2, 2026');
    expect(reminderLabel({ verb: 'calendar.reminder' })).toBe('Upcoming event');
    expect(reminderDetail({ verb: 'calendar.reminder', data: { starts_at: 'invalid' } })).toBe('');
  });
  it('alerts once across desktop/mobile refreshes and ignores read or expired events', () => {
    vi.mocked(toast).mockClear();
    const now = Date.parse('2026-10-02T10:00:00Z');
    const row = {
      id: 'new-reminder',
      verb: 'calendar.reminder',
      entity_name: 'Demo',
      created_at: new Date(now).toISOString(),
      data: { starts_at: '2026-10-02T10:15:00Z' },
      link: '/calendar?date=2026-10-02'
    };
    announceReminders(
      [
        row,
        { ...row, id: 'read', read_at: '2026-10-02T10:00:00Z' },
        { ...row, id: 'past', data: { starts_at: '2026-10-02T09:00:00Z' } }
      ],
      now
    );
    announceReminders([row], now);
    expect(toast).toHaveBeenCalledTimes(1);
    expect(toast).toHaveBeenCalledWith(
      'Upcoming event: Demo',
      expect.objectContaining({ id: 'new-reminder' })
    );
  });
});
