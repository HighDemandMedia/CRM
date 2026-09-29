<script>
  /** @type {{id:string,href?:string|null}} */
  let { id, href } = $props();
  let email = $state(/** @type {any} */ (null)),
    busy = $state(false),
    error = $state('');
  async function load(event) {
    if (!event.currentTarget.open || email || busy) return;
    busy = true;
    error = '';
    try {
      const response = await fetch(`/api/google-mail/${id}`);
      const body = await response.json();
      if (!response.ok) throw new Error(body.error || 'Could not load email.');
      email = body;
    } catch (err) {
      error = err instanceof Error ? err.message : 'Could not load email.';
    } finally {
      busy = false;
    }
  }
</script>

<details ontoggle={load}>
  <summary>Read email</summary>
  {#if busy}<p>Loading email…</p>{/if}
  {#if error}<p class="v2-error" role="alert">{error}</p>{/if}
  {#if email}<p class="meta">From: {email.sender}<br />To: {email.recipients.join(', ')}</p>
    <div class="email-body">{email.body || '(Empty message)'}</div>{/if}
  {#if href}<a {href} target="_blank" rel="noopener noreferrer">Open in Gmail</a>{/if}
</details>

<style>
  details {
    margin-top: 8px;
    padding: 10px 12px;
    border: 1px solid var(--v2-line);
    border-radius: 8px;
  }
  summary {
    cursor: pointer;
    font-weight: 500;
  }
  .meta {
    color: var(--v2-slate);
    font-size: 12px;
    overflow-wrap: anywhere;
  }
  .email-body {
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    max-height: 480px;
    overflow: auto;
    padding: 12px 0;
    line-height: 1.6;
  }
</style>
