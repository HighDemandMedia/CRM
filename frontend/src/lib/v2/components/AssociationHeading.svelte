<script>
  import { ChevronDown, ChevronRight } from '@lucide/svelte';
  /** @type {{title:string,count:number,collapsible?:boolean,expanded?:boolean,controls:string}} */
  let { title, count, collapsible = false, expanded = $bindable(true), controls } = $props();
</script>

<h2>
  {#if collapsible}
    <button
      type="button"
      aria-expanded={expanded}
      aria-controls={controls}
      onclick={() => (expanded = !expanded)}
    >
      {#if expanded}<ChevronDown size={14} />{:else}<ChevronRight size={14} />{/if}
      {title} <span>{count}</span>
    </button>
  {:else}{title} <span>{count}</span>{/if}
</h2>

<style>
  h2 {
    margin: 0;
    font-size: var(--crm-text-sm);
    font-weight: 650;
  }
  button {
    display: flex;
    align-items: center;
    gap: 6px;
    min-height: 32px;
    padding: 0;
    border: 0;
    background: transparent;
    color: inherit;
    font: inherit;
    text-align: left;
    cursor: pointer;
  }
  span {
    color: var(--v2-slate);
    font-size: var(--crm-text-xs);
    font-weight: 400;
  }
  button :global(svg) {
    flex: none;
  }
</style>
