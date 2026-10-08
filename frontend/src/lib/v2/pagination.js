export const PAGE_SIZES = [10, 25, 50, 100];
export const DEFAULT_PAGE_SIZE = 25;

/** Keep filters and sorting; a size change starts from the first page. */
export function paginationHref(url, { offset, pageSize }) {
  const params = new URLSearchParams(url.searchParams);
  if (pageSize !== undefined) {
    params.set('page_size', String(pageSize));
    params.delete('offset');
  } else if (offset > 0) params.set('offset', String(offset));
  else params.delete('offset');
  return `${url.pathname}?${params}`;
}
