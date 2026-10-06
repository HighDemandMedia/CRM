import { expect, it } from 'vitest';
import { stageDuration, exactTime } from './contact-time.js';

it('hides unknown stage age without inventing a date', () => {
  expect(stageDuration(null, Date.now())).toBe('');
  expect(stageDuration('invalid', Date.now())).toBe('');
  expect(exactTime(null)).toBe('Not recorded');
});
it('hides day zero and shows only completed days', () => {
  const start = '2026-09-09T12:00:00Z';
  const now = Date.parse(start);
  expect(stageDuration(start, now)).toBe('');
  expect(stageDuration(start, now + 86400000 - 1)).toBe('');
  expect(stageDuration(start, now + 86400000)).toBe('1 day');
  expect(stageDuration(start, now + 2 * 86400000)).toBe('2 days');
  expect(stageDuration(start, now - 1000)).toBe('');
});

it('uses the account locale for stage age and missing timestamps', () => {
  const start = '2026-09-09T12:00:00Z';
  expect(stageDuration(start, Date.parse(start) + 86400000, 'es-US')).toBe('1 día');
  expect(stageDuration(start, Date.parse(start) + 2 * 86400000, 'es-US')).toBe('2 días');
  expect(exactTime(null, 'es-US')).toBe('Sin registrar');
});
