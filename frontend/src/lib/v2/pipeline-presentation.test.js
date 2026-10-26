import { expect, it } from 'vitest';
import { pipelinePresentation } from './pipeline-presentation.js';

it('updates labels, order and requirements without replacing records or stage pagination', () => {
  const data = {
    stages: [],
    board: [
      {
        value: 'CUSTOM',
        count: 80,
        offset: 25,
        contacts: [{ id: 'a' }],
        moneyTotals: [{ currency: 'EUR', amount: '500' }]
      }
    ]
  };
  const result = pipelinePresentation(
    data,
    { Contact: { stages: [{ key: 'CUSTOM', label: 'Review', required_properties: ['email'] }] } },
    'Contact'
  );
  expect(result.board[0]).toMatchObject({
    ...data.board[0],
    label: 'Review',
    required_properties: ['email']
  });
  expect(result.stages[0].value).toBe('CUSTOM');
  expect(data.board[0]).not.toHaveProperty('label');
});

it('preserves unassigned and fallback columns when no matching presentation exists', () => {
  const data = {
    stages: [{ value: 'LEAD', label: 'Lead' }],
    board: [{ value: 'UNASSIGNED', label: 'No stage', contacts: [] }]
  };
  expect(pipelinePresentation(data, {}, 'Contact')).toEqual(data);
});

it('never retains presentation from a different organization', () => {
  const data = { board: [{ value: 'CUSTOM', contacts: [] }] };
  const first = pipelinePresentation(
    data,
    { Contact: { stages: [{ key: 'CUSTOM', label: 'First organization' }] } },
    'Contact'
  );
  const second = pipelinePresentation(
    data,
    { Contact: { stages: [{ key: 'CUSTOM', label: 'Second organization' }] } },
    'Contact'
  );
  expect(first.board[0].label).toBe('First organization');
  expect(second.board[0].label).toBe('Second organization');
  expect(data.board[0]).not.toHaveProperty('label');
});
