const MAX_PRELOAD_AGE_MS = 5000;

/** One short-lived navigation hint, not a record or permissions cache.
 * SvelteKit owns the response and clears it on navigation/invalidation.
 */
export function createViewNavigation({ preload, navigate, now = Date.now }) {
  let hint = null;
  return {
    prepare(href) {
      if (!href || hint?.href === href) return;
      hint = { href, started: now() };
      // A failed speculative read must never prevent a real navigation/retry.
      void preload(href).catch(() => {});
    },
    go(href) {
      const stale = hint && now() - hint.started >= MAX_PRELOAD_AGE_MS;
      hint = null;
      return navigate(href, {
        keepFocus: true,
        noScroll: true,
        ...(stale ? { invalidateAll: true } : {})
      });
    }
  };
}
