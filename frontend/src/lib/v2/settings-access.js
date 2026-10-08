// Display hints from fresh API permissions. Every endpoint enforces its own access.
export const settingsSections = [
  { key: 'profile', group: 'Personal', label: 'Profile', href: '/profile', member: 'personal' },
  {
    key: 'notifications',
    group: 'Personal',
    label: 'Notifications',
    href: '/notifications',
    member: 'personal'
  },
  {
    key: 'organization',
    group: 'Organization & access',
    label: 'Organization',
    href: '/settings/organization',
    member: 'none'
  },
  {
    key: 'team',
    group: 'Organization & access',
    label: 'Users & Teams',
    href: '/team',
    member: 'none'
  },
  {
    key: 'roles',
    group: 'Organization & access',
    label: 'Roles & Permissions',
    href: '/settings/roles',
    member: 'none'
  },
  {
    key: 'properties',
    group: 'CRM configuration',
    label: 'Properties',
    href: '/settings/custom-fields',
    member: 'none'
  },
  {
    key: 'creation_forms',
    group: 'CRM configuration',
    label: 'Creation forms',
    href: '/settings/creation-forms',
    member: 'none'
  },
  {
    key: 'pipelines',
    group: 'CRM configuration',
    label: 'Pipelines',
    href: '/settings/pipelines',
    member: 'none'
  },
  {
    key: 'tags',
    group: 'CRM configuration',
    label: 'Tags',
    href: '/settings/tags',
    member: 'none'
  },
  {
    key: 'forms',
    group: 'Channels & integrations',
    label: 'Web forms',
    href: '/settings/web-forms',
    member: 'none',
    beta: true
  }
];

export function settingsGroups(permissions) {
  const groups = [];
  for (const section of settingsSections) {
    const access = settingsAccess(permissions, section.key);
    if (access === 'none') continue;
    let group = groups.find((item) => item.label === section.group);
    if (!group) {
      group = { label: section.group, items: [] };
      groups.push(group);
    }
    group.items.push({ ...section, access });
  }
  return groups;
}

export function settingsAccess(permissions, key) {
  const section = settingsSections.find((item) => item.key === key);
  if (!section) return 'none';
  if (section.member === 'personal') return 'personal';
  if (permissions?.is_admin === true) return 'manage';
  if (['team', 'roles'].includes(key)) return 'none';
  const access = permissions?.settings_access?.[key];
  return ['read', 'manage'].includes(access) ? access : 'none';
}

export function canOpenSettingsPath(permissions, pathname) {
  const section = settingsSections.find(
    (item) => pathname === item.href || pathname?.startsWith(item.href + '/')
  );
  return !section || settingsAccess(permissions, section.key) !== 'none';
}
