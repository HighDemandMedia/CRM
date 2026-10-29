import { afterEach, expect, it, vi } from 'vitest';
import { watchResourceStatus } from './watch-resource-status.js';

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

it('uses the provided status endpoint, prevents overlapping requests and ignores results after navigation', async () => {
  vi.useFakeTimers();
  const documentMock = Object.assign(new EventTarget(), { hidden: false });
  vi.stubGlobal('document', documentMock);
  /** @type {(value:any)=>void} */
  let complete = () => {
    throw new Error('Request not started');
  };
  const fetchMock = vi.fn(
    () =>
      new Promise((resolve) => {
        complete = resolve;
      })
  );
  vi.stubGlobal('fetch', fetchMock);
  const onStatus = vi.fn();
  const stop = watchResourceStatus({
    endpoint: '/calendar/events?view=status',
    onStatus,
    onUnavailable: vi.fn()
  });
  documentMock.dispatchEvent(new Event('visibilitychange'));
  await vi.advanceTimersByTimeAsync(10000);
  expect(fetchMock).toHaveBeenCalledOnce();
  expect(fetchMock).toHaveBeenCalledWith('/calendar/events?view=status', {
    signal: expect.any(AbortSignal)
  });
  stop();
  complete({ ok: true, status: 200, json: async () => ({ revision: 'old-account' }) });
  await vi.advanceTimersByTimeAsync(0);
  expect(onStatus).not.toHaveBeenCalled();
});
