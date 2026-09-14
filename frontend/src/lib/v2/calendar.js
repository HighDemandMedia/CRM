export function dateKey(date) {
  const pad = (n) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}
export function calendarDays(selected, view) {
  const start = new Date(selected.getFullYear(), selected.getMonth(), selected.getDate());
  if (view === 'month') start.setDate(1);
  if (view !== 'day') start.setDate(start.getDate() - start.getDay());
  const count = view === 'month' ? 42 : view === 'week' ? 7 : 1;
  return Array.from(
    { length: count },
    (_, i) => new Date(start.getFullYear(), start.getMonth(), start.getDate() + i)
  );
}
export function shiftDate(selected, view, direction) {
  if (view === 'month') return new Date(selected.getFullYear(), selected.getMonth() + direction, 1);
  return new Date(
    selected.getFullYear(),
    selected.getMonth(),
    selected.getDate() + direction * (view === 'week' ? 7 : 1)
  );
}

// Legacy record appointments have no end; reserve one hour for those cards.
export function timedCards(events) {
  const sorted = events
    .map((event) => {
      const date = new Date(event.start);
      const duration = event.end
        ? Math.max(15, (Date.parse(event.end) - date.getTime()) / 60000)
        : 60;
      return { event, duration, minute: date.getHours() * 60 + date.getMinutes() };
    })
    .sort((a, b) => a.minute - b.minute);
  const result = [];
  let group = [],
    ends = [],
    until = -1;
  function flush() {
    for (const item of group) result.push({ ...item, lanes: ends.length });
    group = [];
    ends = [];
    until = -1;
  }
  for (const item of sorted) {
    if (item.minute >= until) flush();
    let lane = ends.findIndex((end) => end <= item.minute);
    if (lane === -1) lane = ends.length;
    ends[lane] = item.minute + item.duration;
    until = Math.max(until, item.minute + item.duration);
    group.push({ ...item, lane });
  }
  flush();
  return result;
}
