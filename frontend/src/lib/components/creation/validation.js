import { normalizedPhone, PHONE_ERROR } from '$lib/utils/phone-number.js';
import { propertyValueError } from '$lib/v2/custom-field-input.js';
import { translate } from '$lib/i18n/messages.js';

/** Basic format checks, never a directory of real-world names or addresses. */
export function recordFieldError(name, raw, required = false, type = '') {
  const value = String(raw ?? '')
    .normalize('NFC')
    .trim();
  if (!value) return required ? 'This field is required.' : '';
  const custom = name.startsWith('custom_fields.');
  const kind =
    (!custom &&
      {
        phone: 'phone',
        email: 'email',
        website: 'url',
        amount: 'money',
        annual_revenue: 'money',
        number_of_employees: 'integer'
      }[name]) ||
    (type === 'tel' ? 'phone' : type);
  const formatError = propertyValueError(kind, raw, required);
  if (formatError || custom) return formatError;
  if (
    [
      'name',
      'title',
      'first_name',
      'last_name',
      'phone',
      'city',
      'state',
      'postcode',
      'address_line'
    ].includes(name) &&
    /\p{Cc}/u.test(value)
  )
    return 'Enter a single line without control characters.';
  if (
    ['city', 'state'].includes(name) &&
    (!/\p{L}/u.test(value) || /[^\p{L}\p{M}\p{N} .,'’‘‐‑–—()&/-]/u.test(value))
  )
    return `Enter a valid ${name === 'city' ? 'city' : 'state / region'} name.`;
  if (name === 'postcode' && (!/[\p{L}\p{N}]/u.test(value) || /[^\p{L}\p{N} -]/u.test(value)))
    return 'Use letters, numbers, spaces or hyphens for the postal code.';
  return '';
}

/** Accessible, consistent inline feedback for create and edit forms. */
export function recordValidation(form, serverErrors = {}) {
  const feedback = new Map();
  function clear(input) {
    const item = feedback.get(input);
    if (!item) return;
    item.message.remove();
    input.setCustomValidity('');
    if (item.described) item.control.setAttribute('aria-describedby', item.described);
    else item.control.removeAttribute('aria-describedby');
    if (item.invalid) item.control.setAttribute('aria-invalid', item.invalid);
    else item.control.removeAttribute('aria-invalid');
    feedback.delete(input);
  }
  function show(input, text) {
    clear(input);
    if (!text) return;
    for (
      let details = input.closest('details');
      details;
      details = details.parentElement?.closest('details')
    )
      details.open = true;
    const message = document.createElement('span');
    message.id = `field-error-${crypto.randomUUID()}`;
    message.className = 'v2-error';
    message.style.cssText = 'display:block;font-size:0.75rem;margin-top:0.375rem';
    text = translate(document.documentElement.lang, text);
    message.textContent = text;
    const control =
      (input.matches('select') &&
        input.closest('[data-property-control]')?.querySelector('[data-select-trigger]')) ||
      input;
    const described = control.getAttribute('aria-describedby');
    const invalid = control.getAttribute('aria-invalid');
    (input.closest('[data-property-control]') || input.closest('label') || input).after(message);
    control.setAttribute('aria-describedby', [described, message.id].filter(Boolean).join(' '));
    control.setAttribute('aria-invalid', 'true');
    input.setCustomValidity(text);
    feedback.set(input, { message, described, invalid, control });
  }
  const controls = () =>
    [...form.elements].filter((input) => input.matches('input:not([type=hidden]),select,textarea'));
  function check(input) {
    if (!input.willValidate || !input.setCustomValidity) return;
    clear(input);
    // PhoneInput may have validated before the latest country/value reached the DOM.
    // Recompute its custom error rather than preserving that stale message.
    if (input.dataset.phoneCountry) input.setCustomValidity('');
    if (input.type === 'checkbox' && !input.dataset.propertyRequired) return;

    const groupMissing =
      input.dataset.propertyRequired === 'true' &&
      !controls().some((other) => other.name === input.name && other.checked);
    const outOfRange =
      input.value !== '' &&
      input.dataset.propertyType === 'money' &&
      ((input.min !== '' && Number(input.value) < Number(input.min)) ||
        (input.max !== '' && Number(input.value) > Number(input.max)));
    show(
      input,
      (groupMissing
        ? 'This field is required.'
        : input.dataset.phoneCountry
          ? input.value.trim()
            ? normalizedPhone(input.value, input.dataset.phoneCountry)
              ? ''
              : PHONE_ERROR
            : input.required
              ? 'This field is required.'
              : ''
          : recordFieldError(
              input.name,
              input.value,
              input.required,
              input.dataset.propertyType || input.type
            )) ||
        (outOfRange ? 'Enter an amount within the allowed range.' : '') ||
        input.validationMessage
    );
  }
  function changed(event) {
    if (!controls().includes(event.target)) return;
    if (event.target.type === 'checkbox' && event.target.dataset.propertyRequired) {
      controls()
        .filter((input) => input.name === event.target.name)
        .forEach(check);
    } else check(event.target);
  }
  function blurred(event) {
    if (controls().includes(event.target)) check(event.target);
  }
  function invalid(event) {
    if (controls().includes(event.target)) check(event.target);
  }
  function submit(event) {
    controls().forEach(check);
    const first = controls().find((input) => input.willValidate && !input.validity.valid);
    if (first) {
      event.preventDefault();
      event.stopImmediatePropagation();
      first.focus();
    }
  }
  function update(errors) {
    for (const input of [...feedback.keys()]) clear(input);
    for (const [name, text] of Object.entries(errors || {})) {
      const input = controls().find((input) => (input.name || input.dataset.phoneName) === name);
      if (input && typeof text === 'string') show(input, text);
    }
    if (!form.classList.contains('auto-save')) feedback.keys().next().value?.focus();
  }
  // Tasks link their title to this form from outside it with the form attribute.
  form.ownerDocument.addEventListener('input', changed);
  form.ownerDocument.addEventListener('change', changed);
  form.ownerDocument.addEventListener('focusout', blurred);
  form.ownerDocument.addEventListener('invalid', invalid, true);
  form.addEventListener('submit', submit, true);
  update(serverErrors);
  return {
    update,
    destroy() {
      form.ownerDocument.removeEventListener('input', changed);
      form.ownerDocument.removeEventListener('change', changed);
      form.ownerDocument.removeEventListener('focusout', blurred);
      form.ownerDocument.removeEventListener('invalid', invalid, true);
      form.removeEventListener('submit', submit, true);
      for (const input of [...feedback.keys()]) clear(input);
    }
  };
}
