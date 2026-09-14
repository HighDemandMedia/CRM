/** @param {Record<string, any>} previous @param {Record<string, any>} next */
export function contactChanges(previous, next) {
  return Object.fromEntries(
    Object.entries(next).filter(([key, value]) => {
      if (key === 'tags')
        return (
          JSON.stringify([...(previous[key] ?? [])].sort()) !==
          JSON.stringify([...(value ?? [])].sort())
        );
      return (previous[key] ?? '') !== (value ?? '');
    })
  );
}
