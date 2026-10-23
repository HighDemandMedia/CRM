/** Canonical values keep a dismissed warning stable through formatting-only edits. */
export function contactDuplicateQuery({ name = '', email = '', phone = '', exclude = '' }) {
  name = name.trim().replace(/\s+/g, ' ').toLowerCase();
  email = email.trim().toLowerCase();
  phone = phone.replace(/\D/g, '');
  if (name.length < 3 && !email.includes('@') && phone.length < 7) return '';
  const query = new URLSearchParams({ name, email, phone });
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
