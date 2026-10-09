/** Only product-safe Google errors may reach the UI; never display provider payloads. */
const messages = new Set([
  'Google connections need configuration by the CRM administrator.',
  'Reconnect Google to restore access.',
  'Google access was denied. Check permissions and reconnect.',
  'The required Google permissions were not granted. Connect again.',
  'Google did not grant offline access. Connect again.',
  'Could not verify the Google account. Connect again.',
  'Use a verified Google email address.',
  'The Google authorization expired. Connect again.',
  'The Google authorization is incomplete. Connect again.',
  'Connection changed. Connect again.',
  'Connect Google first.',
  'Connect Google Calendar first.',
  'Disconnect Calendar before switching a calendar with linked CRM appointments.',
  'Sync could not be queued. It will retry automatically.',
  'Google is unavailable. Try syncing again later.',
  'Too many calendars to list.',
  'Your session may have expired. Sign in again to continue.',
  'Ask your organization administrator to review your permissions.',
  'Please wait a moment before trying again.'
]);

/** @param {any} error @param {string} fallback */
export function googleErrorMessage(
  error,
  fallback = 'Google is unavailable. Try syncing again later.'
) {
  const body = error?.body;
  const candidates = [
    body?.errors,
    body?.detail,
    body?.non_field_errors,
    body,
    error?.message,
    error
  ];
  for (const value of candidates) {
    const message = Array.isArray(value) ? value[0] : value;
    if (typeof message === 'string' && messages.has(message)) return message;
  }
  if (error?.status === 401) return 'Your session may have expired. Sign in again to continue.';
  if (error?.status === 403)
    return 'Ask your organization administrator to review your permissions.';
  if (error?.status === 404) return 'Connect Google first.';
  if (error?.status === 429) return 'Please wait a moment before trying again.';
  return fallback;
}

export function googleCallbackMessage(result) {
  const message = {
    cancelled: 'Connection cancelled or expired. Try connecting again.',
    permissions: 'The required Google permissions were not granted. Connect again.',
    expired: 'The Google authorization expired. Connect again.',
    failed: 'Could not connect Google. Try again or ask your CRM administrator for help.'
  }[result];
  return typeof message === 'string' ? message : '';
}
