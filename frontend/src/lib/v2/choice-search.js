/** Search localized labels and optional aliases without requiring accents. */
export function matchesChoice(option, query) {
  const normalize = (text) =>
    String(text)
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase();
  return normalize(`${option.label} ${option.keywords || ''}`).includes(normalize(query.trim()));
}
