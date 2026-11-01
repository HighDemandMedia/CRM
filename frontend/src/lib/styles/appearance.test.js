import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import { describe, expect, it } from 'vitest';

const template = readFileSync(new URL('../../app.html', import.meta.url), 'utf8');
const initialAppearance = template.match(
  /<script nonce="%sveltekit.nonce%">([\s\S]*?)<\/script>/
)[1];

function renderAppearance(preference, systemDark = false, storageBlocked = false) {
  let storedPreference = preference;
  const classes = new Set();
  const root = {
    style: {},
    classList: {
      toggle(name, enabled) {
        if (enabled) classes.add(name);
        else classes.delete(name);
      }
    }
  };
  runInNewContext(initialAppearance, {
    document: { documentElement: root },
    matchMedia: () => ({ matches: systemDark }),
    localStorage: {
      getItem() {
        if (storageBlocked) throw new Error('Storage unavailable');
        return preference;
      },
      setItem(key, value) {
        storedPreference = value;
      }
    }
  });
  return { dark: classes.has('dark'), scheme: root.style.colorScheme, storedPreference };
}

describe('appearance before hydration', () => {
  it('keeps new visits light even when the device uses dark mode', () => {
    expect(renderAppearance(null, true)).toMatchObject({
      dark: false,
      scheme: 'light',
      storedPreference: 'light'
    });
  });
  it('restores explicit dark and light choices independently of the device', () => {
    expect(renderAppearance('dark', false)).toMatchObject({
      dark: true,
      scheme: 'dark',
      storedPreference: 'dark'
    });
    expect(renderAppearance('light', true)).toMatchObject({
      dark: false,
      scheme: 'light',
      storedPreference: 'light'
    });
  });
  it('migrates system preferences to explicit light before hydration', () => {
    for (const systemDark of [true, false]) {
      expect(renderAppearance('system', systemDark)).toMatchObject({
        dark: false,
        scheme: 'light',
        storedPreference: 'light'
      });
    }
  });
  it('falls back to light for an invalid preference', () => {
    expect(renderAppearance('invalid', true).dark).toBe(false);
  });
  it('does not block the page when storage is unavailable', () => {
    expect(renderAppearance(null, false, true).dark).toBe(false);
  });
});
