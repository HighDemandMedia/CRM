<script>
  /** @type {{stage?:string|null, label?:string, stages:{value:string,label:string,percentage?:number}[]}} */
  let { stage, label = '', stages } = $props();
  let pipeline = $derived(stages.filter((item) => item.value !== 'UNASSIGNED'));
  let position = $derived(pipeline.findIndex((item) => item.value === stage));
  let complete = $derived(stage === 'QUALIFIED' || stage === 'CLOSED_WON');
  let lost = $derived(stage === 'LOST' || stage === 'CLOSED_LOST');
  let percentage = $derived(pipeline[position]?.percentage);
  let name = $derived(pipeline[position]?.label || label || 'No stage');
</script>

<div class="stage-progress" aria-label={name}>
  <div class="segments" aria-hidden="true">
    {#each pipeline as item, index (item.value)}<span
        class:filled={percentage != null ? index < Math.ceil(percentage / 100 * pipeline.length) : !lost && (complete || (position >= 0 && index <= position))}
      ></span>{/each}
  </div>
  <span class="stage-name">{name}</span>
</div>

<style>
  .stage-progress {
    display: flex;
    flex-direction: column;
    gap: 6px;
    min-width: 0;
    padding: 4px 0;
  }
  .segments {
    display: flex;
    gap: 4px;
    width: 132px;
    max-width: 100%;
  }
  .segments span {
    flex: 1;
    min-width: 0;
    height: 6px;
    border-radius: 4px;
    background: #e5e5e5;
  }
  .segments span.filled {
    background: #252321;
  }
  .stage-name {
    color: var(--v2-muted, #79736f);
    font-size: 13px;
    line-height: 1.3;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
