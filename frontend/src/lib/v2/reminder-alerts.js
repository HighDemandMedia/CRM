import { toast } from 'svelte-sonner';
import { reminderLabel, reminderDetail, resolvedLink } from './notification-content.js';

// Desktop and mobile navigation mount separately. Share receipts so each
// reminder produces one toast per app session, even when both refresh.
const announced = new Set();
export function announceReminders(
  rows,
  now = Date.now(),
  ui = (message) => message,
  locale = 'en-US'
) {
  for (const row of rows) {
    if (!reminderLabel(row) || !row.id || row.read_at || announced.has(row.id)) continue;
    announced.add(row.id);
    if (row.verb === 'calendar.reminder' && !(Date.parse(row.data?.starts_at) > now)) continue;
    // Old task reminders remain in History without interrupting today's work.
    if (!(Date.parse(row.created_at) > now - 24 * 60 * 60 * 1000)) continue;
    const link = resolvedLink(row.link);
    toast(`${ui(reminderLabel(row))}: ${row.entity_name || ui('Reminder')}`, {
      id: row.id,
      description: reminderDetail(row, locale),
      duration: 10000,
      action: link ? { label: ui('Open'), onClick: () => window.location.assign(link) } : undefined
    });
  }
}
