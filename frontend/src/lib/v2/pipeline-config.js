export function configuredStages(config, target, fallback = []) {
  return config?.[target]?.stages?.map((s) => ({ ...s, value: s.key })) ?? fallback;
}
export function configuredLabel(config, target, key, fallback = '') {
  return config?.[target]?.stages?.find((s) => s.key === key)?.label ?? fallback ?? key;
}
