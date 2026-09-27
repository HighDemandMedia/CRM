import { describe, it, expect } from 'vitest';
import { articles } from './articles.js';
import { requestTypes } from './request-types.js';
describe('CRM help content', () => {
  it('has unique routable guides with content', () => {
    expect(new Set(articles.map((item) => item.slug)).size).toBe(articles.length);
    for (const article of articles) {
      expect(article.slug).toMatch(/^[a-z0-9-]+$/);
      expect(article.sections.length).toBeGreaterThan(0);
      for (const section of article.sections)
        expect(Boolean(section.text || section.steps?.length)).toBe(true);
    }
  });
  it('keeps request forms specific to their purpose', () => {
    expect(
      requestTypes
        .find((t) => t.key === 'bug')
        .fields.filter((f) => f.required)
        .map((f) => f.key)
    ).toEqual(['actual', 'expected', 'impact']);
    expect(
      requestTypes
        .find((t) => t.key === 'feature')
        .fields.filter((f) => f.required)
        .map((f) => f.key)
    ).toEqual(['problem', 'benefit']);
    expect(
      requestTypes
        .find((t) => t.key === 'help')
        .fields.filter((f) => f.required)
        .map((f) => f.key)
    ).toEqual(['question']);
  });
});
