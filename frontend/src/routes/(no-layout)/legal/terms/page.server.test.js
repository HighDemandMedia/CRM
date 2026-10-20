import { expect, it, vi } from 'vitest';
import { load } from './+page.server.js';

it.each(['en', 'es'])('makes the terms readable before signing in (%s)', (language) => {
  const setHeaders = vi.fn();
  const result = load(
    /** @type {any} */ ({
      cookies: { get: () => undefined },
      url: new URL(`https://crm.example.com/legal/terms?lang=${language}`),
      setHeaders
    })
  );
  expect(result.language).toBe(language);
  expect(result.draft).toBe(false);
  expect(result.document.sections).toHaveLength(8);
  expect(setHeaders).toHaveBeenCalledWith(
    expect.objectContaining({ 'X-Robots-Tag': 'noindex, nofollow' })
  );
});
