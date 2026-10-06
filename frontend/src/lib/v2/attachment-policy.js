// Matches common.utils.ATTACHMENT_MAX_BYTES. The API remains authoritative.
export const ATTACHMENT_MAX_BYTES = 25 * 1024 * 1024;
export const ATTACHMENT_LIMIT_MESSAGE = 'Files must be 25 MB or smaller.';

/** @param {{size: number} | null | undefined} file */
export function attachmentError(file) {
  return file && file.size > ATTACHMENT_MAX_BYTES ? ATTACHMENT_LIMIT_MESSAGE : '';
}
