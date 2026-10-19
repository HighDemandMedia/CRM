/** Pending setup is supplied by the API for the current membership, never a URL flag. */
export function setupDestination(step) {
  if (['profile', 'profile_organization', 'organization'].includes(step)) return '/onboarding';
  return null;
}
