import { describe, expect, it } from 'vitest';
import { attentionPreview, agendaPreview } from './today-dashboard.js';

const day = {
  counts: { tasks: 15, tickets: 4, deals: 2, reminders: 1, overdue: 17, tasks_today: 1 },
  tasks: [
    {
      id: 'T1',
      name: 'Late task',
      due: '2026-10-28',
      priority: 'Low',
      overdue: true,
      can_complete: false
    }
  ],
  tasks_today: [{ id: 'T2', name: 'Today task', due: '2026-10-29', can_complete: true }],
  reminders: [{ id: 'T3', name: 'Prepare', due: '2026-10-30' }],
  tickets: [
    { id: 'K1', name: 'Urgent ticket', due: '2026-10-28', priority: 'Urgent', overdue: true }
  ],
  deals: [{ id: 'D1', name: 'Oldest deal', due: '2026-10-27', overdue: true }]
};

describe('Today attention preview', () => {
  it('orders by due date then priority, and retains accurate server totals', () => {
    const result = attentionPreview(day);
    expect(result.rows.map((row) => row.id)).toEqual(['D1', 'K1', 'T1', 'T3']);
    expect(result.total).toBe(22);
    expect(result.rows[2].can_complete).toBe(false);
    expect(result.rows[0].href).toBe('/pipeline/D1');
  });
  it('keeps today tasks accessible behind a larger overdue backlog', () => {
    expect(attentionPreview(day, 'today').rows.map((row) => row.id)).toEqual(['T2']);
    expect(attentionPreview(day, 'overdue').rows.map((row) => row.id)).toEqual(['D1', 'K1', 'T1']);
  });
  it('preserves future task reminders in follow-ups and tasks without duplicates', () => {
    expect(attentionPreview(day, 'followups').rows.map((row) => row.id)).toEqual(['D1', 'T3']);
    expect(attentionPreview(day, 'tasks').total).toBe(16);
    expect(attentionPreview(day, 'tasks').rows[1].reminder).toBe(true);
    expect(attentionPreview(day, 'tickets').rows.map((row) => row.id)).toEqual(['K1']);
    expect(attentionPreview(day, 'deals').total).toBe(2);
  });
  it('caps the visible list without changing source data or totals', () => {
    expect(attentionPreview(day, 'all', 2).rows).toHaveLength(2);
    expect(day.tasks[0]).not.toHaveProperty('kind');
    expect(
      attentionPreview({ counts: { tasks: 0, tickets: 0, deals: 0, reminders: 0 } }).rows
    ).toEqual([]);
  });
});

it('highlights ongoing/next meetings and retains completed meetings when the day is finished', () => {
  const events = [
    { id: 'later', start: '2026-10-29T15:00:00Z', end: '2026-10-29T16:00:00Z' },
    { id: 'ongoing', start: '2026-10-29T13:00:00Z', end: '2026-10-29T14:00:00Z' },
    { id: 'past', start: '2026-10-29T11:00:00Z', end: '2026-10-29T12:00:00Z' }
  ];
  expect(
    agendaPreview(events, Date.parse('2026-10-29T13:30:00Z')).rows.map((row) => row.id)
  ).toEqual(['ongoing', 'later']);
  expect(agendaPreview(events, Date.parse('2026-10-29T13:30:00Z')).nextId).toBe('ongoing');
  expect(agendaPreview(events, Date.parse('2026-10-29T16:00:00Z')).nextId).toBeNull();
  expect(agendaPreview([], Date.now()).rows).toEqual([]);
});
