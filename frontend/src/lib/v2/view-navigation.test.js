import { expect, it, vi } from 'vitest';
import { createViewNavigation } from './view-navigation.js';

it('coalesces focus and pointer hints, preserving the full destination query', async () => {
  const preload = vi.fn().mockResolvedValue({});
  const navigate = vi.fn();
  const controller = createViewNavigation({ preload, navigate, now: () => 10 });
  const href = '/contacts?view=pipeline&search=Example&stage=CUSTOM&CUSTOM_offset=25';
  controller.prepare(href);
  controller.prepare(href);
  await controller.go(href);
  expect(preload).toHaveBeenCalledExactlyOnceWith(href);
  expect(navigate).toHaveBeenCalledWith(href, { keepFocus: true, noScroll: true });
});

it('forces fresh data rather than using a hint that aged while the pointer stayed still', async () => {
  let now = 0;
  const navigate = vi.fn();
  const controller = createViewNavigation({
    preload: vi.fn().mockResolvedValue({}),
    navigate,
    now: () => now
  });
  controller.prepare('/accounts?view=pipeline');
  now = 5001;
  controller.prepare('/accounts?view=pipeline');
  await controller.go('/accounts?view=pipeline');
  expect(navigate).toHaveBeenCalledWith('/accounts?view=pipeline', {
    keepFocus: true,
    noScroll: true,
    invalidateAll: true
  });
});

it('allows navigation after a speculative failure and propagates real errors', async () => {
  const navigate = vi.fn().mockRejectedValue(new Error('offline'));
  const controller = createViewNavigation({
    preload: vi.fn().mockRejectedValue(new Error('offline')),
    navigate
  });
  controller.prepare('/pipeline?view=list');
  await expect(controller.go('/pipeline?view=list')).rejects.toThrow('offline');
});
