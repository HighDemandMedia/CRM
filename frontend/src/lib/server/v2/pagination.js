import { redirect } from '@sveltejs/kit';
import { PAGE_SIZES, DEFAULT_PAGE_SIZE } from '$lib/v2/pagination.js';

export function listPagination(url, enabled = true) {
  const requested = Number(url.searchParams.get('page_size'));
  const pageSize = enabled && PAGE_SIZES.includes(requested) ? requested : DEFAULT_PAGE_SIZE;
  const rawOffset = Math.max(
    0,
    Math.min(10000000, Number.parseInt(url.searchParams.get('offset') ?? '0') || 0)
  );
  const offset = enabled ? Math.floor(rawOffset / pageSize) * pageSize : 0;
  return { pageSize, offset };
}

/** A deleted record or stale bookmark must not strand a list on an empty page. */
export function checkListPage(url, { pageSize, offset }, count) {
  if (offset > 0 && offset >= count) {
    const next = new URL(url);
    next.searchParams.set(
      'offset',
      String(Math.max(0, Math.ceil(count / pageSize) - 1) * pageSize)
    );
    redirect(303, next.pathname + next.search);
  }
}
