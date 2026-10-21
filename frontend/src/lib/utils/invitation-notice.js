/** Terminal links must offer a useful exit, never a retry loop.
 * @returns {{tone: 'success' | 'warning', title: string, message: string, retry: boolean}} */
export function invitationNotice(issue) {
  if (issue === 'invitation_accepted')
    return {
      tone: 'success',
      title: 'Invitation already accepted',
      message: 'Sign in to access your workspace.',
      retry: false
    };
  if (issue === 'temporary' || issue === 'rate_limited')
    return {
      tone: 'warning',
      title: issue === 'rate_limited' ? 'Too many requests' : 'Unable to open invitation',
      message: 'Please try again shortly.',
      retry: true
    };
  return {
    tone: 'warning',
    title:
      issue === 'invitation_expired'
        ? 'Invitation expired'
        : issue === 'invitation_cancelled'
          ? 'Invitation cancelled'
          : 'Invitation unavailable',
    message: 'Ask your administrator for a new invitation. If you already joined, sign in.',
    retry: false
  };
}
