import { describe, it, expect } from 'vitest';
import { readTicketForm } from './ticket-form.js';
function form(extra = {}) {
  const form = new FormData();
  for (const [key, value] of Object.entries({
    name: 'Help',
    description: 'Cannot open file',
    priority: 'Normal',
    assigned_to: 'user',
    status: 'New',
    ...extra
  }))
    form.set(key, value);
  return form;
}
describe('ticket form requirements', () => {
  it('allows records without associations', () => expect(readTicketForm(form()).error).toBeNull());
  it('accepts either association', () => {
    expect(readTicketForm(form({ account: 'company' })).error).toBeNull();
    expect(readTicketForm(form({ contacts: 'contact' })).error).toBeNull();
  });
  it('preserves company, deal and multiple contacts in the same submitted form', () => {
    const submitted = form({ account: 'company-a', deal: 'deal-a' });
    submitted.append('contacts', 'contact-a');
    submitted.append('contacts', 'contact-b');
    expect(readTicketForm(submitted).values).toMatchObject({
      assigned_to: 'user',
      account: 'company-a',
      deal: 'deal-a',
      contacts: ['contact-a', 'contact-b']
    });
  });
  it('submits empty associations when all selected records are removed', () => {
    expect(readTicketForm(form({ account: '', deal: '' })).values).toMatchObject({
      account: '',
      deal: '',
      contacts: []
    });
  });
  it('allows an empty user and description', () => {
    expect(readTicketForm(form({ account: 'company', assigned_to: '' })).error).toBeNull();
    expect(readTicketForm(form({ account: 'company', description: ' ' })).error).toBeNull();
  });
});
