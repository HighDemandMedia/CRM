export function readTicketForm(form) {
  const fields = [
    'name',
    'description',
    'status',
    'priority',
    'category',
    'source',
    'due_at',
    'waiting_reason',
    'account',
    'deal',
    'assigned_to',
    'resolution_note'
  ];
  const values = Object.fromEntries(
    fields.filter((key) => form.has(key)).map((key) => [key, String(form.get(key) ?? '').trim()])
  );
  values.contacts = form.getAll('contacts').map(String);
  if (values.status === 'Closed') values.closed_on = new Date().toISOString().slice(0, 10);
  if (!values.name) return { values, error: 'Name is required.' };
  return { values, error: null };
}
