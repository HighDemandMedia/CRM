/** Basic format checks, never a directory of real-world names or addresses. */
export function recordFieldError(name, raw, required = false) {
  const value = String(raw ?? '')
    .normalize('NFC')
    .trim();
  if (!value) return required ? 'This field is required.' : '';
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
    (!/\p{L}/u.test(value) || /[^\p{L}\p{M}\p{N} .,'’‘‐‑–—()&/\-]/u.test(value))
  )
    return `Enter a valid ${name === 'city' ? 'city' : 'state / region'} name.`;
  if (name === 'postcode' && (!/[\p{L}\p{N}]/u.test(value) || /[^\p{L}\p{N} -]/u.test(value)))
    return 'Use letters, numbers, spaces or hyphens for the postal code.';
  if (
    name === 'phone' &&
    (!/^\+?[0-9 ().-]+$/.test(value) ||
      (value.match(/[0-9]/g) || []).length < 7 ||
      (value.match(/[0-9]/g) || []).length > 15)
  )
    return 'Enter 7 to 15 digits, with an optional country code (+) and separators.';
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
    if (item.described) input.setAttribute('aria-describedby', item.described);
    else input.removeAttribute('aria-describedby');
    if (item.invalid) input.setAttribute('aria-invalid', item.invalid);
    else input.removeAttribute('aria-invalid');
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
    message.style.cssText = 'display:block;font-size:12px;margin-top:6px';
    message.textContent = text;
    const described = input.getAttribute('aria-describedby');
    const invalid = input.getAttribute('aria-invalid');
    (input.closest('label') || input).after(message);
    input.setAttribute('aria-describedby', [described, message.id].filter(Boolean).join(' '));
    input.setAttribute('aria-invalid', 'true');
    input.setCustomValidity(text);
    feedback.set(input, { message, described, invalid });
  }
  const controls = () => [...form.querySelectorAll('input:not([type=hidden]),select,textarea')];
  function check(input) {
    if (!input.name || input.disabled || !input.setCustomValidity) return;
    clear(input);
    show(
      input,
      recordFieldError(input.name, input.value, input.required) || input.validationMessage
    );
  }
  function changed(event) {
    if (feedback.has(event.target)) check(event.target);
  }
  function blurred(event) {
    check(event.target);
  }
  function invalid(event) {
    check(event.target);
  }
  function submit(event) {
    controls().forEach(check);
    const first = controls().find((input) => !input.validity.valid);
    if (first) {
      event.preventDefault();
      event.stopImmediatePropagation();
      first.focus();
    }
  }
  function update(errors) {
    for (const input of [...feedback.keys()]) clear(input);
    for (const [name, text] of Object.entries(errors || {})) {
      const input = controls().find((input) => input.name === name);
      if (input && typeof text === 'string') show(input, text);
    }
    if (!form.classList.contains('auto-save')) feedback.keys().next().value?.focus();
  }
  form.addEventListener('input', changed);
  form.addEventListener('change', changed);
  form.addEventListener('focusout', blurred);
  form.addEventListener('invalid', invalid, true);
  form.addEventListener('submit', submit, true);
  update(serverErrors);
  return {
    update,
    destroy() {
      form.removeEventListener('input', changed);
      form.removeEventListener('change', changed);
      form.removeEventListener('focusout', blurred);
      form.removeEventListener('invalid', invalid, true);
      form.removeEventListener('submit', submit, true);
      for (const input of [...feedback.keys()]) clear(input);
    }
  };
}
