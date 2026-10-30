import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest';
import { toast } from 'svelte-sonner';
import { announceNotifications, resetPendingAlerts } from './notification-alerts.js';
vi.mock('svelte-sonner', () => ({ toast: vi.fn() }));
const now = Date.parse('2026-10-30T01:00:00Z');
let storage,
  desktop,
  profile,
  sequence = 0;
const ui = (text) => text;
const row = (changes = {}) => ({
  id: 'receipt',
  verb: 'task.reminder',
  created_at: new Date(now).toISOString(),
  entity_name: 'Private task',
  link: '/tasks/TSK-abc',
  channels: { popup: true, browser: true, bell: false },
  ...changes
});

beforeEach(() => {
  vi.mocked(toast).mockReset();
  resetPendingAlerts();
  profile = `profile-${++sequence}`;
  storage = new Map();
  desktop = [];
  class FakeNotification {
    static permission = 'granted';
    static requestPermission = vi.fn();
    constructor(title, options) {
      this.title = title;
      this.options = options;
      this.close = vi.fn();
      desktop.push(this);
    }
  }
  vi.stubGlobal('Notification', FakeNotification);
  vi.stubGlobal('window', {
    isSecureContext: true,
    Notification: FakeNotification,
    focus: vi.fn(),
    location: { assign: vi.fn() }
  });
  vi.stubGlobal('document', { visibilityState: 'visible' });
  vi.stubGlobal('navigator', { locks: { request: vi.fn(async (_, run) => run()) } });
  vi.stubGlobal('localStorage', {
    getItem: (key) => storage.get(key),
    setItem: (key, value) => storage.set(key, value)
  });
});
afterEach(() => vi.unstubAllGlobals());
const announce = (rows) => announceNotifications(rows, profile, ui, 'en-US', now);

describe('independent notification channels', () => {
  it('delivers popup and desktop once without Bell and never asks permission automatically', async () => {
    await announce([row()]);
    await announce([row()]);
    expect(toast).toHaveBeenCalledTimes(1);
    expect(desktop).toHaveLength(1);
    expect(desktop[0].options.body).toBe('Task reminder');
    expect(Notification.requestPermission).not.toHaveBeenCalled();
    expect(JSON.stringify([...storage.values()])).not.toContain('Private task');
    desktop[0].onclick();
    expect(window.location.assign).toHaveBeenCalledWith('/tasks/TSK-abc');
  });
  it('honors disabled channels', async () => {
    await announce([row({ channels: { popup: false, browser: false, bell: true } })]);
    expect(toast).not.toHaveBeenCalled();
    expect(desktop).toHaveLength(0);
  });
  it('honors denied browser permission without suppressing popup', async () => {
    Object.defineProperty(Notification, 'permission', { value: 'denied', configurable: true });
    await announce([row()]);
    expect(toast).toHaveBeenCalledTimes(1);
    expect(desktop).toHaveLength(0);
  });
  it('holds popup for visible tab but can deliver desktop in background', async () => {
    vi.stubGlobal('document', { visibilityState: 'hidden' });
    await announce([row()]);
    expect(toast).not.toHaveBeenCalled();
    expect(desktop).toHaveLength(1);
    vi.stubGlobal('document', { visibilityState: 'visible' });
    await announce([]);
    expect(toast).toHaveBeenCalledTimes(1);
    expect(desktop).toHaveLength(1);
  });
  it('drops queued alerts on profile change or preferences update', async () => {
    vi.stubGlobal('document', { visibilityState: 'hidden' });
    await announce([row()]);
    resetPendingAlerts();
    vi.stubGlobal('document', { visibilityState: 'visible' });
    await announce([]);
    expect(toast).not.toHaveBeenCalled();
    vi.stubGlobal('document', { visibilityState: 'hidden' });
    await announce([row({ id: 'second' })]);
    profile = 'another-profile';
    vi.stubGlobal('document', { visibilityState: 'visible' });
    await announce([]);
    expect(toast).not.toHaveBeenCalled();
  });
  it('skips read, stale and ended events', async () => {
    await announce([
      row({ read_at: new Date(now).toISOString() }),
      row({ id: 'old', created_at: new Date(now - 3600000).toISOString() }),
      row({
        id: 'past',
        verb: 'calendar.reminder',
        data: { starts_at: new Date(now - 1000).toISOString() }
      })
    ]);
    expect(toast).not.toHaveBeenCalled();
    expect(desktop).toHaveLength(0);
  });
  it('honors preferences changed elsewhere before delivering a queued popup', async () => {
    vi.stubGlobal('document', { visibilityState: 'hidden' });
    await announce([row()]);
    vi.stubGlobal('document', { visibilityState: 'visible' });
    await announceNotifications([], profile, ui, 'en-US', now, {
      'task.reminder': { popup: false, browser: false }
    });
    expect(toast).not.toHaveBeenCalled();
    expect(desktop).toHaveLength(1);
  });
  it('never opens an external notification link', async () => {
    await announce([row({ link: 'https://evil.test' })]);
    desktop[0].onclick();
    expect(window.location.assign).toHaveBeenCalledWith('/notifications');
  });
  it('keeps working if local storage is blocked', async () => {
    localStorage.getItem = () => {
      throw new Error('blocked');
    };
    localStorage.setItem = localStorage.getItem;
    await announce([row()]);
    await announce([row()]);
    expect(toast).toHaveBeenCalledTimes(1);
  });
});
