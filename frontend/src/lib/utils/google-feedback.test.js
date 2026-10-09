import { describe, expect, it } from 'vitest';
import { googleErrorMessage, googleCallbackMessage } from './google-feedback.js';

describe('Google connection feedback', () => {
  it.each([
    { body: ['The required Google permissions were not granted. Connect again.'] },
    { body: { errors: ['The required Google permissions were not granted. Connect again.'] } },
    new Error('The required Google permissions were not granted. Connect again.')
  ])('preserves actionable permission feedback across API formats', (error) => {
    expect(googleErrorMessage(error)).toBe(
      'The required Google permissions were not granted. Connect again.'
    );
  });
  it.each([
    new SyntaxError('Unexpected end of JSON input'),
    new Error('secret token abc'),
    '<html>502 Bad Gateway</html>',
    { body: { secret: 'abc' } }
  ])('does not expose technical or provider payloads', (error) => {
    expect(googleErrorMessage(error)).toBe('Google is unavailable. Try syncing again later.');
  });
  it('distinguishes CRM permissions from Google authorization', () => {
    expect(googleErrorMessage({ status: 403 })).toContain('organization administrator');
    expect(googleErrorMessage('Reconnect Google to restore access.')).toContain('Reconnect Google');
  });
  it('does not display arbitrary callback query strings', () => {
    expect(googleCallbackMessage('secret')).toBe('');
    expect(googleCallbackMessage('__proto__')).toBe('');
    expect(googleCallbackMessage('constructor')).toBe('');
    expect(googleCallbackMessage('permissions')).toContain('permissions');
  });
});
