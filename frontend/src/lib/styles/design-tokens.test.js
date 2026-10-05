import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';

const css = readFileSync(new URL('./design-tokens.css', import.meta.url), 'utf8');
const declarations = (selector) =>
  Object.fromEntries(
    [...css.match(selector)[1].matchAll(/(--crm-[\w-]+):\s*([^;]+);/g)].map((m) => [m[1], m[2]])
  );
const light = declarations(/:root\s*\{([^}]+)\}/);
const dark = { ...light, ...declarations(/\.dark\s*\{([^}]+)\}/) };
function color(tokens, name) {
  const value = tokens[`--crm-${name}`];
  const alias = value.match(/^var\(--crm-(.+)\)$/);
  return alias ? color(tokens, alias[1]) : value;
}
function luminance(hex) {
  const rgb = hex.match(/[a-f\d]{2}/gi).map((v) => parseInt(v, 16) / 255);
  const linear = rgb.map((v) => (v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  return linear[0] * 0.2126 + linear[1] * 0.7152 + linear[2] * 0.0722;
}
function contrast(a, b) {
  const [high, low] = [luminance(a), luminance(b)].sort((a, b) => b - a);
  return (high + 0.05) / (low + 0.05);
}
// Regression guard for reusable text/background contracts, not a substitute for page QA.
for (const [theme, tokens] of Object.entries({ light, dark })) {
  describe(`${theme} visual contrast`, () => {
    for (const foreground of ['text', 'text-muted', 'link']) {
      for (const background of ['canvas', 'surface', 'surface-secondary', 'surface-selected']) {
        it(`${foreground} on ${background} meets AA for normal text`, () => {
          expect(
            contrast(color(tokens, foreground), color(tokens, background))
          ).toBeGreaterThanOrEqual(4.5);
        });
      }
    }
    for (const state of ['primary', 'primary-hover', 'primary-active']) {
      it(`primary text on ${state} meets AA`, () => {
        expect(
          contrast(color(tokens, 'primary-text'), color(tokens, state))
        ).toBeGreaterThanOrEqual(4.5);
      });
    }
    it('white text meets AA along the branded gradient in every interaction state', () => {
      const endpoints = ['brand-red', 'brand-orange'].map((name) =>
        color(tokens, name)
          .match(/[a-f\d]{2}/gi)
          .map((v) => parseInt(v, 16))
      );
      for (const state of ['action-bg', 'action-hover-bg', 'action-active-bg']) {
        const overlay = Number(tokens[`--crm-${state}`].match(/\/ (\d+)%/)[1]) / 100;
        for (let step = 0; step <= 100; step++) {
          const rgb = endpoints[0].map((start, index) =>
            Math.round((start + ((endpoints[1][index] - start) * step) / 100) * (1 - overlay))
          );
          const background = '#' + rgb.map((v) => v.toString(16).padStart(2, '0')).join('');
          expect(contrast(color(tokens, 'primary-text'), background)).toBeGreaterThanOrEqual(4.5);
        }
      }
    });
    for (const semantic of ['success', 'warning', 'danger', 'info', 'calendar-external']) {
      it(`${semantic} status meets AA`, () => {
        expect(
          contrast(color(tokens, semantic), color(tokens, `${semantic}-bg`))
        ).toBeGreaterThanOrEqual(4.5);
      });
    }
    for (const boundary of ['control-border', 'focus']) {
      for (const surface of ['surface', 'canvas', 'surface-secondary']) {
        it(`${boundary} against ${surface} meets non-text AA`, () => {
          expect(contrast(color(tokens, boundary), color(tokens, surface))).toBeGreaterThanOrEqual(
            3
          );
        });
      }
    }
    for (const foreground of ['nav-text', 'nav-muted']) {
      it(`${foreground} on navigation meets AA`, () => {
        expect(contrast(color(tokens, foreground), color(tokens, 'nav-bg'))).toBeGreaterThanOrEqual(
          4.5
        );
      });
    }
  });
}
