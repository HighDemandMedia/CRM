/** Display a user's saved name across Profile, User and lookup payloads. */
export function userName(profile, fallback = 'Unnamed user') {
  const user = profile?.user_details ?? profile?.user ?? profile ?? {};
  return (
    String(user.name || profile?.user__name || '').trim() ||
    user.email ||
    profile?.user__email ||
    fallback
  );
}
