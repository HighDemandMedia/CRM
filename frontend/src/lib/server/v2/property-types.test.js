import { describe, it, expect, vi } from 'vitest';
vi.mock('$lib/api-helpers.js', () => ({ apiRequest: vi.fn() }));
import { pairForEdit, displayValue, collectFromForm } from './lead-custom-fields.js';
import { fieldInputType, fieldInputStep } from '$lib/v2/custom-field-input.js';
const definition = {
  key: 'regions',
  label: 'Regions',
  field_type: 'multi_select',
  options: [
    { value: 'n', label: 'North' },
    { value: 's', label: 'South' }
  ]
};
describe('new custom property types', () => {
  it('preserves selection arrays and displays labels', () => {
    expect(pairForEdit([definition], { regions: ['n', 's'] })[0].value).toEqual(['n', 's']);
    expect(displayValue(definition, ['s', 'n'])).toBe('South, North');
  });
  it('submits selected values and allows clearing all selections', () => {
    const form = new FormData();
    form.append('cf_regions', 'n');
    form.append('cf_regions', 's');
    expect(collectFromForm(form, [definition])).toEqual({ regions: ['n', 's'] });
    expect(collectFromForm(new FormData(), [definition])).toEqual({ regions: [] });
  });
  it('uses suitable inputs and numeric steps', () => {
    expect(fieldInputType('phone')).toBe('tel');
    expect(fieldInputType('email')).toBe('email');
    expect(fieldInputType('money')).toBe('text');
    expect(fieldInputStep('money')).toBe('0.01');
    expect(fieldInputStep('integer')).toBe('1');
    expect(displayValue({ field_type: 'percentage' }, 0)).toBe('0%');
  });
});
