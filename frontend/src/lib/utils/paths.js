/**
 * Mark a dynamically assembled string as an internal pathname.
 *
 * @param {string} path
 * @returns {any}
 */
export function asInternalPath(path) {
  return path;
}

/**
 * Convert an already browser-resolved path back to an app path before resolve().
 * Only remove the configured base at a path boundary, never a similarly named route.
 * @param {string} path
 * @param {string} base
 */
export function withoutBase(path, base) {
  if (!base) return path;
  if (path === base) return '/';
  if (path.startsWith(`${base}/`)) return path.slice(base.length);
  if (path.startsWith(`${base}?`) || path.startsWith(`${base}#`))
    return `/${path.slice(base.length)}`;
  return path;
}
