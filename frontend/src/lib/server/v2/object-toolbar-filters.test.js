import { describe, expect, it } from 'vitest';
import { companyQuery } from './company-query.js';
import { dealQuery } from './deal-query.js';

// The same builders feed list, pipeline and CSV requests.
describe.each([
  ['companies', companyQuery],
  ['deals', dealQuery]
])('%s toolbar filters', (_name, buildQuery) => {
  it.each(['list', 'pipeline'])('forwards common filters in %s view', (view) => {
    const query = buildQuery(
      new URL(
        `http://localhost/?view=${view}&search=Acme&assigned_to=owner-id&stage=LEAD&tags=tag-id&org=other-org`
      )
    );
    expect(Object.fromEntries(query)).toMatchObject({
      search: 'Acme',
      assigned_to: 'owner-id',
      stage: 'LEAD',
      tags: 'tag-id'
    });
    expect(query.has('view')).toBe(false);
    expect(query.has('org')).toBe(false);
  });
  it('does not send empty owner or tag filters', () => {
    const query = buildQuery(new URL('http://localhost/?assigned_to=&tags='));
    expect(query.has('assigned_to')).toBe(false);
    expect(query.has('tags')).toBe(false);
  });
});
it('retains priority when moved into advanced deal filters', () => {
  expect(dealQuery(new URL('http://localhost/?priority=HIGH')).get('priority')).toBe('HIGH');
});
