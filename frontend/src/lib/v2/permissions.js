/** UI hints only; the API checks the current policy and record scope on every request. */
export function can(permissions, module, action = 'view') {
  const value = permissions?.rules?.[module]?.[action];
  return value === true || ['own', 'team', 'organization'].includes(value);
}
export function recordModule(pathname) {
  return {
    contacts: 'contacts',
    accounts: 'companies',
    pipeline: 'deals',
    tasks: 'tasks',
    tickets: 'tickets'
  }[pathname.split('/')[1]];
}

/** An owner filter is redundant when only the viewer's own records are visible. */
export function canFilterOwners(permissions, module) {
  return ['team', 'organization'].includes(permissions?.rules?.[module]?.view);
}

/** No owner picker is needed for self-assigned records. */
export function canChooseOwner(permissions, module) {
  return ['team', 'organization'].includes(permissions?.rules?.[module]?.reassign);
}
