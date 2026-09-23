import { describe, it, expect, vi, beforeEach } from 'vitest';
const apiRequest = vi.fn();
vi.mock('$lib/api-helpers.js', () => ({ apiRequest: (...args) => apiRequest(...args) }));
const { updateTask } = await import('./tasks.js');
const event = /** @type {any} */ ({ cookies: {} });
describe('task pipeline moves', () => {
  beforeEach(() => { apiRequest.mockReset(); });
  it.each(['New', 'In Progress', 'Completed'])('updates only status for %s', async (status) => {
    apiRequest.mockResolvedValue({});
    await updateTask(event, 'task-id', { status });
    expect(apiRequest).toHaveBeenCalledWith(
      '/tasks/task-id/',
      { method: 'PATCH', body: { status } },
      { cookies: event.cookies }
    );
  });
  it('propagates a rejected move so the UI can report failure', async () => {
    apiRequest.mockRejectedValue(new Error('Forbidden'));
    await expect(updateTask(event, 'task-id', { status: 'Completed' })).rejects.toThrow(
      'Forbidden'
    );
  });
});
