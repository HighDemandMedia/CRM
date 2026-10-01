// Modules ready for the customer demonstration. Exact prefix boundaries matter.
export const DEMO_MAIN = [
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
  '/settings/pipelines',
  '/settings/tags',
  '/settings/web-forms'
];
export function demoPageAllowed(path) {
  return [...DEMO_MAIN, ...DEMO_SETTINGS].some(
    (root) => path === root || (root !== '/' && path.startsWith(root + '/'))
  );
}
