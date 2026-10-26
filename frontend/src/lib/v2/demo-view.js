// Modules ready for the customer demonstration. Exact prefix boundaries matter.
export const DEMO_MAIN = [
  '/onboarding',
  '/platform-usage',
  '/',
  '/contacts',
  '/accounts',
  '/pipeline',
  '/calendar',
  '/tasks',
  '/tickets',
  '/reports',
  '/help'
];
export const DEMO_SETTINGS = [
  '/profile',
  '/notifications',
  '/settings/organization',
  '/team',
  '/settings/roles',
  '/settings/custom-fields',
  '/settings/creation-forms',
  '/settings/pipelines',
  '/settings/tags',
  '/settings/web-forms'
];
export function demoPageAllowed(path) {
  // These JSON handlers support the record screens; redirecting them returns HTML to fetch.
  // Authentication and record permissions are still checked by the server handlers and API.
  if (/^\/record-(?:delete|associations)\/(?:contact|company|deal)\/[^/]+\/?$/.test(path))
    return true;
  return [...DEMO_MAIN, ...DEMO_SETTINGS].some(
    (root) => path === root || (root !== '/' && path.startsWith(root + '/'))
  );
}
