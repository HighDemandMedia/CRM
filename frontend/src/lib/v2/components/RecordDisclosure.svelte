<script>
  import { onMount } from 'svelte';
  /** @type {{title:string, class?:string, collapseBelowRem?:number, expandForEditor?:boolean, header?:import('svelte').Snippet, children:import('svelte').Snippet}} */
  let {
    title,
    class: className = '',
    collapseBelowRem = 72,
    expandForEditor = false,
    header,
    children
  } = $props();
  let element = $state();
  let expanded = $state(true);
  $effect(() => {
    if (expandForEditor) expanded = true;
  });
  onMount(() => {
    // Match available record space, including when the main navigation is collapsed.
    let previousNarrow;
    const observer = new ResizeObserver(([entry]) => {
      const rootSize = parseFloat(getComputedStyle(document.documentElement).fontSize);
      const narrow = entry.contentRect.width <= collapseBelowRem * rootSize;
      if (narrow !== previousNarrow) {
        if (!expandForEditor && !element.contains(document.activeElement)) expanded = !narrow;
        previousNarrow = narrow;
      }
    });
    observer.observe(element.parentElement);
    return () => observer.disconnect();
  });
</script>

{#if header}
  <section bind:this={element} class="hdm-panel record-disclosure {className}">
    {@render header()}
    <details bind:open={expanded}>
      <summary>{title}</summary>
      <div class="disclosure-body">{@render children()}</div>
    </details>
  </section>
{:else}
  <details bind:this={element} class="hdm-panel record-disclosure {className}" bind:open={expanded}>
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
