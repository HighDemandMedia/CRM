/** Build a paste-ready connector without letting a form ID become HTML. */
export function connectorSnippet(submitUrl, formId = '') {
  if (!/^https?:\/\//i.test(submitUrl || '')) return '';
  const id = formId.trim();
  if (id && !/^[A-Za-z][A-Za-z0-9_-]*$/.test(id)) return '';
  const source = submitUrl
    .replace(/submit\/$/, 'connect.js')
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;');
  return `<script src="${source}" data-form="${id ? '#' + id : 'form'}" data-mode="copy" defer></script>`;
}

export function previewUrl(submitUrl) {
  return /^https?:\/\//i.test(submitUrl || '') ? submitUrl.replace(/submit\/$/, 'embed/') : '';
}
