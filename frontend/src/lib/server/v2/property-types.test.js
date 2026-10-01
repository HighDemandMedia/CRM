import { describe, it, expect } from 'vitest';
import { fieldInputType, fieldInputStep } from '$lib/v2/custom-field-input.js';
describe('new custom property types', () => {
  it('uses suitable inputs and numeric steps', () => {
    expect(fieldInputType('phone')).toBe('tel');
    expect(fieldInputType('email')).toBe('email');
    expect(fieldInputType('money')).toBe('text');
    expect(fieldInputStep('money')).toBe('0.01');
    expect(fieldInputStep('integer')).toBe('1');
  });
});
