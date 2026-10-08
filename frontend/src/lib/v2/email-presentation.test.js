import { describe, expect, it } from 'vitest';
import { emailEvents, splitEmailBody } from './email-presentation.js';

describe('email presentation', () => {
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
