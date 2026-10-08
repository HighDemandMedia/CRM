/** Keep quoted history/signatures accessible without repeating it in every message.
 * @param {string} body
 */
export function splitEmailBody(body = '') {
  const lines = body.split('\n');
  const at = lines.findIndex(
    (line, index) =>
      index > 0 &&
      (/^\s*>/.test(line) ||
        /^On .+wrote:\s*$/.test(line) ||
        /^El .+escribió:\s*$/.test(line) ||
        /^\s*-{2,}\s*(Original Message|Mensaje original)/i.test(line) ||
        /^--\s*$/.test(line))
  );
  if (at < 0) return { text: body, quoted: '' };
  return { text: lines.slice(0, at).join('\n').trimEnd(), quoted: lines.slice(at).join('\n') };
}

/** @param {any[]} emails */
export function emailEvents(emails = []) {
  return emails.map((mail) => ({
    id: `email-${mail.id}`,
    type: /** @type {const} */ ('email'),
    at: mail.at,
    by: mail.sender,
    body: mail.subject,
    emailId: mail.id,
    href: mail.href,
    email: mail
  }));
}
