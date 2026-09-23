import { getContext } from 'svelte';
import { enhance } from '$app/forms';

// Read context during component initialization, not when the form action mounts.
export function creationEnhance() {
  const panel = getContext('creation-panel');
  if (!panel) return enhance;
  return (node, submit) => {
    node.action = new URL(node.getAttribute('action') || '?/create', panel.url).href;
    return enhance(node, async (input) => {
      if (panel.busy()) {
        input.cancel();
        return;
      }
      let cancelled = false;
      const callback = await submit?.({
        ...input,
        cancel() {
          cancelled = true;
          input.cancel();
        }
      });
      if (cancelled) return;
      panel.setBusy(true);
      return async (output) => {
        const update = async () => panel.result(output.result);
        try {
          if (callback) await callback({ ...output, update });
          else await update();
        } finally {
          panel.setBusy(false);
        }
      };
    });
  };
}
