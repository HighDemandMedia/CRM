<script>
  import { onMount } from 'svelte';
  /** @type {{title:string, class?:string, collapseBelowRem?:number, children:import('svelte').Snippet}} */
  let { title, class: className = '', collapseBelowRem = 72, children } = $props();
  let element;
  let expanded = $state(true);
  onMount(() => {
    // Match available record space, including when the main navigation is collapsed.
    let previousNarrow;
    const observer = new ResizeObserver(([entry]) => {
      const rootSize = parseFloat(getComputedStyle(document.documentElement).fontSize);
      const narrow = entry.contentRect.width <= collapseBelowRem * rootSize;
      if (narrow !== previousNarrow) {
        if (!element.contains(document.activeElement)) expanded = !narrow;
        previousNarrow = narrow;
      }
    });
    observer.observe(element.parentElement);
    return () => observer.disconnect();
  });
</script>

<details bind:this={element} class="hdm-panel record-disclosure {className}" bind:open={expanded}>
  <summary>{title}</summary>
  <div class="disclosure-body">{@render children()}</div>
</details>

<style>
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
