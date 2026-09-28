import { enhance } from '$app/forms';

// Keep transport failures on the form: SvelteKit's default error handling
// navigates to the error page even when only the response body was interrupted.
export function authForm(node, { setBusy, setError }) {
  let pending;
  const enhanced = enhance(node, ({ controller, cancel }) => {
    if (pending) {
      cancel();
      return;
    }
    setBusy(true);
    setError('');
    const request = { controller, timer: undefined };
    pending = request;
    request.timer = setTimeout(() => {
      pending = undefined;
      controller.abort();
      setBusy(false);
      setError('The server took too long to respond. Please try again.');
    }, 30000);

    return async ({ result, update }) => {
      if (pending !== request) return;
      clearTimeout(request.timer);
      try {
        if (result.type === 'error') {
          setError('We couldn’t complete the request. Please try again.');
          return;
        }
        await update({ reset: false });
      } catch {
        setError('We couldn’t complete the request. Please reload the page and try again.');
      } finally {
        pending = undefined;
        setBusy(false);
      }
    };
  });
  return {
    destroy() {
      if (pending) {
        clearTimeout(pending.timer);
        pending.controller.abort();
        pending = undefined;
      }
      enhanced.destroy();
    }
  };
}
