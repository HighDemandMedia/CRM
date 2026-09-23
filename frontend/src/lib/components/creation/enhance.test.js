import { beforeEach, describe, expect, it, vi } from 'vitest';
const mocks = vi.hoisted(() => ({ context: undefined, enhance: vi.fn() }));
vi.mock('svelte', () => ({ getContext: () => mocks.context }));
vi.mock('$app/forms', () => ({ enhance: mocks.enhance }));
import { creationEnhance } from './enhance.js';

beforeEach(() => {
  mocks.context = undefined;
  mocks.enhance.mockReset();
});
const panel = () => ({
  url: 'http://localhost/contacts/new?account=123',
  busy: () => false,
  setBusy: vi.fn(),
  result: vi.fn()
});
const node = () => /** @type {HTMLFormElement} */ (/** @type {unknown} */ ({ action: '', getAttribute: () => '?/create' }));
async function setup(submit) {
  mocks.context = panel();
  const form = node();
  creationEnhance()(form, submit);
  const input = { cancel: vi.fn() };
  const complete = await mocks.enhance.mock.calls[0][1](input);
  return { form, input, complete, context: mocks.context };
}
describe('creation panel form submission', () => {
  it('keeps ordinary edit and full-page forms on the default enhancer', () => {
    expect(creationEnhance()).toBe(mocks.enhance);
  });
  it('posts to the new-record route, not the list behind it', async () => {
    const { form } = await setup();
    expect(form.action).toBe('http://localhost/contacts/new?/create');
  });
  it('handles redirect locally instead of navigating away from filters', async () => {
    const { complete, context } = await setup();
    const result = { type: 'redirect', location: '/contacts/new-id' };
    const update = vi.fn();
    await complete({ result, update });
    expect(context.result).toHaveBeenCalledWith(result);
    expect(update).not.toHaveBeenCalled();
    expect(context.setBusy).toHaveBeenLastCalledWith(false);
  });
  it('passes validation failures into the panel while retaining form callbacks', async () => {
    const callback = vi.fn(async ({ update }) => update({ reset: false }));
    const { complete, context } = await setup(() => callback);
    const result = { type: 'failure', status: 400, data: { error: 'Phone required' } };
    await complete({ result, update: vi.fn() });
    expect(callback).toHaveBeenCalled();
    expect(context.result).toHaveBeenCalledWith(result);
  });
  it('respects association validation before posting', async () => {
    const { complete, input, context } = await setup(({ cancel }) => cancel());
    expect(input.cancel).toHaveBeenCalled();
    expect(complete).toBeUndefined();
    expect(context.setBusy).not.toHaveBeenCalled();
  });
  it('blocks duplicate submissions while saving', async () => {
    mocks.context = { ...panel(), busy: () => true };
    creationEnhance()(node());
    const cancel = vi.fn();
    await mocks.enhance.mock.calls[0][1]({ cancel });
    expect(cancel).toHaveBeenCalled();
  });
});
