import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { parse } from 'svelte/compiler';

// The shared Button resolves internal hrefs itself. Resolving them again in a
// caller crashes SSR on nested record URLs, where Kit returns relative paths.
describe('error-page recovery link contract', () => {
  it('passes absolute internal paths to Button without resolving twice', () => {
    const ast = parse(readFileSync(new URL('./ErrorPage.svelte', import.meta.url), 'utf8'), {
      modern: true
    });
    const hrefs = [];
    function visit(node) {
      if (!node || typeof node !== 'object') return;
      if (node.type === 'Component' && node.name === 'Button') {
        const href = node.attributes.find((attribute) => attribute.name === 'href');
        if (href) {
          expect(href.value).toHaveLength(1);
          expect(href.value[0].type).toBe('Text');
          hrefs.push(href.value[0].data);
        }
      }
      for (const value of Object.values(node)) {
        if (Array.isArray(value)) value.forEach(visit);
        else if (value && typeof value === 'object') visit(value);
      }
    }
    visit(ast.fragment);
    expect(hrefs).toEqual(['/login', '/']);
  });
});
