<script>
  /**
   * A conversation, not a record view. The customer wants to know what was said
   * and to say something back, so the thread is the page and the case fields are
   * a header above it.
   */
  import { enhance } from '$app/forms';
  import { resolve } from '$app/paths';
  import PortalShell from '$lib/v2/components/PortalShell.svelte';

  let { data, form } = $props();

  const OPEN_STATUSES = new Set(['New', 'Assigned', 'Pending']);

  function formatWhen(value) {
    if (!value) return '';
    return new Date(value).toLocaleString(undefined, {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
</script>

<svelte:head>
  <title>{data.case.name}</title>
</svelte:head>

<PortalShell>
  <a class="back" href={resolve('/portal/cases')}>Back to your requests</a>

  <header class="head">
    <h1>{data.case.name}</h1>
    <span class="tag" class:open={OPEN_STATUSES.has(data.case.status)}>{data.case.status}</span>
  </header>

  {#if data.case.description}
    <p class="desc">{data.case.description}</p>
  {/if}

  <section class="thread">
    {#if data.comments.length === 0}
      <p class="empty">No replies yet. We will email you when support responds.</p>
    {:else}
      {#each data.comments as entry (entry.id)}
        <article class="msg" class:mine={entry.is_mine}>
          <div class="who">
            <strong>{entry.is_mine ? 'You' : entry.author}</strong>
            <span class="when">{formatWhen(entry.commented_on)}</span>
          </div>
          <p>{entry.comment}</p>
        </article>
      {/each}
    {/if}
  </section>

  <form method="POST" action="?/reply" use:enhance class="reply">
    <label for="comment">Add a reply</label>
    <textarea id="comment" name="comment" rows="4" placeholder="Type your message" required
    ></textarea>
    {#if form?.error}<p class="err">{form.error}</p>{/if}
    <button type="submit">Send reply</button>
  </form>
</PortalShell>

<style>
  .back {
    /* The only way back on a phone, so it gets a real tap target rather than
       the 19px a bare text link would be. Measured at 390px, not assumed. */
    display: inline-flex;
    align-items: center;
    min-height: 44px;
    margin-bottom: var(--crm-space-1);
    font-size: var(--crm-text-sm);
    color: var(--v2-slate, var(--crm-text-muted));
  }
  .head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: var(--crm-space-3);
    margin-bottom: 10px;
  }
  h1 {
    margin: 0;
    font-size: var(--crm-text-lg);
    font-weight: 600;
    /* Long summaries must wrap rather than push the tag off a 390px screen. */
    overflow-wrap: anywhere;
  }
  .tag {
    flex: none;
    padding: 3px 10px;
    border-radius: var(--crm-radius-full);
    background: var(--v2-rule, var(--crm-surface-secondary));
    font-size: var(--crm-text-sm);
  }
  .tag.open {
    background: var(--v2-moss-bg, var(--crm-success-bg));
  }
  .desc {
    margin: 0 0 var(--crm-space-5);
    color: var(--v2-slate, var(--crm-text-muted));
    font-size: var(--crm-text-sm);
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }
  .thread {
    display: grid;
    gap: var(--crm-space-3);
    margin-bottom: var(--crm-space-6);
  }
  .msg {
    border: 1px solid var(--v2-rule, var(--crm-border));
    border-radius: var(--crm-radius-md);
    padding: var(--crm-space-3) 14px;
  }
  .msg.mine {
    background: var(--v2-paper-2, var(--crm-canvas));
  }
  .who {
    display: flex;
    justify-content: space-between;
    gap: 10px;
    margin-bottom: 6px;
    font-size: var(--crm-text-sm);
    color: var(--v2-slate, var(--crm-text-muted));
  }
  .msg p {
    margin: 0;
    font-size: var(--crm-text-sm);
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }
  .reply label {
    display: block;
    margin-bottom: 6px;
    font-size: var(--crm-text-sm);
    font-weight: 500;
  }
  textarea {
    width: 100%;
    box-sizing: border-box;
    /* 16px stops iOS Safari zooming the viewport on focus. */
    font-size: var(--crm-text-base);
    padding: 11px;
    border: 1px solid var(--v2-rule, var(--crm-control-border));
    border-radius: var(--crm-radius-md);
  }
  button {
    margin-top: var(--crm-space-3);
    width: 100%;
    min-height: 46px;
    font-size: var(--crm-text-sm);
    border: 0;
    border-radius: var(--crm-radius-md);
    background: var(--v2-ink, var(--crm-text));
    color: var(--crm-surface);
    cursor: pointer;
  }
  .empty {
    color: var(--v2-slate, var(--crm-text-muted));
    font-size: var(--crm-text-sm);
  }
  .err {
    margin: 10px 0 0;
    color: var(--v2-rust, var(--crm-danger));
    font-size: var(--crm-text-sm);
  }
</style>
