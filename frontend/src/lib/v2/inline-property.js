import { languages } from './languages.js';
import { configuredStages } from './pipeline-config.js';
import { can, canChooseOwner } from './permissions.js';

export const propertyModules = {
  Contact: 'contacts',
  Account: 'companies',
  Opportunity: 'deals',
  Task: 'tasks',
  Case: 'tickets'
};

/** Only real writable fields get an editor; display-only values remain text. */
export function editableProperty(row, target, schema, permissions, pipelines) {
  const module = propertyModules[target];
  if (!can(permissions, module, 'edit')) return null;
  if (row.definition)
    return { ...row.definition, key: row.key, custom: true, required: row.definition.is_required };
  if (!['Contact', 'Account'].includes(target)) return null;
  const field = schema?.fields?.find((field) => field.key === row.key && !field.custom);
  if (
    !field ||
    field.is_read_only ||
    ['id', 'created_at', 'created_by', 'appointment_at', 'last_activity_at'].includes(row.key)
  )
    return null;
  if (field.key === 'assigned_to' && !canChooseOwner(permissions, module)) return null;
  return {
    ...field,
    label: row.label,
    required: !!field.locked,
    // Preserve all current assignees; editing an unrelated field never replaces this list.
    multiple: field.key === 'assigned_to' || field.multiple,
    field_type: ['country', 'language'].includes(field.key) ? 'dropdown' : field.field_type,
    options:
      field.key === 'language'
        ? languages.map((value) => ({ value, label: value }))
        : field.key === 'stage'
          ? configuredStages(pipelines, target, field.options)
          : field.options
  };
}
export function propertyRawValue(record, field) {
  if (field.custom) return record.custom_fields?.[field.key.replace(/^custom_fields\./, '')];
  if (field.key === 'industry') return record.industry_value;
  if (field.key === 'tags') return (record.tags || []).map((tag) => String(tag.id ?? tag));
  return record[field.key];
}
export function propertyDraft(value, field) {
  if (field.field_type === 'checkbox') return value == null ? '' : String(value);
  if (field.multiple || field.field_type === 'multi_select') return [...(value || [])];
  if (field.key === 'pages') return (value || []).map((page) => ({ ...page }));
  if (field.field_type === 'list') return JSON.stringify(value || []);
  if (field.field_type === 'datetime' && value) {
    const date = new Date(value);
    return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
  }
  return value ?? '';
}
export function propertyValue(draft, field) {
  if (field.field_type === 'checkbox') return draft === '' ? null : draft === 'true';
  if (field.field_type === 'list' && typeof draft === 'string') return JSON.parse(draft || '[]');
  if (field.field_type === 'datetime' && draft) return new Date(draft).toISOString();
  return typeof draft === 'string' ? draft.trim() : draft;
}
export function samePropertyValue(a, b) {
  if (
    Array.isArray(a) &&
    Array.isArray(b) &&
    a.every((v) => typeof v === 'string') &&
    b.every((v) => typeof v === 'string')
  )
    return JSON.stringify([...a].sort()) === JSON.stringify([...b].sort());
  return JSON.stringify(a ?? '') === JSON.stringify(b ?? '');
}
