export function showStageRequirements(result, target, id, values) {
  const issue = result?.data?.stageRequirements;
  if (!issue) return false;
  window.dispatchEvent(
    new CustomEvent('crm-stage-requirements', { detail: { issue, target, id, values } })
  );
  return true;
}
export const fieldNames = (key) =>
  ({
    first_name: ['name', 'first_name'],
    tags: ['tags', 'tag_ids'],
    contacts: ['contacts', 'parent_contacts'],
    account: ['account', 'parent_account'],
    opportunity: ['opportunity', 'parent_opportunity'],
    case: ['case', 'parent_case']
  })[key] ?? [key];
