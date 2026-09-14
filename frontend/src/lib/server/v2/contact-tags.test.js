import { expect, it, vi } from 'vitest';
vi.mock('$lib/api-helpers.js', () => ({ apiRequest: vi.fn() }));
import { readContactTags } from './contact-tags.js';
it('preserves tags when the picker is absent or selection is unchanged', () => {
  const values = {};
  const form = new FormData();
  readContactTags(form, values);
  expect(values).toEqual({});
  form.set('tags_present', '1');
  form.set('tags_original', '["a","b"]');
  form.append('tags', 'b');
  form.append('tags', 'a');
  readContactTags(form, values);
  expect(values).toEqual({});
});
it('sends an empty list when all tags are removed', () => {
  const values = {};
  const form = new FormData();
  form.set('tags_present', '1');
  form.set('tags_original', '["a"]');
  readContactTags(form, values);
  expect(values).toEqual({ tags: [] });
});
