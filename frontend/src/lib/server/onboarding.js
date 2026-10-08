/** Pending setup is supplied by the API for the current membership, never a URL flag. */
export function setupDestination(step) {
  if (step === 'profile' || step === 'profile_organization') return '/profile';
  if (step === 'organization') return '/settings/organization';
  return null;
}
