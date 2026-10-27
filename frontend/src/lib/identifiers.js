const BUSINESS_ID = /^(?:HDM-[0-9A-HJKMNP-TV-Z]{8}|(?:USR|CON|COM|DEA|TSK|TKT|EVT)-[0-9]{4,20})$/;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** Shape validation only; the API enforces existence and access permissions.
 * @param {unknown} value
 */
export function isRecordId(value) {
  return (
    typeof value === 'string' &&
    value.trim() === value &&
    (BUSINESS_ID.test(value) || UUID.test(value))
  );
}

/** @param {unknown} value */
export function displayRecordId(value) {
  const id = String(value ?? '');
  return id.length > 24 ? `${id.slice(0, 8)}…${id.slice(-4)}` : id;
}
