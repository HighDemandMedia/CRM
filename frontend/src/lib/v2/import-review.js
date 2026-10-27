/** Error-only CSV retains editable source fields; diagnostic columns are ignored on reupload. */
export function errorReportCsv(records, fields, translate = (text) => text) {
  const keys = fields.map((field) => field.key);
  const cell = (value) => {
    let text = String(value ?? '');
    // Neutralize spreadsheet formulas, retaining valid international phone numbers.
    if (/^[\s]*[=+@-]/.test(text) && !/^\+\d{1,15}$/.test(text)) text = `'${text}`;
    return `"${text.replaceAll('"', '""')}"`;
  };
  const rows = [
    [...keys, '__import_row', '__import_errors'],
    ...records.map((record) => [
      ...keys.map((key) => record.values[key] ?? ''),
      record.row,
      record.errors.map((error) => `${error.field}: ${translate(error.message)}`).join(' | ')
    ])
  ];
  return '\ufeff' + rows.map((row) => row.map(cell).join(',')).join('\r\n') + '\r\n';
}

/** Resume using durable server counts, including when an earlier response was lost. */
export async function importBatches(send, start, onProgress) {
  let completed = start;
  for (;;) {
    const result = await send(completed);
    if (
      !Number.isInteger(result.created) ||
      result.created < completed ||
      result.created > result.total ||
      (!result.complete && result.created === completed)
    ) {
      throw new Error(
        'Could not confirm import progress. Retry the same file to check its result.'
      );
    }
    completed = result.created;
    onProgress(completed);
    if (result.complete) return result;
  }
}
