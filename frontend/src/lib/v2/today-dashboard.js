const priorityRank = { Urgent: 0, High: 1, Medium: 2, Normal: 2, Low: 3 };
const paths = { tasks: '/tasks', tickets: '/tickets', deals: '/pipeline' };

/** Combine the bounded, permission-scoped previews without changing server totals. */
export function attentionPreview(day, filter = 'all', limit = 7) {
  const records = (rows, kind, reminder = false) =>
    (rows ?? []).map((row) => ({ ...row, kind, reminder, href: `${paths[kind]}/${row.id}` }));
  const tasks = records(day.tasks, 'tasks');
  const reminders = records(day.reminders, 'tasks', true);
  const deals = records(day.deals, 'deals');
  const tickets = records(day.tickets, 'tickets');
  const counts = day.counts;
  const sources = {
    all: {
      rows: [...tasks, ...tickets, ...deals, ...reminders],
      total: counts.tasks + counts.tickets + counts.deals + counts.reminders
    },
    tasks: { rows: [...tasks, ...reminders], total: counts.tasks + counts.reminders },
    tickets: { rows: tickets, total: counts.tickets },
    deals: { rows: deals, total: counts.deals },
    overdue: {
      rows: [...tasks, ...tickets, ...deals].filter((row) => row.overdue),
      total: counts.overdue
    },
    today: { rows: records(day.tasks_today, 'tasks'), total: counts.tasks_today },
    followups: { rows: [...deals, ...reminders], total: counts.deals + counts.reminders }
  };
  const source = sources[filter] ?? sources.all;
  return {
    total: source.total,
    rows: [...source.rows]
      .sort(
        (a, b) =>
          String(a.due).localeCompare(String(b.due)) ||
          (priorityRank[a.priority] ?? 2) - (priorityRank[b.priority] ?? 2) ||
          a.id.localeCompare(b.id)
      )
      .slice(0, limit)
  };
}

/** Prefer remaining appointments; keep completed meetings accessible on quiet afternoons. */
export function agendaPreview(events, now, limit = 7) {
  const ordered = [...events].sort((a, b) => Date.parse(a.start) - Date.parse(b.start));
  const remaining = ordered.filter((event) => Date.parse(event.end) > now);
  return {
    nextId: remaining[0]?.id ?? null,
    rows: remaining.length ? remaining.slice(0, limit) : ordered.slice(-limit)
  };
}
