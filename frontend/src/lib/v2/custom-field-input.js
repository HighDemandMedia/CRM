export function fieldInputType(type) {
  if (['number', 'integer', 'percentage'].includes(type)) return 'number';
  if (type === 'phone') return 'tel';
  if (['email', 'date', 'time'].includes(type)) return type;
  return 'text';
}
export function fieldInputStep(type) {
  return type === 'integer' ? '1' : type === 'money' ? '0.01' : type === 'time' ? '1' : 'any';
}

/** Format validation shared by creation, stage requirements and property editing. */
export function propertyValueError(type, raw, required = false) {
  const value = typeof raw === 'string' ? raw.trim() : raw;
  if (value == null || value === '' || (Array.isArray(value) && !value.length))
    return required ? 'This field is required.' : '';
  const text = String(value);
  if (type === 'phone' && !/^[0-9]{10}$/.test(text))
    return 'Enter exactly 10 digits, without a country code or separators.';
  if (type === 'email' && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/u.test(text))
    return 'Enter a valid email address.';
  if (type === 'url') {
    try {
      const url = new URL(/^[a-z][a-z0-9+.-]*:/i.test(text) ? text : `https://${text}`);
      if (
        !['http:', 'https:'].includes(url.protocol) ||
        /[\s\p{Cc}]/u.test(text) ||
        (!url.hostname.includes('.') &&
          !url.hostname.startsWith('[') &&
          url.hostname !== 'localhost')
      )
        return 'Enter a valid HTTP or HTTPS website URL.';
    } catch {
      return 'Enter a valid HTTP or HTTPS website URL.';
    }
  }
  if (['number', 'integer', 'percentage', 'money'].includes(type)) {
    const numeric = Number(text);
    if (!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i.test(text) || !Number.isFinite(numeric))
      return 'Enter a valid number.';
    if (type === 'integer' && !Number.isSafeInteger(numeric))
      return 'Enter a whole number within the safe integer range.';
    if (type === 'percentage' && (numeric < 0 || numeric > 100))
      return 'Enter a percentage between 0 and 100.';
    if (
      type === 'money' &&
      (!/^[+-]?\d+(?:\.\d{1,2})?$/.test(text) ||
        text.replace(/^[+-]?0*/, '').split('.')[0].length > 14)
    )
      return 'Enter an amount with up to 14 integer digits and 2 decimal places.';
  }
  if (type === 'date') {
    const date = new Date(`${text}T00:00:00Z`);
    if (
      !/^\d{4}-\d{2}-\d{2}$/.test(text) ||
      Number.isNaN(date.getTime()) ||
      date.toISOString().slice(0, 10) !== text ||
      text.startsWith('0000')
    )
      return 'Enter a valid date.';
  }
  if (type === 'time' && !/^(?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d(?:\.\d{1,6})?)?$/.test(text))
    return 'Enter a valid time.';
  if (type === 'text' || type === 'textarea') {
    if (/\p{Cc}/u.test(type === 'textarea' ? text.replace(/[\r\n\t]/g, '') : text))
      return 'Remove invalid control characters.';
  }
  return '';
}

/** @returns {Pick<import('svelte/elements').HTMLInputAttributes, 'inputmode' | 'pattern' | 'maxlength' | 'min' | 'max'>} */
export function propertyInputAttributes(type) {
  if (type === 'phone') return { inputmode: 'numeric', pattern: '[0-9]{10}' };
  if (type === 'integer') return { min: -Number.MAX_SAFE_INTEGER, max: Number.MAX_SAFE_INTEGER };
  if (type === 'percentage') return { min: 0, max: 100 };
  if (type === 'money') return { inputmode: 'decimal' };
  if (type === 'text') return { maxlength: 255 };
  if (type === 'textarea') return { maxlength: 10000 };
  return {};
}

/** Examples guide input without replacing labels or becoming saved defaults. */
export function propertyPlaceholder(field, target = '') {
  if (!field.custom) {
    if (['first_name', 'name', 'title'].includes(field.key))
      return (
        {
          Contact: 'e.g. Alex Morgan',
          Account: 'e.g. Acme Inc.',
          Opportunity: 'e.g. Website redesign',
          Task: 'e.g. Follow up on proposal',
          Case: 'e.g. Unable to sign in'
        }[target] || 'Enter a name'
      );
    const example = {
      address_line: 'e.g. 123 Main St, Suite 200',
      city: 'e.g. Miami',
      state: 'e.g. Florida',
      postcode: 'e.g. 33101',
      website: 'https://example.com',
      description: 'Add relevant details…',
      waiting_reason: 'What are you waiting for?',
      resolution_note: 'Describe the resolution…'
    }[field.key];
    if (example) return example;
  }
  return (
    {
      email: 'name@example.com',
      phone: '2125550123',
      url: 'https://example.com',
      number: 'e.g. 100',
      integer: 'e.g. 10',
      money: 'e.g. 1000.00',
      percentage: 'e.g. 25',
      text: 'Enter a value',
      textarea: 'Add relevant details…',
      list: '["Item 1", "Item 2"]'
    }[field.field_type] || ''
  );
}
