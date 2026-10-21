import { expect, it } from 'vitest';
import { activityParts, activityText } from './activity-presentation.js';

it('keeps all change lines available behind the event summary', () => {
  expect(activityParts({ body: 'Contact updated\nName: A → B\nPhone: — → 2125550123' })).toEqual({
    summary: 'Contact updated',
    details: 'Name: A → B\nPhone: — → 2125550123'
  });
  expect(activityParts({ body: 'Record created' }).details).toBe('');
});

it('formats explicit timestamps without treating numbers and ordinary text as dates', () => {
  expect(
    activityText(
      'Appointment: 2026-10-15T13:30:00+00:00 → 2026-10-16T12:30:00Z',
      () => 'Oct 15, 9:30 AM'
    )
  ).toBe('Appointment: Oct 15, 9:30 AM → Oct 15, 9:30 AM');
  expect(activityText('Call 2125550123; reference 2026-10-15; <b>note</b>', () => 'wrong')).toBe(
    'Call 2125550123; reference 2026-10-15; <b>note</b>'
  );
});

it('replaces a legacy model name while retaining the complete reference', () => {
  expect(activityText('SalesAppointment object (4451022c-2c64)', String, () => 'Cita')).toBe(
    'Cita · 4451022c-2c64'
  );
});
