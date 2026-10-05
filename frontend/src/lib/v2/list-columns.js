import { orderedEntries, customDisplay } from './property-order.js';

// Keep the existing row adapters and sort contracts while using the organization's catalog.
const aliases = {
  Contact: {
    first_name: 'name',
    assigned_to: 'owner',
    source: 'source_label',
    stage: 'stage_label',
    preferred_communication_channel: 'preferred_communication_channel_label'
  },
  Account: {
    assigned_to: 'owner',
    source: 'source_label',
    stage: 'stage_label',
    country: 'country_display'
  },
  Opportunity: {
    assigned_to: 'owner',
    stage: 'stage_label',
    priority: 'priority_label',
    lead_source: 'lead_source_label',
    country: 'country_label'
  },
  Task: { assigned_to: 'assigned_names' },
  Case: { assigned_to: 'assignee', last_activity_at: 'last_activity' }
};

/** @param {string} target @param {any} config @param {string[][]} [legacy] */
export function listColumns(target, config, legacy = []) {
  const entries = orderedEntries(
    (config?.system || []).map((p) => [p.label, null, p.key]),
    target,
    config
  );
  const columns = entries.map((p) => ({
    key: aliases[target]?.[p.key] || p.key,
    label: p.label,
    definition: p.definition,
    system: !p.definition
  }));
  for (const [key, label] of legacy) {
    if (!columns.some((p) => p.key === key))
      columns.push({ key, label, definition: undefined, system: true });
  }
  return columns;
}

/** @param {any} row @param {string} key @param {any[]} columns */
export function columnValue(row, key, columns) {
  const definition = columns.find((c) => c.key === key)?.definition;
  if (definition) return customDisplay(row.custom_fields?.[definition.key], definition);
  const display = (value) => {
    if (value == null || value === '') return '—';
    if (Array.isArray(value))
      return (
        value
          .map(display)
          .filter((v) => v !== '—')
          .join(', ') || '—'
      );
    if (typeof value === 'boolean') return value ? 'Yes' : 'No';
    if (typeof value === 'object')
      return (
        value.name ||
        [value.first_name, value.last_name].filter(Boolean).join(' ') ||
        value.email ||
        '—'
      );
    return String(value);
  };
  return display(row[key]);
}

/** @param {unknown} saved @param {any[]} columns */
export function validColumns(saved, columns) {
  const keys = new Set(columns.map((c) => c.key));
  const valid = Array.isArray(saved) ? [...new Set(saved.filter((k) => keys.has(k)))] : [];
  return valid.length
    ? valid
    : columns.filter((c) => c.system && !['id', 'description'].includes(c.key)).map((c) => c.key);
}
