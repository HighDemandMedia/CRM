import { redirect } from '@sveltejs/kit';
import { getTask } from '$lib/server/v2/tasks.js';
import { getTaskEditor, saveTaskEditor } from '$lib/server/v2/task-editor.js';
export async function load(event) {
  const { task } = await getTask(event, event.params.id);
  return getTaskEditor(event, task);
}
export const actions = {
  save: async (event) => {
    const result = await saveTaskEditor(event);
    if ('saved' in result) redirect(303, `/tasks/${event.params.id}`);
    return result;
  }
};
