import { describe, it, expect, vi, beforeEach } from 'vitest';
const updateTask = vi.fn();
vi.mock('$lib/server/v2/tasks.js', () => ({
  updateTask: (...args) => updateTask(...args),
  getTask: vi.fn(),
  getTaskFormOptions: vi.fn()
}));
const { saveTaskEditor } = await import('./task-editor.js');
function event(extra = {}) {
  const fields = new FormData();
  for (const [key, value] of Object.entries({
    title: 'Follow up',
    status: 'New',
    priority: 'Medium',
    parent_kind_original: 'account',
    parent_id_original: 'company-a',
    parent_kind: 'account',
    parent_account: 'company-a',
    ...extra
  }))
    fields.set(key, value);
  fields.append('assigned_to', 'user-a');
  fields.append('assigned_to', 'user-b');
  return { params: { id: 'task-a' }, request: { formData: async () => fields } };
}
describe('inline task editing', () => {
  beforeEach(() => {
    updateTask.mockReset();
  });
  it('saves without redirecting and preserves multiple assignees', async () => {
    const result = await saveTaskEditor(event());
    expect(result).toEqual({ saved: true });
    const payload = updateTask.mock.calls[0][2];
    expect(payload.assigned_to).toEqual(['user-a', 'user-b']);
    expect(payload).not.toHaveProperty('account');
  });
  it('changes parent in a single update', async () => {
    await saveTaskEditor(event({ parent_kind: 'case', parent_case: 'ticket-a' }));
    expect(updateTask.mock.calls[0][2]).toMatchObject({ account: null, case: 'ticket-a' });
  });
  it('clears a removed association', async () => {
    await saveTaskEditor(event({ parent_kind: '' }));
    expect(updateTask.mock.calls[0][2]).toMatchObject({ account: null });
  });
  it('returns validation failures with the submitted values', async () => {
    updateTask.mockRejectedValue(new Error('Rejected'));
    const result = await saveTaskEditor(event());
    if (!('status' in result)) throw new Error('Expected a failed save');
    expect(result.status).toBe(400);
    expect(result.data.values).toMatchObject({ title: 'Follow up' });
    expect(result.data.error).toBeTruthy();
  });
});
