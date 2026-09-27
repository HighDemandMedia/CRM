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
