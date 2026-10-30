import { toast } from 'svelte-sonner';
import { reminderDetail, resolvedLink } from './notification-content.js';

const titles = {
  'task.reminder': 'Task reminder',
  'calendar.reminder': 'Upcoming event',
  'case.mentioned': 'You were mentioned in a ticket',
  'case.commented': 'New ticket comment',
  'webform.submitted': 'New website submission'
};
const pending = new Map();
const receipts = new Map();
let currentProfile = '';
const MAX_AGE = 15 * 60 * 1000;

export function resetPendingAlerts() {
  pending.clear();
}
export function browserAlertsAllowed() {
  return (
    typeof window !== 'undefined' &&
    window.isSecureContext &&
    'Notification' in window &&
    Notification.permission === 'granted'
  );
}

/** Store only IDs, channel and timestamp; never persist notification content. */
function receiptStore(profile, now) {
  const key = `crm.notification-receipts.${profile}`;
  let stored = receipts.get(key) || {};
  try {
    stored = JSON.parse(localStorage.getItem(key) || '{}');
  } catch {
    /* In-memory fallback when storage is unavailable. */
  }
  if (!stored || typeof stored !== 'object' || Array.isArray(stored)) stored = {};
  stored = Object.fromEntries(
    Object.entries(stored)
      .filter(([, at]) => Number(at) > now - MAX_AGE)
      .slice(-500)
  );
  return {
    has: (id) => !!stored[id],
    add: (id) => {
      stored[id] = now;
      receipts.set(key, stored);
      try {
        localStorage.setItem(key, JSON.stringify(stored));
      } catch {
        /* Same-session deduplication remains available. */
      }
    }
  };
}

export async function announceNotifications(
  rows,
  profile,
  ui = (message) => message,
  locale = 'en-US',
  now = Date.now(),
  preferences = null
) {
  if (!profile) return;
  if (currentProfile !== profile) {
    pending.clear();
    currentProfile = profile;
  }
  for (const row of rows) pending.set(row.id, row);
  const deliver = () => {
    const store = receiptStore(profile, now);
    for (const [id, row] of pending) {
      if (
        !id ||
        row.read_at ||
        !(Date.parse(row.created_at) > now - MAX_AGE) ||
        (row.verb === 'calendar.reminder' && !(Date.parse(row.data?.starts_at) > now))
      ) {
        pending.delete(id);
        continue;
      }
      const title = ui(titles[row.verb] || 'New notification');
      const link = resolvedLink(row.link) || '/notifications';
      const visible = document.visibilityState === 'visible';
      // Recheck queued background alerts against the latest server preferences,
      // including changes saved from another tab or device.
      const popup = row.channels?.popup && preferences?.[row.verb]?.popup !== false;
      const browser = row.channels?.browser && preferences?.[row.verb]?.browser !== false;
      if (popup && visible && !store.has(`${id}:popup`)) {
        toast(title, {
          id: `notification-${id}`,
          description: [row.entity_name, reminderDetail(row, locale)].filter(Boolean).join(' · '),
          duration: 10000,
          action: { label: ui('Open'), onClick: () => window.location.assign(link) }
        });
        store.add(`${id}:popup`);
      }
      if (browser && browserAlertsAllowed() && !store.has(`${id}:browser`)) {
        try {
          // Desktop previews deliberately omit private record names and comments.
          const alert = new Notification('High Demand Media CRM', {
            body: title,
            tag: `crm-${profile}-${id}`
          });
          alert.onclick = () => {
            window.focus();
            window.location.assign(link);
            alert.close();
          };
          store.add(`${id}:browser`);
        } catch {
          // An OS/browser can refuse delivery even after granting permission.
          // Retain this item for a later poll instead of marking it delivered.
          continue;
        }
      }
      if (!popup || visible || store.has(`${id}:popup`)) pending.delete(id);
    }
  };
  // Coordinate receipts across tabs where available; notification tags also
  // replace duplicate desktop alerts in browsers without Web Locks.
  if (navigator.locks) await navigator.locks.request(`crm-notifications-${profile}`, deliver);
  else deliver();
}
