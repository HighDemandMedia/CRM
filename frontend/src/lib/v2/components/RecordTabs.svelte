<script>
  /** @type {{notes: import('svelte').Snippet, activity: import('svelte').Snippet}} */
  let { notes, activity } = $props();
  let active = $state('notes');
  const id = $props.id();
  let notesButton, activityButton;
  function navigate(event) {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    active =
      event.key === 'Home'
        ? 'notes'
        : event.key === 'End'
          ? 'activity'
          : active === 'notes'
            ? 'activity'
            : 'notes';
    (active === 'notes' ? notesButton : activityButton)?.focus();
  }
</script>

<div class="record-tabs">
  <div
    class="tabs"
    role="tablist"
    tabindex="-1"
    aria-label="Notes and activity"
    onkeydown={navigate}
  >
    <button
      type="button"
      bind:this={notesButton}
      role="tab"
      id={`${id}-notes-tab`}
      aria-controls={`${id}-notes`}
      aria-selected={active === 'notes'}
      tabindex={active === 'notes' ? 0 : -1}
      onclick={() => (active = 'notes')}>Notes</button
    >
    <button
      type="button"
      bind:this={activityButton}
      role="tab"
      id={`${id}-activity-tab`}
      aria-controls={`${id}-activity`}
      aria-selected={active === 'activity'}
      tabindex={active === 'activity' ? 0 : -1}
      onclick={() => (active = 'activity')}>Activity</button
    >
  </div>
  <div
    class="panel"
    role="tabpanel"
    id={`${id}-notes`}
    aria-labelledby={`${id}-notes-tab`}
    hidden={active !== 'notes'}
    tabindex="0"
  >
    {@render notes()}
  </div>
  <div
    class="panel"
    role="tabpanel"
    id={`${id}-activity`}
    aria-labelledby={`${id}-activity-tab`}
    hidden={active !== 'activity'}
    tabindex="0"
  >
    {@render activity()}
  </div>
</div>

<style>
  .tabs {
    display: flex;
    gap: 28px;
    border-bottom: 1px solid var(--v2-line);
    margin-bottom: var(--crm-space-6);
  }
  .tabs button {
    background: none;
    border: 0;
    border-bottom: 3px solid transparent;
    padding: 0 0 15px;
    color: var(--v2-slate);
    font: inherit;
    cursor: pointer;
  }
  .tabs button[aria-selected='true'] {
    color: var(--v2-ink);
    border-bottom-color: var(--v2-ink);
    font-weight: 650;
  }
  .panel:focus-visible,
  button:focus-visible {
    outline: 2px solid var(--v2-ink);
    outline-offset: 3px;
  }
</style>
