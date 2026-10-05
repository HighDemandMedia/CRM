<script>
  /** @type {{title:string, collapsible?:boolean, children:import('svelte').Snippet}} */
  let { title, collapsible = false, children } = $props();
</script>

{#if collapsible}
  <details class="record-section optional-section">
    <summary>{title}</summary>
    <div class="record-fields">{@render children()}</div>
  </details>
{:else}
  <fieldset class="record-section">
    <legend>{title}</legend>
    <div class="record-fields">{@render children()}</div>
  </fieldset>
{/if}

<style>
  .record-section {
    border: 0;
    padding: 0;
    margin: 0 0 26px;
    min-width: 0;
  }
  legend {
    width: 100%;
    padding: 0 0 10px;
    margin-bottom: var(--crm-space-4);
    border-bottom: 1px solid var(--v2-line);
    font-size: var(--crm-text-sm);
    font-weight: 600;
    color: var(--v2-ink);
  }
  summary {
    cursor: pointer;
    padding: var(--crm-space-3) 0;
    font-size: var(--crm-text-sm);
    font-weight: 600;
    border-bottom: 1px solid var(--v2-line);
  }
  .optional-section[open] summary {
    margin-bottom: var(--crm-space-4);
  }
  .record-fields {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: var(--crm-space-4);
  }
  .record-fields :global(.v2-field) {
    margin-bottom: 0;
  }
</style>
