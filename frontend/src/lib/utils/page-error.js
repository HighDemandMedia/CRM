/** Error boundaries can receive a failed client render while the page still reports 200. */
export function pageError(status) {
  const code = Number.isInteger(status) && status >= 400 && status <= 599 ? status : 500;
  const descriptions = {
    401: [
      'Please sign in to continue',
      'Your session may have expired. Sign in again to continue.'
    ],
    403: ['Access restricted', 'Ask your organization administrator to review your permissions.'],
    404: ['Page not found', 'This page is unavailable. Check the link or return to Today.'],
    429: ['Too many requests', 'Please wait a moment before trying again.']
  };
  const [title, description] =
    descriptions[code] ??
    (code >= 500
      ? [
          'Unable to load this page',
          'Please try again. If the problem continues, contact your administrator.'
        ]
      : ['Unable to open this page', 'Check the link or return to Today to continue.']);
  return { code, title, description, retry: code >= 500 || code === 429, signIn: code === 401 };
}
