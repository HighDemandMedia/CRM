import { describe, expect, it } from 'vitest';
import {
  emailEvents,
  splitEmailBody,
  replyRecipients,
  emailTextParts
} from './email-presentation.js';

describe('email presentation', () => {
  it('replies to Reply-To and adds other participants only for Reply all', () => {
    const message = {
      account: 'me@example.test',
      direction: 'received',
      sender: 'Sender <sender@example.test>',
      reply_to: ['reply@example.test'],
      recipients: ['ME@example.test', 'other@example.test'],
      cc: ['other@example.test', 'cc@example.test', 'me@example.test']
    };
    expect(replyRecipients(message)).toEqual({ to: ['reply@example.test'], cc: [] });
    expect(replyRecipients(message, true)).toEqual({
      to: ['reply@example.test', 'other@example.test'],
      cc: ['cc@example.test']
    });
  });
  it('replies to the original recipients of sent messages, preserving CC only for Reply all', () => {
    const message = {
      account: 'me@example.test',
      direction: 'sent',
      recipients: ['Ana <ana@example.test>'],
      cc: ['cc@example.test']
    };
    expect(replyRecipients(message)).toEqual({ to: ['ana@example.test'], cc: [] });
    expect(replyRecipients(message, true)).toEqual({
      to: ['ana@example.test'],
      cc: ['cc@example.test']
    });
  });
  it('does not make executable schemes or markup into links', () => {
    const text =
      '<img onerror=alert(1)> javascript:alert(1) See https://example.test/quote?a=1&b=2.';
    const parts = emailTextParts(text);
    expect(parts.filter((part) => part.href)).toEqual([
      { text: 'https://example.test/quote?a=1&b=2', href: 'https://example.test/quote?a=1&b=2' }
    ]);
    expect(parts.map((part) => part.text).join('')).toBe(text);
  });
  it.each([
    'On Monday, Ana wrote:',
    'El lunes Ana escribió:',
    '> Previous message',
    '--',
    '-----Original Message-----'
  ])('keeps quoted content accessible: %s', (marker) => {
    const result = splitEmailBody(`New answer\n\n${marker}\nPrevious content`);
    expect(result.text).toBe('New answer');
    expect(result.quoted).toBe(`${marker}\nPrevious content`);
  });
  it('preserves plain messages and a quoted first line', () => {
    expect(splitEmailBody('> Question\nAnswer')).toEqual({
      text: '> Question\nAnswer',
      quoted: ''
    });
    expect(splitEmailBody()).toEqual({ text: '', quoted: '' });
  });
  it('retains participants and thread metadata in the timeline', () => {
    const mail = {
      id: '1',
      thread_id: 'thread',
      sender: 'sender@example.test',
      recipients: ['to@example.test'],
      subject: 'Hello',
      at: '2026-10-07',
      direction: 'received'
    };
    expect(emailEvents([mail])[0]).toMatchObject({
      id: 'email-1',
      type: 'email',
      body: 'Hello',
      email: mail
    });
  });
});
