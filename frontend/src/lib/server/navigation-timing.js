import { AsyncLocalStorage } from 'node:async_hooks';

// Request-local numeric diagnostics: never retain URLs, identities or payloads.
const timings = new AsyncLocalStorage();

export async function timeRequest(enabled, run) {
  if (!enabled) return { response: await run(), header: null };
  const state = { count: 0, api: 0 };
  const started = performance.now();
  const response = await timings.run(state, run);
  return {
    response,
    // API durations may overlap; api_total is not the request's critical path.
    header: `web;dur=${(performance.now() - started).toFixed(1)}, api_total;dur=${state.api.toFixed(1)}, api_count;desc="${state.count}"`
  };
}

export function startApiTiming() {
  const state = timings.getStore();
  if (!state) return () => {};
  const started = performance.now();
  return () => {
    state.count++;
    state.api += performance.now() - started;
  };
}
