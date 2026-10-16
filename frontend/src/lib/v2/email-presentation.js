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

/** Keep reply recipients explicit; never include the connected mailbox twice.
 * @param {any} message
 * @param {boolean} all
 */
export function replyRecipients(message, all = false) {
  const address = (value = '') => (value.match(/<([^<>]+)>/)?.[1] || value).trim();
  const own = address(message.account).toLowerCase();
  const seen = new Set([own]);
  const unique = (values) =>
    values.map(address).filter((value) => {
      const key = value.toLowerCase();
      if (!key || seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  const targets =
    message.direction === 'sent'
      ? message.recipients || []
      : message.reply_to?.length
        ? message.reply_to
        : [message.sender];
  const to = unique(
    all && message.direction !== 'sent' ? [...targets, ...(message.recipients || [])] : targets
  );
  return { to, cc: all ? unique(message.cc || []) : [] };
}

/** Link only explicit web URLs; the rest remains escaped text, never raw HTML.
 * @param {string} text
 */
export function emailTextParts(text = '') {
  const parts = [];
  const pattern = /https?:\/\/[^\s<>"']+/gi;
  let end = 0;
  for (const match of text.matchAll(pattern)) {
    const url = match[0].replace(/[.,;:!?)\]]+$/, '');
    parts.push({ text: text.slice(end, match.index), href: '' });
    parts.push({ text: url, href: url });
    end = match.index + url.length;
  }
  parts.push({ text: text.slice(end), href: '' });
  return parts;
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
