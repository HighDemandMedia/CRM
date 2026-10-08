/** Canonical property names map to the existing create endpoint contracts. */
export function inputKey(target, key) {
  return target === 'Contact' && key === 'first_name' ? 'name' : key;
}
export function initialCreationValues(target, fields, data, previous = {}) {
  const defaults = {
    stage: target === 'Opportunity' ? 'PROSPECTING' : 'LEAD',
    status: 'New',
    priority: target === 'Case' ? 'Normal' : target === 'Task' ? 'Medium' : '',
    category: 'General',
    source: target === 'Case' ? 'Internal' : '',
    currency: data.org?.currency || 'USD',
    ...data.defaults
  };
  const result = {};
  for (const field of fields) {
    const key = inputKey(target, field.key);
    const prior = field.custom ? previous.custom_fields?.[field.key.slice(14)] : previous[key];
    result[field.key] = prior ?? defaults[key] ?? (field.multiple || key === 'pages' ? [] : '');
    if (key === 'pages' && typeof result[field.key] === 'string') {
      try {
        result[field.key] = JSON.parse(result[field.key] || '[]');
      } catch {
        result[field.key] = [];
      }
    }
    if (field.multiple && !Array.isArray(result[field.key]))
      result[field.key] = result[field.key] ? [result[field.key]] : [];
    if (field.field_type === 'datetime' && result[field.key]) {
      const date = new Date(result[field.key]);
      if (!Number.isNaN(date.getTime()))
        result[field.key] = new Date(date.getTime() - date.getTimezoneOffset() * 60000)
          .toISOString()
          .slice(0, 16);
    }
    if (field.field_type === 'list' && typeof result[field.key] !== 'string' && key !== 'pages')
      result[field.key] = JSON.stringify(result[field.key]);
  }
  return result;
}
export function creationPayload(target, fields, values) {
  const body = {};
  const custom = {};
  for (const field of fields) {
    let value = values[field.key];
    if (field.field_type === 'datetime' && value) value = new Date(value).toISOString();
    if (field.custom) {
      if (field.field_type === 'list' && typeof value === 'string' && value.trim())
        value = JSON.parse(value);
      custom[field.key.slice(14)] = value;
    } else {
      const key = inputKey(target, field.key);
      if (['due_date', 'due_at', 'closed_on'].includes(key) && !value) value = null;
      if (key === 'reminder_days') value = value === '' ? null : Number(value);
      if (key === 'pages') value = JSON.stringify(value || []);
      if (field.relation && !field.multiple && !value && key !== 'assigned_to') continue;
      body[key] = value;
    }
  }
  if (target === 'Case' && body.status === 'Closed')
    body.closed_on = new Date().toISOString().slice(0, 10);
  return { ...body, custom_fields: custom };
}

/** False and zero are answers; blank strings and empty selections are not. */
export function missingCreationFields(fields, values) {
  return fields.filter(
    (field) =>
      field.required &&
      (values[field.key] == null ||
        (typeof values[field.key] === 'string' && !values[field.key].trim()) ||
        (Array.isArray(values[field.key]) && !values[field.key].length))
  );
}
