import { readFileSync } from 'node:fs';
import { parse } from 'svelte/compiler';
import { expect, it } from 'vitest';

// Native OAuth form submissions need a real Origin for SvelteKit's CSRF check.
// Unlike no-referrer, strict-origin preserves it without leaking token URLs.
it.each(['register', 'invite'])(
  '%s keeps native POST origins while excluding paths and tokens from referrers',
  (route) => {
    const source = readFileSync(
      new URL(`../../routes/(no-layout)/${route}/+page.svelte`, import.meta.url),
      'utf8'
    );
    const ast = parse(source, { modern: true });
    const policies = [];
    function visit(node) {
      if (!node || typeof node !== 'object') return;
      if (node.type === 'RegularElement' && node.name === 'meta') {
        const attribute = (name) =>
          node.attributes.find((item) => item.name === name)?.value?.[0]?.data;
        if (attribute('name') === 'referrer') policies.push(attribute('content'));
      }
      for (const value of Object.values(node)) {
        if (Array.isArray(value)) value.forEach(visit);
        else if (value && typeof value === 'object') visit(value);
      }
    }
    visit(ast.fragment);
    expect(policies).toEqual(['strict-origin']);
  }
);
