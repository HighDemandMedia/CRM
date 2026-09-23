export const propertyKey = (property) => property.is_system ? property.key : `custom_fields.${property.key}`;
const aliases = {
  'contact owner': 'assigned_to', 'company owner': 'assigned_to', 'deal owner': 'assigned_to',
  'assigned to': 'assigned_to', owner: 'assigned_to', created: 'created_at',
  'created by': 'created_by', 'zip code': 'postcode', 'country': 'country',
  'close date': 'closed_on', 'preferred communication channel': 'preferred_communication_channel',
  address: 'address_line', 'last activity': 'last_activity_at', 'number of employees': 'number_of_employees'
};
export function entryKey(label, target, config) {
  const normalized = label.toLowerCase();
  if (normalized === 'name') return target === 'Contact' ? 'first_name' : target === 'Task' ? 'title' : 'name';
  if (normalized === 'source') return target === 'Opportunity' ? 'lead_source' : 'source';
  return aliases[normalized] || config?.system?.find(p => p.label.toLowerCase() === normalized)?.key || normalized.replaceAll(' ', '_');
}
export function orderedEntries(entries, target, config, values = {}) {
  const system = entries.map(([label, value, key]) => ({key: key || entryKey(label, target, config), label, value}));
  const custom = (config?.custom || []).map(definition => ({key: `custom_fields.${definition.key}`, label: definition.label, value: values[definition.key], definition}));
  const defaults = [...(config?.system || []).map(p=>p.key), ...custom.map(p=>p.key)];
  const keys = [...new Set([...(config?.order || []), ...defaults])];
  return [...system, ...custom].sort((a,b)=>(keys.includes(a.key)?keys.indexOf(a.key):keys.length)-(keys.includes(b.key)?keys.indexOf(b.key):keys.length));
}
export function customDisplay(value, field) {
  if (value === null || value === undefined || value === '' || (Array.isArray(value) && !value.length)) return '—';
  const label = v => field.options?.find(o => String(o.value) === String(v))?.label || v;
  if (field.field_type === 'checkbox') return value ? 'Yes' : 'No';
  if (field.field_type === 'dropdown') return label(value);
  if (Array.isArray(value)) return value.map(label).join(', ');
  if (field.field_type === 'datetime') return new Date(value).toLocaleString();
  return String(value);
}
