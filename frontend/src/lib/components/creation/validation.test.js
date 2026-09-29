import { describe, expect, it } from 'vitest';
import { recordFieldError } from './validation.js';
import { fieldErrors } from '$lib/server/v2/form-errors.js';

describe('record form validation', () => {
  it.each([['city','1234'],['city','<Miami>'],['state','@@@'],['postcode','!!!'],['phone','-------'],['phone','12345'],['phone','1+3055550190']])('rejects malformed %s: %s', (field,value) => {
    expect(recordFieldError(field,value)).not.toBe('');
  });
  it.each([['city','São Paulo'],['city','東京'],['city',"St. John's"],['city','6th of October City'],['state','Île-de-France'],['postcode','SW1A 1AA'],['postcode','00901-1234'],['phone','+1 (305) 555-0190']])('accepts international %s: %s', (field,value) => {
    expect(recordFieldError(field,value)).toBe('');
  });
  it('keeps optional fields empty but requires a meaningful name', () => {
    expect(recordFieldError('city','')).toBe('');
    expect(recordFieldError('name','   ',true)).toBe('This field is required.');
  });
  it('maps API errors to public form names without rendering nested objects', () => {
    expect(fieldErrors({body:{errors:{first_name:['Required'],city:['Invalid city'],stage_requirements:{code:'missing'}}}})).toEqual({name:'Required',city:'Invalid city'});
  });
});
