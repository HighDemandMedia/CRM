import { describe, expect, it, vi } from 'vitest';
vi.mock('$lib/server/v2/organization.js', () => ({
  getOrgSettings: vi.fn(async () => ({ org: {}, can_edit: true })),
  listTimezones: vi.fn(async () => []),
  updateOrgSettings: vi.fn(),
  EDITABLE_FIELDS: [],
  BOOLEAN_FIELDS: []
}));
vi.mock('$lib/server/v2/tags.js', () => ({
  getTags: vi.fn(async () => ({ tags: [], can_edit: true })),
  createTag: vi.fn(),
  archiveTag: vi.fn(),
  restoreTag: vi.fn(),
  mergeTags: vi.fn(),
  updateTag: vi.fn()
}));
vi.mock('$lib/server/v2/custom-fields.js', () => ({
  getPropertyCatalog: vi.fn(async () => ({ can_edit: true })),
  createCustomField: vi.fn(),
  updateCustomField: vi.fn(),
  deactivateCustomField: vi.fn(),
  deleteCustomField: vi.fn()
}));
vi.mock('$lib/server/v2/web-forms.js', () => ({
  getWebForms: vi.fn(async () => ({ forms: [], canManage: true })),
  getWebForm: vi.fn(async () => ({ form: {}, canManage: true })),
  getSubmissions: vi.fn(async () => ({ submissions: [] })),
  getAnalytics: vi.fn(async () => ({})),
  createWebForm: vi.fn(),
  updateWebForm: vi.fn(),
  deleteWebForm: vi.fn(),
  publishWebForm: vi.fn(),
  unpublishWebForm: vi.fn()
}));
import { load as organization } from './organization/+page.server.js';
import { load as editOrganization } from './organization/edit/+page.server.js';
import { load as tags } from './tags/+page.server.js';
import { load as properties } from './custom-fields/+page.server.js';
import { load as forms } from './web-forms/+page.server.js';
import { load as form } from './web-forms/[id]/+page.server.js';
const event = (admin) =>
  /** @type {any} */ ({
    cookies: {},
    params: { id: 'form-id' },
    url: new URL('https://crm.example.test/settings'),
    parent: async () => ({ permissions: { is_admin: admin } })
  });
describe('Settings editor access freshness', () => {
  it.each([
    ['organization', organization, 'can_edit'],
    ['tags', tags, 'can_edit'],
    ['properties', properties, 'can_edit'],
    ['forms', forms, 'canManage'],
    ['form', form, 'canManage']
  ])('%s ignores stale administrator hints', async (_name, load, flag) => {
    expect(await load(event(false))).toHaveProperty(flag, false);
    expect(await load(event(true))).toHaveProperty(flag, true);
    expect(await load(event(undefined))).toHaveProperty(flag, false);
  });
  it('also protects the legacy organization editor after demotion', async () => {
    expect(await editOrganization(event(false))).toEqual({ forbidden: true });
  });
});

it.each([
  ['organization', organization, 'can_edit'],
  ['tags', tags, 'can_edit'],
  ['properties', properties, 'can_edit'],
  ['forms', forms, 'canManage'],
  ['forms', form, 'canManage']
])('honors delegated %s read/manage access independently', async (key, load, flag) => {
  for (const level of ['none', 'read', 'manage']) {
    const delegated = {
      ...event(false),
      parent: async () => ({ permissions: { is_admin: false, settings_access: { [key]: level } } })
    };
    expect(await load(delegated)).toHaveProperty(flag, level === 'manage');
  }
});
