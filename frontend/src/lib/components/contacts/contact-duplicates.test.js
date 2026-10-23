import { describe, expect, it } from 'vitest';
import { contactDuplicateNoticeIndex, contactDuplicateQuery } from './contact-duplicates.js';

describe('contact duplicate identity', () => {
  const identity = {
    name: 'Ana Maria Lopez',
    email: 'ana+sales@example.com',
    phone: '3055550199'
  };

  it('preserves acknowledgement through formatting-only edits', () => {
    expect(
      contactDuplicateQuery({
        name: '  ANA   Maria\tLopez  ',
        email: ' ANA+Sales@Example.COM ',
        phone: '(305) 555-0199'
      })
    ).toBe(contactDuplicateQuery(identity));
  });

  it.each([
    ['name', 'Ana Maria Perez'],
    ['email', 'ana+support@example.com'],
    ['phone', '3055550100'],
    ['exclude', 'other-contact']
  ])('requires another review when %s changes', (key, value) => {
    expect(contactDuplicateQuery({ ...identity, [key]: value })).not.toBe(
      contactDuplicateQuery(identity)
    );
  });

  it('preserves email plus addressing and excludes only the edited record', () => {
    const query = new URLSearchParams(contactDuplicateQuery({ ...identity, exclude: 'contact-a' }));
    expect(query.get('email')).toBe('ana+sales@example.com');
    expect(query.get('exclude')).toBe('contact-a');
    expect(new URLSearchParams(contactDuplicateQuery(identity)).has('exclude')).toBe(false);
    expect(contactDuplicateQuery({ ...identity, exclude: 'contact-b' })).not.toBe(query.toString());
  });

  it.each([
    {},
    { name: '  ', email: ' ', phone: '  ' },
    { name: 'Al', email: 'not-an-email', phone: '123-456' },
    { exclude: 'contact-a' }
  ])('does not start a lookup without sufficient identifying data: %j', (values) => {
    expect(contactDuplicateQuery(values)).toBe('');
  });

  it.each([{ name: 'Ana' }, { email: 'a@example.com' }, { phone: '555-0199' }])(
    'allows any supported identifying field to trigger a lookup: %j',
    (values) => {
      expect(contactDuplicateQuery(values)).not.toBe('');
    }
  );
});

describe('contact duplicate warning placement', () => {
  const field = (key, section) => ({ key, section });
  const name = field('first_name', 'Identity');
  const email = field('email', 'Identity');
  const owner = field('assigned_to', 'Ownership');
  const company = field('account', 'Associations');
  const notes = field('description', 'Additional details');

  it('appears immediately before the first Ownership section', () => {
    const fields = [name, email, owner, company, notes];
    expect(contactDuplicateNoticeIndex(fields)).toBe(2);
  });

  it.each([
    ['self-assigned member', [name, email, owner, company, notes].filter((f) => f !== owner)],
    ['owner omitted in configuration', [name, email, notes]]
  ])('falls back after identifying fields for %s', (_case, fields) => {
    expect(contactDuplicateNoticeIndex(fields)).toBe(2);
  });

  it('honors reordered fields without moving them', () => {
    const fields = Object.freeze([notes, name, company, owner, email]);
    expect(contactDuplicateNoticeIndex(fields)).toBe(3);
    expect(fields).toEqual([notes, name, company, owner, email]);
    expect(contactDuplicateNoticeIndex([owner, name, email])).toBe(0);
  });

  it('uses the last identifying field when reordered fields have no Ownership section', () => {
    expect(contactDuplicateNoticeIndex([name, company, email, notes])).toBe(3);
  });

  it('supports identity-only, empty and identity-free visible fields', () => {
    expect(contactDuplicateNoticeIndex([name, email])).toBe(2);
    expect(contactDuplicateNoticeIndex([name])).toBe(1);
    expect(contactDuplicateNoticeIndex([])).toBe(0);
    expect(contactDuplicateNoticeIndex([company, notes])).toBe(0);
  });
});
