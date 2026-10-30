<script>
  /** @type {{title:string, class?:string, expandForEditor?:boolean, header?:import('svelte').Snippet, children:import('svelte').Snippet}} */
  let { title, class: className = '', expandForEditor = false, header, children } = $props();
  let expanded = $state(true);
  $effect(() => {
    if (expandForEditor) expanded = true;
  });
</script>

{#if header}
  <section class="hdm-panel record-disclosure {className}">
    {@render header()}
    <details bind:open={expanded}>
      <summary>{title}</summary>
      <div class="disclosure-body">{@render children()}</div>
    </details>
  </section>
{:else}
  <details class="hdm-panel record-disclosure {className}" bind:open={expanded}>
    <summary>{title}</summary>
    <div class="disclosure-body">{@render children()}</div>
  </details>
{/if}

<style>
  .record-disclosure {
    align-self: start;
    max-height: 100%;
  }
  summary {
    cursor: pointer;
    font-size: var(--crm-text-sm);
    font-weight: 650;
    min-height: var(--crm-target-size);
    align-content: center;
  }
  .disclosure-body {
    padding-top: var(--crm-space-2);
  }
  details:not([open]) {
    align-self: start;
  }
</style>
