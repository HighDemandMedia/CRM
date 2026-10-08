import { emailEvents } from '$lib/v2/email-presentation.js';
import { attachmentHref } from './files.js';
import { userName } from '$lib/utils/user-name.js';

/** Meaningful record events only; personal emails remain a separate authorized projection.
 * @param {any} response
 * @param {any} record
 */
export function recordActivity(response, record) {
  const history = (response.history ?? []).filter(
    (entry) => !['VIEW', 'OPEN', 'DOWNLOAD'].includes(entry.action)
  );
  const events = history.map((entry) => {
    const changes = Object.entries(entry.changes ?? {}).map(([field, change]) => {
      const detail = /** @type {any} */ (change);
      const show = (value) => {
        if (value == null || value === '' || (Array.isArray(value) && !value.length)) return '—';
        if (Array.isArray(value)) return value.map((item) => item?.name || String(item)).join(', ');
        return typeof value === 'object' ? JSON.stringify(value) : String(value);
      };
      return `${detail.label || field}: ${show(detail.before_display ?? detail.before)} → ${show(detail.after_display ?? detail.after)}`;
    });
    const file =
      entry.resource?.type === 'Attachment' &&
      (response.attachments ?? []).find((file) => file.id === entry.resource.id);
    return {
      id: `history-${entry.id}`,
      type: file ? 'file' : entry.resource?.type === 'Note' ? 'note' : 'status',
      at: entry.created_at,
      by: entry.actor,
      href: file ? attachmentHref(file.id) : null,
      body: [entry.description || entry.action, ...changes].join('\n')
    };
  });
  // Existing records predate comprehensive auditing. Show facts still available,
  // without inventing past edits/deletions or duplicating their audited events.
  if (record?.created_at && !history.some((entry) => entry.action === 'CREATE'))
    events.push({
      id: 'record-created',
      type: 'status',
      at: record.created_at,
      by:
        record.created_by_name ||
        userName(record.created_by, '') ||
        record.created_by_email ||
        null,
      href: null,
      body: 'Record created'
    });
  for (const note of response.comments ?? []) {
    if (
      history.some(
        (entry) =>
          entry.resource?.type === 'Note' &&
          entry.resource.id === note.id &&
          entry.description === 'Note added'
      )
    )
      continue;
    events.push({
      id: `note-${note.id}`,
      type: 'note',
      at: note.commented_on,
      by: userName(note.commented_by) || null,
      href: null,
      body: `Note added: ${note.comment}`
    });
  }
  for (const file of response.attachments ?? []) {
    if (
      history.some(
        (entry) =>
          entry.resource?.type === 'Attachment' &&
          entry.resource.id === file.id &&
          entry.description === 'Attachment added'
      )
    )
      continue;
    events.push({
      id: `file-${file.id}`,
      type: 'file',
      at: file.created_at,
      by: null,
      href: attachmentHref(file.id),
      body: `Attachment added: ${file.file_name}`
    });
  }
  return [...events, ...emailEvents(response.email_activity)].sort(
    (a, b) => new Date(b.at).getTime() - new Date(a.at).getTime()
  );
}
