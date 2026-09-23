import { describe, it, expect } from 'vitest';
import { userName } from './user-name.js';
describe('User names across owner lookup payloads', () => {
  it.each([
    {user_details:{name:'Alex Rivera',email:'test@example.com'}},
    {user:{name:'Alex Rivera',email:'test@example.com'}},
    {user__name:'Alex Rivera',user__email:'test@example.com'},
    {name:'Alex Rivera',email:'test@example.com'}
  ])('prefers the saved name', profile => expect(userName(profile)).toBe('Alex Rivera'));
  it('keeps legacy nameless users identifiable', () => expect(userName({user__email:'old@example.com'})).toBe('old@example.com'));
});
