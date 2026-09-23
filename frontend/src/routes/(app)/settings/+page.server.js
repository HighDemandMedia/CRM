import { redirect } from '@sveltejs/kit';
import { resolve } from '$app/paths';

// Keep old settings links working; settings now live in the preferences navigation.
export function load() {
  redirect(303, resolve('/profile'));
}
