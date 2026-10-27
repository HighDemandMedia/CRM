/** Canonical values keep a dismissed warning stable through formatting-only edits. */
/** @param {{ name?: string, email?: string, phone?: string, exclude?: string }} values */
export function contactDuplicateQuery({ email = '', phone = '', exclude = '' }) {
  email = email.trim().toLowerCase();
  const international = phone.trim().startsWith('+');
  phone = (international ? '+' : '') + phone.replace(/\D/g, '');
  if (!email.includes('@') && phone.length < 7) return '';
  const query = new URLSearchParams({ email, phone });
  if (exclude) query.set('exclude', exclude);
  return query.toString();
}

/** Self-assigned and customized forms can omit Ownership entirely. */
export function contactDuplicateNoticeIndex(fields) {
  const ownership = fields.findIndex((field) => field.section === 'Ownership');
  if (ownership !== -1) return ownership;
  const identity = fields.findLastIndex((field) => field.section === 'Identity');
  return identity + 1;
}
