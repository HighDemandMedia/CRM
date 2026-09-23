export const statuses = [
  ['New', 'New'],
  ['Assigned', 'In Progress'],
  ['Pending', 'Waiting'],
  ['Resolved', 'Resolved'],
  ['Closed', 'Closed']
];
export const priorities = [
  ['Low', 'Low'],
  ['Normal', 'Medium'],
  ['High', 'High'],
  ['Urgent', 'Urgent']
];
export const categories = ['Support', 'Billing', 'Service', 'General'];
export const sources = ['Email', 'Call', 'SMS', 'Website', 'Internal'];
export const statusLabel = (value) => statuses.find(([key]) => key === value)?.[1] ?? value;
export const priorityLabel = (value) => priorities.find(([key]) => key === value)?.[1] ?? value;
export function localDateInput(value) {
  if (!value) return '';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return '';
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}

// Date-only deadlines stay available through the selected local day.
export function dueDateEnd(value) {
  if (!value) return '';
  const date = new Date(`${value}T23:59:59.999`);
  return Number.isNaN(date.getTime()) ? '' : date.toISOString();
}
export const dueDateLabel = (value) =>
  value ? new Date(value).toLocaleDateString(undefined, { dateStyle: 'medium' }) : '—';
