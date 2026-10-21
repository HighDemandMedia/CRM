import { describe, expect, it } from 'vitest';
import { invitationNotice } from './invitation-notice.js';
import { invitationFailure } from '$lib/server/invitation.js';

describe('invitation recovery actions', () => {
  it('presents accepted invitations as a confirmation', () => {
    expect(invitationNotice('invitation_accepted')).toMatchObject({
      tone: 'success',
      retry: false
    });
  });
  it.each(['invitation_expired', 'invitation_invalid', 'invitation_cancelled', undefined])(
    'does not retry a terminal or unknown link: %s',
    (issue) => {
      expect(invitationNotice(issue).retry).toBe(false);
    }
  );
  it.each(['temporary', 'rate_limited'])('allows recovery for %s', (issue) => {
    expect(invitationNotice(issue).retry).toBe(true);
  });
  it('uses response codes rather than matching localized strings', () => {
    expect(
      invitationFailure({ status: 400, body: { code: 'invitation_expired', error: 'Venció' } })
    ).toBe('invitation_expired');
    expect(
      invitationFailure({ response: { status: 400, data: { error: 'Legacy generic error' } } })
    ).toBe('invitation_invalid');
    expect(invitationFailure({ response: { status: 403 } })).toBe('invitation_invalid');
    expect(invitationFailure(new Error('network offline'))).toBe('temporary');
  });
});
