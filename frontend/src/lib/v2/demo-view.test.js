import { describe, expect, it } from 'vitest';
import { demoPageAllowed } from './demo-view.js';

describe('customer demo routes', () => {
  it('allows ready record screens and reviewed settings', () => {
    for (const route of [
      '/',
      '/contacts',
      '/imports/contacts',
      '/imports/companies',
      '/imports/deals',
      '/imports/tasks',
      '/imports/tickets',
      '/contacts/123/edit',
      '/accounts/new',
      '/record-delete/contact/123',
      '/record-delete/company/123',
      '/record-delete/deal/123',
      '/record-associations/company/123',
      '/pipeline/123',
      '/calendar',
      '/tasks',
      '/tickets',
      '/help',
      '/help/knowledge/contacts',
      '/profile',
      '/settings/pipelines',
      '/team',
      '/settings/roles',
      '/settings/custom-fields',
      '/settings/creation-forms',
      '/settings/tags',
      '/settings/web-forms'
    ]) {
      expect(demoPageAllowed(route), route).toBe(true);
    }
  });
  it('excludes unfinished modules and similar prefixes', () => {
    for (const route of [
      '/leads',
      '/imports/users',
      '/imports/contacts/extra',
      '/invoices/123',
      '/documents',
      '/solutions',
      '/goals',
      '/settings/api-tokens',
      '/contacts-other',
      '/record-delete',
      '/record-delete/user/123',
      '/record-delete/contact/123/extra',
      '/record-delete-other/contact/123'
    ]) {
      expect(demoPageAllowed(route), route).toBe(false);
    }
  });
});
