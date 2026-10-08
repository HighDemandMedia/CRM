import { describe, expect, it } from 'vitest';
import { settingsGroups, settingsSections } from './settings-access.js';
const items = (permissions) => settingsGroups(permissions).flatMap((group) => group.items);
describe('Settings navigation', () => {
  it('only exposes personal preferences to ordinary members', () => {
    expect(items({ is_admin: false }).map((item) => item.key)).toEqual([
      'profile',
      'notifications'
    ]);
  });
  it('exposes only explicit Manager grants and never delegates role management', () => {
    const sections = items({
      settings_access: { organization: 'read', tags: 'manage', roles: 'manage', forms: true }
    });
    expect(sections.map((item) => item.key)).toEqual([
      'profile',
      'notifications',
      'organization',
      'tags'
    ]);
    expect(sections.find((item) => item.key === 'organization').access).toBe('read');
    expect(sections.find((item) => item.key === 'tags').access).toBe('manage');
  });
  it('does not treat organization-wide record scope or a missing response as admin access', () => {
    for (const permissions of [
      undefined,
      {},
      { is_admin: 'true' },
      { rules: { contacts: { view: 'organization', edit: 'organization' } } }
    ]) {
      expect(
        items(permissions).some((item) => ['team', 'roles', 'properties'].includes(item.key))
      ).toBe(false);
    }
  });
  it('updates immediately when admin access is revoked and preserves personal ownership', () => {
    expect(items({ is_admin: true }).map((item) => item.key)).toEqual(
      settingsSections.map((item) => item.key)
    );
    expect(items({ is_admin: true }).find((item) => item.key === 'profile').access).toBe(
      'personal'
    );
    expect(items({ is_admin: false }).some((item) => item.access === 'manage')).toBe(false);
  });
});
