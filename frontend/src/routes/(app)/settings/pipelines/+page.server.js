import { fail } from '@sveltejs/kit';
import { getPipelineSettings, savePipelineSettings } from '$lib/server/v2/pipeline-settings.js';
import { readableError } from '$lib/server/v2/form-errors.js';
export const load = getPipelineSettings;
export const actions = {
  save: async (event) => {
    const form = await event.request.formData();
    try {
      const result = await savePipelineSettings(event, {
        target_model: form.get('target_model'),
        revision: form.get('revision'),
        stages: JSON.parse(String(form.get('stages'))),
        additions: JSON.parse(String(form.get('additions') || '[]')),
        removals: JSON.parse(String(form.get('removals') || '{}'))
      });
      return { saved: true, revision: result.revision };
    } catch (error) {
      return fail(400, { error: readableError(error, 'Could not save pipeline settings.') });
    }
  }
};
