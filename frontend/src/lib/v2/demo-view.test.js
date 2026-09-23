import { describe, expect, it } from 'vitest';
import { demoPageAllowed } from './demo-view.js';

describe('customer demo routes', () => {
  it('allows ready record screens and reviewed settings', () => {
    for (const route of ['/', '/contacts', '/contacts/123/edit', '/accounts/new', '/pipeline/123', '/calendar', '/tasks', '/tickets', '/profile', '/settings/pipelines', '/team', '/settings/roles', '/settings/custom-fields']) {
      expect(demoPageAllowed(route), route).toBe(true);
    }
  });
  it('excludes unfinished modules and similar prefixes', () => {
    for (const route of ['/leads', '/invoices/123', '/documents', '/solutions', '/goals', '/help', '/settings/tags', '/settings/api-tokens', '/contacts-other']) {
      expect(demoPageAllowed(route), route).toBe(false);
    }
  });
});
