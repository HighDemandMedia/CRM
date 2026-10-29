import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { watchRecordMail } from './watch-record-mail.js';
/** @type {EventTarget & {hidden:boolean}} */
let documentMock;
let fetchMock;
let stop;
beforeEach(() => {
  vi.useFakeTimers();
  documentMock = Object.assign(new EventTarget(), { hidden: false });
  vi.stubGlobal('document', documentMock);
  fetchMock = vi
    .fn()
    .mockResolvedValue({ ok: true, status: 200, json: async () => ({ revision: 'one' }) });
  vi.stubGlobal('fetch', fetchMock);
});
afterEach(() => {
  stop?.();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});
it('checks the cache while visible, pauses hidden, resumes immediately, and cleans up', async () => {
  const onStatus = vi.fn();
  stop = watchRecordMail({ endpoint: '/mail', onStatus, onUnavailable: vi.fn() });
  await vi.advanceTimersByTimeAsync(0);
  expect(onStatus).toHaveBeenCalledWith({ revision: 'one' });
  await vi.advanceTimersByTimeAsync(10000);
  expect(fetch).toHaveBeenCalledTimes(2);
  documentMock.hidden = true;
  documentMock.dispatchEvent(new Event('visibilitychange'));
  await vi.advanceTimersByTimeAsync(60000);
  expect(fetch).toHaveBeenCalledTimes(2);
  documentMock.hidden = false;
  documentMock.dispatchEvent(new Event('visibilitychange'));
  await vi.advanceTimersByTimeAsync(0);
  expect(fetch).toHaveBeenCalledTimes(3);
  stop();
  await vi.advanceTimersByTimeAsync(60000);
  expect(fetch).toHaveBeenCalledTimes(3);
});
it('backs off temporary failures without clearing content', async () => {
  fetchMock.mockResolvedValueOnce({ ok: false, status: 503 });
  const onStatus = vi.fn();
  stop = watchRecordMail({ endpoint: '/mail', onStatus, onUnavailable: vi.fn() });
  await vi.advanceTimersByTimeAsync(10000);
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(onStatus).not.toHaveBeenCalled();
  await vi.advanceTimersByTimeAsync(10000);
  expect(fetch).toHaveBeenCalledTimes(2);
});
it('stops polling and rechecks record access after permission or session loss', async () => {
  fetchMock.mockResolvedValue({ ok: false, status: 403 });
  const onUnavailable = vi.fn();
  stop = watchRecordMail({ endpoint: '/mail', onStatus: vi.fn(), onUnavailable });
  await vi.advanceTimersByTimeAsync(60000);
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(onUnavailable).toHaveBeenCalledOnce();
});
