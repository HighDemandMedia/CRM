export function resolvedLink(link) {
  if (typeof link !== 'string') return '';
  const m = link.match(/^\/(?:cases|tickets)\/([^/?#]+)\/?$/);
  if (m) return `/tickets/${encodeURIComponent(m[1])}`;
  const record = link.match(/^\/(contacts|leads|tasks)\/([^/?#]+)\/?$/);
  if (record) return `/${record[1]}/${encodeURIComponent(record[2])}`;
  const calendar = link.match(/^\/calendar\?date=(\d{4}-\d{2}-\d{2})$/);
  if (calendar) return `/calendar?date=${calendar[1]}`;
  const help = link.match(/^\/(?:support|help)\/([^/?#]+)\/?$/);
  return help ? `/help/${encodeURIComponent(help[1])}` : '';
}

export function reminderLabel(row) {
  if (row.verb === 'task.reminder') return 'Task reminder';
  if (row.verb === 'calendar.reminder') return 'Upcoming event';
  return '';
}

export function reminderDetail(row, locale = 'en-US') {
  if (row.verb === 'task.reminder' && /^\d{4}-\d{2}-\d{2}$/.test(row.data?.due_date || '')) {
    return `${locale.startsWith('es') ? 'Vence' : 'Due'} ${new Intl.DateTimeFormat(locale, { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' }).format(new Date(row.data.due_date + 'T12:00:00Z'))}`;
  }
  if (row.verb === 'calendar.reminder' && Number.isFinite(Date.parse(row.data?.starts_at))) {
    return new Intl.DateTimeFormat(locale, {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    }).format(new Date(row.data.starts_at));
  }
  return '';
}
