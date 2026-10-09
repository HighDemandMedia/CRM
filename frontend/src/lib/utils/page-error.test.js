import { describe, expect, it } from 'vitest';
import { pageError } from './page-error.js';

describe('page error recovery', () => {
  it.each([200, 0, undefined, NaN, 600])('normalizes an invalid error status %s', (status) => {
    expect(pageError(status)).toMatchObject({ code: 500, retry: true, signIn: false });
  });
  it('offers sign-in for expired sessions, not retries', () => {
    expect(pageError(401)).toMatchObject({ code: 401, retry: false, signIn: true });
  });
  it('does not disclose record existence for forbidden access', () => {
    expect(pageError(403)).toMatchObject({ title: 'Access restricted', retry: false });
    expect(pageError(403).description).not.toMatch(/exists|belongs|deleted/);
  });
  it('distinguishes missing pages from transient failures', () => {
    expect(pageError(404)).toMatchObject({ title: 'Page not found', retry: false });
    expect(pageError(503)).toMatchObject({ title: 'Unable to load this page', retry: true });
    expect(pageError(429)).toMatchObject({ title: 'Too many requests', retry: true });
  });
});
