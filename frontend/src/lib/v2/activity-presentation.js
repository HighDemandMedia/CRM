/** Format legacy audit values without changing the stored audit trail. */
export function activityText(value, formatDate, ui = (text) => text) {
  return String(value ?? '')
    .replace(/\bSalesAppointment object \(([^)]+)\)/g, (_, id) => `${ui('Appointment')} · ${id}`)
    .replace(/\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})\b/g, (value) =>
      Number.isFinite(Date.parse(value)) ? formatDate(value) : value
    );
}

export function activityParts(event) {
  const [summary = '', ...lines] = String(event.body ?? '').split('\n');
  return { summary, details: lines.join('\n').trim() };
}
