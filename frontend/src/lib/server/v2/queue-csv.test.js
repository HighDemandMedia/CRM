import { it, expect, vi, beforeEach } from 'vitest';
vi.mock('$lib/api-helpers.js', () => ({ apiRequest: vi.fn() }));
vi.mock('./tasks.js', () => ({
  listTasks: vi.fn(),
  FILTER_FIELDS: ['status', 'priority', 'assigned_to']
}));
vi.mock('./tickets.js', () => ({
  listTickets: vi.fn(),
  FILTER_FIELDS: ['priority', 'assigned_to'],
  OPEN_STATUSES: ['New', 'Assigned', 'Pending']
}));
import { apiRequest } from '$lib/api-helpers.js';
import { listTasks } from './tasks.js';
import { listTickets } from './tickets.js';
import { exportQueue } from './queue-csv.js';
beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(apiRequest).mockResolvedValue({
    property_layout: {
      Task: { system: [{ key: 'title', label: 'Title' }] },
      Case: { system: [{ key: 'name', label: 'Name' }] }
    },
    pipelines: {
      Case: {
        stages: [
          { key: 'custom', label: 'Custom' },
          { key: 'Resolved', label: 'Resolved' }
        ]
      }
    }
  });
});
it('uses configured ticket stages for the same filtered view', async () => {
  vi.mocked(listTickets).mockResolvedValueOnce({
    results: [{ id: 'a', name: 'Ticket' }],
    totals: { count: 1, open: 1, urgent: 0, awaiting_reply: 0, shown: 1 }
  });
  const csv = await exportQueue(
    {
      url: new URL('http://localhost/tickets/export?all=0&search=Ticket&columns=name'),
      cookies: {}
    },
    'Case'
  );
  expect(csv).toContain('"Ticket"');
  const q = vi.mocked(listTickets).mock.calls[0][1];
  expect(q.getAll('status')).toEqual(['custom']);
  expect(q.get('search')).toBe('Ticket');
  expect(q.get('permission_action')).toBe('export');
});
it('all task exports ignore search and open-only filters', async () => {
  vi.mocked(listTasks).mockResolvedValueOnce({
    owners: [],
    results: [{ id: 'a', title: 'Finished', is_done: true }],
    totals: {
      count: 1,
      open: 0,
      overdue: 0,
      due_today: 0,
      due_this_week: 0,
      no_due_date: 1,
      unassigned: 1,
      shown: 1,
      matched: 1
    }
  });
  const csv = await exportQueue(
    {
      url: new URL('http://localhost/tasks/export?all=0&q=test&scope=all&columns=title'),
      cookies: {}
    },
    'Task'
  );
  expect(csv).toContain('Finished');
  expect(vi.mocked(listTasks).mock.calls[0][1].get('search')).toBeNull();
});
it('filtered task exports retain the open-only view across all pages', async () => {
  vi.mocked(listTasks).mockResolvedValueOnce({
    owners: [],
    results: [
      { title: 'Finished', is_done: true },
      { title: 'Open', is_done: false }
    ],
    totals: {
      count: 2,
      open: 1,
      overdue: 0,
      due_today: 0,
      due_this_week: 0,
      no_due_date: 2,
      unassigned: 2,
      shown: 2,
      matched: 2
    }
  });
  const csv = await exportQueue(
    { url: new URL('http://localhost/tasks/export?all=0&columns=title'), cookies: {} },
    'Task'
  );
  expect(csv).not.toContain('Finished');
  expect(csv).toContain('Open');
});
