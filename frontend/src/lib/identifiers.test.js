import { describe, expect, it } from 'vitest';
import { displayRecordId, isRecordId } from './identifiers.js';

describe('business identifiers', () => {
  it('accepts compact business IDs and auxiliary UUIDs', () => {
    for (const id of [
      'HDM-7K9M4R8Q',
      'USR-0001',
      'CON-0001',
      'COM-10000',
      'DEA-0001',
      'TSK-0001',
      'TKT-0001',
      'EVT-0001',
      '01a078c7-1e1c-73b0-9ea4-27f4c797c1cf'
    ]) {
      expect(isRecordId(id)).toBe(true);
    }
  });
  it('rejects malformed values and preserves compact IDs when displaying them', () => {
    for (const id of ['ORG001', 'HDM-OOOOOOOO', 'CON-1', '', null, 'CON-0001/', 'CON-0001\n']) {
      expect(isRecordId(id)).toBe(false);
    }
    expect(displayRecordId('HDM-7K9M4R8Q')).toBe('HDM-7K9M4R8Q');
    expect(displayRecordId('CON-10000')).toBe('CON-10000');
  });
});
