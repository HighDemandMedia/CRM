import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
const mocks = vi.hoisted(() => ({ enhance: vi.fn() }));
vi.mock('$app/forms', () => ({ enhance: mocks.enhance }));
import { authForm } from './auth-form.js';

beforeEach(() => {
  vi.useFakeTimers();
  mocks.enhance.mockReset().mockReturnValue({ destroy: vi.fn() });
});
afterEach(() => vi.useRealTimers());

function setup() {
  const setBusy = vi.fn();
  const setError = vi.fn();
  const action = authForm({}, { setBusy, setError });
  const submit = mocks.enhance.mock.calls[0][1];
  const controller = new AbortController();
  const complete = submit({ controller, cancel: vi.fn() });
  return { setBusy, setError, action, submit, controller, complete };
}

describe('authentication form recovery', () => {
  it('keeps an interrupted JSON response on the form instead of opening the 500 page', async () => {
    const { complete, setBusy, setError } = setup();
    const update = vi.fn();
    await complete({
      result: { type: 'error', error: new SyntaxError('Unexpected end of JSON input') },
      update
    });
    expect(update).not.toHaveBeenCalled();
    expect(setError).toHaveBeenLastCalledWith(expect.stringContaining('Please try again'));
    expect(setBusy).toHaveBeenLastCalledWith(false);
    expect(vi.getTimerCount()).toBe(0);
  });
  it.each(['failure', 'success', 'redirect'])(
    'preserves normal %s handling without resetting fields',
    async (type) => {
      const { complete, setBusy, setError } = setup();
      const update = vi.fn();
      await complete({ result: { type }, update });
      expect(update).toHaveBeenCalledWith({ reset: false });
      expect(setBusy).toHaveBeenLastCalledWith(false);
      expect(setError).toHaveBeenLastCalledWith('');
    }
  );
  it('aborts a stalled request, permits retry, and ignores a late response', async () => {
    const { controller, complete, submit, setBusy, setError } = setup();
    vi.advanceTimersByTime(30000);
    expect(controller.signal.aborted).toBe(true);
    expect(setBusy).toHaveBeenLastCalledWith(false);
    expect(setError).toHaveBeenLastCalledWith(expect.stringContaining('too long'));
    const cancel = vi.fn();
    submit({ controller: new AbortController(), cancel });
    expect(cancel).not.toHaveBeenCalled();
    const update = vi.fn();
    await complete({ result: { type: 'redirect' }, update });
    expect(update).not.toHaveBeenCalled();
    expect(setBusy).toHaveBeenLastCalledWith(true);
  });
  it('blocks double submissions and cleans up when leaving the page', () => {
    const { submit, action, controller } = setup();
    const cancel = vi.fn();
    submit({ controller: new AbortController(), cancel });
    expect(cancel).toHaveBeenCalledOnce();
    action.destroy();
    expect(controller.signal.aborted).toBe(true);
    expect(vi.getTimerCount()).toBe(0);
  });
});
