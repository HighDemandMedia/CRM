export const MAIL_ATTACHMENT_MAX_BYTES = 10 * 1024 * 1024;
export const MAIL_ATTACHMENT_MAX_COUNT = 10;

/** @param {{size:number}[]} files */
export function mailAttachmentError(files) {
  if (files.length > MAIL_ATTACHMENT_MAX_COUNT) return 'Attach up to 10 files.';
  if (files.some((file) => !file.size)) return 'Empty files cannot be attached.';
  if (files.reduce((total, file) => total + file.size, 0) > MAIL_ATTACHMENT_MAX_BYTES)
    return 'Attachments must total 10 MB or less.';
  return '';
}

/** @param {number} bytes */
export function mailFileSize(bytes) {
  return bytes >= 1024 * 1024
    ? `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    : `${Math.max(1, Math.ceil(bytes / 1024))} KB`;
}

/** Plain text is encoded as editor nodes, never interpreted as markup. @param {string} text */
export function mailEditorDocument(text) {
  return {
    type: 'doc',
    content: text.split('\n').map((line) => ({
      type: 'paragraph',
      ...(line ? { content: [{ type: 'text', text: line }] } : {})
    }))
  };
}
