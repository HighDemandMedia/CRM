export const appearanceDefaults = {
  title: '',
  description: '',
  button_color: '#343234',
  text_color: '#343234',
  background_color: '#ffffff',
  font: 'system',
  width: 640,
  radius: 8,
  columns: 1
};
export const formFonts = {
  system: 'system-ui, -apple-system, sans-serif',
  arial: 'Arial, Helvetica, sans-serif',
  georgia: 'Georgia, serif'
};

export function buttonTextColor(hex) {
  const c = [1, 3, 5]
    .map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
    .map((v) => (v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  return c[0] * 0.2126 + c[1] * 0.7152 + c[2] * 0.0722 > 0.179 ? '#000000' : '#ffffff';
}

export function suggestProperty(name, type = '') {
  const key = name.toLowerCase().replace(/[^a-z0-9]/g, '');
  if (type === 'email' || /email|correo/.test(key)) return 'email';
  if (/lastname|surname|apellido/.test(key)) return 'last_name';
  if (/firstname|fullname|yourname|nombre/.test(key) || key === 'name') return 'first_name';
  if (type === 'tel' || /phone|telefono|mobile/.test(key)) return 'phone';
  if (/company|business|empresa|organization/.test(key)) return 'organization';
  if (/message|mensaje|comments|description/.test(key)) return 'description';
  if (/postcode|zipcode|postal/.test(key)) return 'postcode';
  if (/country|pais/.test(key)) return 'country';
  if (/city|ciudad/.test(key)) return 'city';
  if (/state|region|provincia/.test(key)) return 'state';
  if (/address|direccion/.test(key)) return 'address_line';
  return '';
}

/** Parse only in an inert template. Never attach its contents, execute scripts, or fetch resources. */
export function inspectFormHtml(html, doc = document) {
  if (!html.trim()) throw new Error('Paste the HTML of your form first.');
  if (html.length > 200000) throw new Error('Paste only the form HTML (maximum 200 KB).');
  const template = doc.createElement('template');
  template.innerHTML = html;
  const forms = [...template.content.querySelectorAll('form')];
  if (!forms.length) throw new Error('Include the opening <form> and closing </form> tags.');
  return forms.map((form, index) => {
    const seen = new Set();
    const inputs = [...form.querySelectorAll('input, textarea, select')]
      .filter((input) => {
        const name = input.getAttribute('name') || '';
        const type = (input.getAttribute('type') || '').toLowerCase();
        if (
          !name ||
          input.matches(':disabled') ||
          ['password', 'hidden', 'file', 'submit', 'button', 'reset', 'image'].includes(type) ||
          seen.has(name)
        )
          return false;
        seen.add(name);
        return true;
      })
      .map((input) => {
        const name = input.getAttribute('name') || '';
        const id = input.getAttribute('id');
        const label =
          [...form.querySelectorAll('label')]
            .find((l) => id && l.htmlFor === id)
            ?.textContent?.trim() ||
          input.getAttribute('aria-label') ||
          name;
        return {
          name,
          label: label.slice(0, 128),
          property: suggestProperty(name, input.getAttribute('type') || ''),
          required: input.hasAttribute('required')
        };
      });
    return { id: form.id, label: form.id || `Form ${index + 1}`, inputs };
  });
}

/** Build suggestions only; unknown fields remain visible until mapped or explicitly ignored. */
export function mappingRows(inputs) {
  const used = new Set();
  return inputs.map((input) => {
    const property = used.has(input.property) ? '' : input.property;
    if (property) used.add(property);
    return { ...input, property };
  });
}
