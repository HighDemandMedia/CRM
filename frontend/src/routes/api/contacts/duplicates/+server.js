import { json } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';

export async function GET({ url, cookies }) {
  const query = new URLSearchParams();
  for (const key of ['name', 'email', 'phone', 'exclude']) {
    const value = url.searchParams.get(key)?.trim();
    if (value) query.set(key, value);
  }
  try {
    const result = await apiRequest(`/contacts/duplicates/?${query}`, {}, { cookies });
    return json(result, { headers: { 'cache-control': 'no-store' } });
  } catch (error) {
    return json(
      { results: [], error: 'Could not check existing contacts.' },
      { status: error.status || 400 }
    );
  }
}
