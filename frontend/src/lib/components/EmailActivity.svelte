<script>
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();

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
  <summary>{ui('Read email')}</summary>
  {#if busy}<p>{ui('Loading email…')}</p>{/if}
  {#if error}<p class="v2-error" role="alert">{ui(error)}</p>{/if}
  {#if email}<p class="meta">
      {ui('From:')}
      {email.sender}<br />{ui('To:')}
      {email.recipients.join(', ')}
    </p>
    <div class="email-body">{email.body || '(Empty message)'}</div>{/if}
  {#if href}<a {href} target="_blank" rel="noopener noreferrer">{ui('Open in Gmail')}</a>{/if}
</details>

<style>
  details {
    margin-top: var(--crm-space-2);
    padding: 10px var(--crm-space-3);
    border: 1px solid var(--v2-line);
    border-radius: var(--crm-radius-md);
  }
  summary {
    cursor: pointer;
    font-weight: 500;
  }
  .meta {
    color: var(--v2-slate);
    font-size: var(--crm-text-xs);
    overflow-wrap: anywhere;
  }
  .email-body {
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    max-height: 480px;
    overflow: auto;
    padding: var(--crm-space-3) 0;
    line-height: 1.6;
  }
</style>
