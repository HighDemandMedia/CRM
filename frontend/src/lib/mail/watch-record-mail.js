/**
 * Poll the CRM cache only while the record is visible. Google push drives the
 * backend; this short request avoids holding WSGI/database connections open.
 * @param {{endpoint:string, onStatus:(data:any)=>void|Promise<void>, onUnavailable:()=>void|Promise<void>}} options
 */
export function watchRecordMail({ endpoint, onStatus, onUnavailable }) {
  let stopped = false;
  let running = false;
  let delay = 10000;
  let timer;
  let controller;
  async function check() {
    if (stopped || running || document.hidden) return;
    clearTimeout(timer);
    running = true;
    controller = new AbortController();
    const timeout = setTimeout(() => controller?.abort(), 15000);
    try {
      const response = await fetch(`${endpoint}?view=status`, { signal: controller.signal });
      if ([401, 403, 404].includes(response.status)) {
        stopped = true;
        await onUnavailable();
        return;
      }
      if (!response.ok) throw new Error('Mail status unavailable');
      const status = await response.json();
      if (!stopped) await onStatus(status);
      delay = 10000;
    } catch {
      // Keep the current content during a transient outage; back off, then retry.
      delay = Math.min(delay * 2, 60000);
    } finally {
      clearTimeout(timeout);
      running = false;
      if (!stopped && !document.hidden) timer = setTimeout(check, delay);
    }
  }
  function visibility() {
    clearTimeout(timer);
    if (document.hidden) controller?.abort();
    else void check();
  }
  document.addEventListener('visibilitychange', visibility);
  void check();
  return () => {
    stopped = true;
    clearTimeout(timer);
    controller?.abort();
    document.removeEventListener('visibilitychange', visibility);
  };
}
