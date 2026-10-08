import { describe, expect, it } from 'vitest';
import {
  creationPayload,
  initialCreationValues,
  missingCreationFields
} from './creation-values.js';
const field = (key, extra = {}) => ({ key, field_type: 'text', ...extra });
describe('configured creation values', () => {
  it('keeps custom false/zero and selected arrays across validation failures', () => {
    const fields = [
      field('first_name'),
      field('contacts', { multiple: true }),
      field('custom_fields.count', { custom: true }),
      field('custom_fields.flag', { custom: true })
    ];
    const values = initialCreationValues(
      'Contact',
      fields,
      {},
      { name: 'Claudia', contacts: ['one'], custom_fields: { count: 0, flag: false } }
    );
    expect(creationPayload('Contact', fields, values)).toEqual({
      name: 'Claudia',
      contacts: ['one'],
      custom_fields: { count: 0, flag: false }
    });
    expect(
      missingCreationFields(
        fields.map((f) => ({ ...f, required: true })),
        values
      )
    ).toEqual([]);
  });
  it('sends only selected fields and leaves empty task parent relations absent', () => {
    const fields = [
      field('title'),
      field('account', { relation: 'Account' }),
      field('case', { relation: 'Case' }),
      field('reminder_days')
    ];
    expect(
      creationPayload('Task', fields, {
        title: 'Call',
        account: 'a',
        case: '',
        reminder_days: '0',
        org: 'other'
      })
    ).toEqual({ title: 'Call', account: 'a', reminder_days: 0, custom_fields: {} });
  });
  it('validates required multiple selections and rejects whitespace', () => {
    const fields = [
      field('name', { required: true }),
      field('contacts', { required: true, multiple: true })
    ];
    expect(missingCreationFields(fields, { name: ' ', contacts: [] })).toHaveLength(2);
  });
  it('parses custom lists, preserves company pages and rejects invalid JSON', () => {
    const fields = [
      field('custom_fields.items', { custom: true, field_type: 'list' }),
      field('pages', { field_type: 'list' })
    ];
    expect(
      creationPayload('Account', fields, {
        'custom_fields.items': '[1,2]',
        pages: [{ name: 'Site', url: 'https://example.test' }]
      })
    ).toEqual({
      custom_fields: { items: [1, 2] },
      pages: '[{"name":"Site","url":"https://example.test"}]'
    });
    expect(() => creationPayload('Account', fields, { 'custom_fields.items': 'oops' })).toThrow();
  });
  it('converts dates and retains the existing ticket closed-date contract', () => {
    const fields = [field('status'), field('due_at', { field_type: 'datetime' })];
    expect(
      creationPayload('Case', fields, { status: 'Closed', due_at: '2026-10-07T16:00Z' })
    ).toMatchObject({
      closed_on: expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/),
      due_at: '2026-10-07T16:00:00.000Z'
    });
  });
});
