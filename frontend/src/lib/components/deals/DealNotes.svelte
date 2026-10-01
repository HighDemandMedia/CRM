<script>
  import { enhance } from '$app/forms';
  import { exactTime } from '$lib/v2/contact-time.js';
  /** @type {{ notes: Array<{id:string,body:string,by:string|null,at:string}> }} */
  let { notes } = $props();
  let note = $state('');
  let noteBusy = $state(false);
  let noteError = $state('');
</script>

<div class="notes-panel">
  <form
    method="POST"
    action="?/note"
    use:enhance={() => {
      noteBusy = true;
      noteError = '';
      return async ({ result, update }) => {
        noteBusy = false;
        if (result.type === 'success') {
          note = '';
          await update({ reset: false });
        } else
          noteError =
            result.type === 'failure'
              ? String(result.data?.message ?? 'Could not save note.')
              : 'Could not save note.';
      };
    }}
  >
    <textarea
      class="v2-input"
      name="comment"
      aria-label="New note"
      rows="3"
      placeholder="Write a note…"
      bind:value={note}></textarea>
    <button type="submit" class="v2-btn add-note" disabled={noteBusy || !note.trim()}
      >{noteBusy ? 'Saving…' : 'Add note'}</button
    >
    {#if noteError}<p class="v2-error" role="alert">{noteError}</p>{/if}
  </form>
  <div class="notes-list">
    {#each notes as entry (entry.id)}
      <article class="history-entry">
        <div class="history-body">{entry.body}</div>
        <div class="entry-meta">{entry.by || 'Not recorded'} · {exactTime(entry.at)}</div>
      </article>
    {:else}<p class="v2-sub">No notes.</p>{/each}
  </div>
</div>

<style>
  .notes-list {
    max-height: 320px;
    overflow-y: auto;
    overscroll-behavior-y: contain;
    padding-right: 6px;
  }
  form {
    display: grid;
    gap: 8px;
    margin-bottom: 14px;
  }
  textarea {
    width: 100%;
    resize: vertical;
    max-height: 140px;
  }
  .add-note {
    justify-self: start;
    width: auto;
  }
  .history-entry {
    padding: 12px 0;
    border-bottom: 1px solid var(--v2-line-soft);
  }
  .history-body {
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    font-size: 14px;
  }
  .entry-meta {
    font-size: 12px;
    color: var(--v2-slate);
    margin-top: 6px;
  }
</style>
