import { expect, it } from 'vitest';
import { startApiTiming, timeRequest } from './navigation-timing.js';

it('isolates concurrent requests and reports only aggregate numbers', async () => {
  const [one, two] = await Promise.all([
    timeRequest(true, async () => {
      const done = startApiTiming();
      await Promise.resolve();
      done();
      return 'one';
    }),
    timeRequest(true, async () => {
      const first = startApiTiming();
      const second = startApiTiming();
      await Promise.resolve();
      first();
      second();
      return 'two';
    })
  ]);
  expect(one.header).toMatch(/api_count;desc="1"/);
  expect(two.header).toMatch(/api_count;desc="2"/);
  expect(one.response).toBe('one');
  expect(two.response).toBe('two');
});

it('has no request state or header when disabled', async () => {
  const result = await timeRequest(false, async () => {
    startApiTiming()();
    return 'ok';
  });
  expect(result).toEqual({ response: 'ok', header: null });
});

it('does not hide failures or leak their state into the next request', async () => {
  await expect(
    timeRequest(true, async () => {
      startApiTiming()();
      throw new Error('denied');
    })
  ).rejects.toThrow('denied');
  const result = await timeRequest(true, async () => 'ok');
  expect(result.header).toContain('api_count;desc="0"');
});
