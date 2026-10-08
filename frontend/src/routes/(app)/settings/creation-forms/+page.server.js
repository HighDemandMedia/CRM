import { apiRequest } from '$lib/api-helpers.js';
import { fail } from '@sveltejs/kit';
import { settingsAccess } from '$lib/v2/settings-access.js';
import { creationObjects } from '$lib/server/v2/creation-forms.js';
import { readableError } from '$lib/server/v2/form-errors.js';

export async function load({ cookies, url, parent }) {
  const target = url.searchParams.get('object') || 'Contact';
  const [config, shell] = await Promise.all([
    apiRequest(`/creation-forms/?target_model=${encodeURIComponent(target)}`, {}, { cookies }),
    parent()
  ]);
  return {
    ...config,
    objects: creationObjects,
    can_edit: settingsAccess(shell.permissions, 'creation_forms') === 'manage'
  };
}
export const actions = {
  async save({ cookies, request }) {
    const form = await request.formData();
    try {
      await apiRequest(
        '/creation-forms/',
        {
          method: 'PUT',
          body: {
            target_model: form.get('target_model'),
            revision: form.get('revision'),
            selected: JSON.parse(String(form.get('selected')))
          }
        },
        { cookies }
      );
      return { saved: true };
    } catch (error) {
      return fail([403, 409].includes(error?.status) ? error.status : 400, {
        error: readableError(error, 'Could not save the creation form.')
      });
    }
  }
};
