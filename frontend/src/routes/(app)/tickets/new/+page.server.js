import { readTicketForm } from '$lib/server/v2/ticket-form.js';
import { fail, redirect } from '@sveltejs/kit';
import { createTicket, getTicketFormOptions } from '$lib/server/v2/tickets.js';
import { readableError, stageRequirements } from '$lib/server/v2/form-errors.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ cookies, url }) {
  return await getTicketFormOptions(
    { cookies },
    url.searchParams.get('account'),
    url.searchParams.get('contact')
  );
}

/** @type {import('./$types').Actions} */
export const actions = {
  create: async ({ cookies, request }) => {
    const form = await request.formData();

    const { values, error } = readTicketForm(form);
    if (error) return fail(400, { values, error });

    /** @type {any} */
    let created;
    try {
      created = await createTicket({ cookies }, values);
    } catch (/** @type {any} */ err) {
      return fail(400, { values, stageRequirements: stageRequirements(err), error: readableError(err, 'Could not raise this ticket.') });
    }

    // `CaseListView.post` returns the new id, so this lands on the ticket
    // rather than back at a queue where the user has to go and find it.
    redirect(303, created?.id ? `/tickets/${created.id}` : '/tickets');
  }
};
