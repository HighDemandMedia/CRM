import { it, expect } from 'vitest';
import { attachmentError, ATTACHMENT_MAX_BYTES } from './attachment-policy.js';
it('accepts the boundary and rejects even one byte above it', () => {
  expect(attachmentError(null)).toBe('');
  expect(attachmentError({ size: ATTACHMENT_MAX_BYTES })).toBe('');
  expect(attachmentError({ size: ATTACHMENT_MAX_BYTES + 1 })).toBe(
    'Files must be 25 MB or smaller.'
  );
});
