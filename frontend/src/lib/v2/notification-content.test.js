import { describe, expect, it } from 'vitest';
import { resolvedLink, reminderLabel, reminderDetail } from './notification-content.js';
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
});
