import { describe, expect, it } from 'vitest';
import {
  mailAttachmentError,
  MAIL_ATTACHMENT_MAX_BYTES,
  mailEditorDocument
} from './mail-composition.js';

describe('email composition boundaries', () => {
  it('limits aggregate file sizes, counts and empty files', () => {
    expect(mailAttachmentError([{ size: MAIL_ATTACHMENT_MAX_BYTES }])).toBe('');
    expect(mailAttachmentError([{ size: MAIL_ATTACHMENT_MAX_BYTES }, { size: 1 }])).toContain(
      '10 MB'
    );
    expect(mailAttachmentError(Array.from({ length: 11 }, () => ({ size: 1 })))).toContain(
      '10 files'
    );
    expect(mailAttachmentError([{ size: 0 }])).toContain('Empty');
  });
  it('preserves forwarded markup as text rather than editor HTML', () => {
    const result = mailEditorDocument('<img src=x onerror=alert(1)>\nNext line');
    expect(result.content[0].content).toEqual([
      { type: 'text', text: '<img src=x onerror=alert(1)>' }
    ]);
    expect(result.content).toHaveLength(2);
  });
});
