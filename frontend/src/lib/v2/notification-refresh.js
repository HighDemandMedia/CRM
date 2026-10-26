// Coalesce navigation/focus events; opening the panel and read mutations remain fresh.
export function notificationRefreshDue({ loading, lastSuccess, force = false, now = Date.now() }) {
  return !loading && (force || lastSuccess === null || now - lastSuccess >= 15000);
}
