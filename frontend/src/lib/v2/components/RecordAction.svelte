<script>
  import * as Tooltip from '$lib/components/ui/tooltip/index.js';
  /** @type {{label:string,icon:import('svelte').Component<any>,href?:import('$app/types').ResolvedPathname,onclick?:(event:MouseEvent)=>void,disabled?:boolean,primary?:boolean,type?:'button'|'submit',name?:string,value?:string}} */
  let {
    label,
    icon: Icon,
    href,
    onclick,
    disabled = false,
    primary = false,
    type = 'button',
    name,
    value
  } = $props();
</script>

<Tooltip.Provider delayDuration={200}>
  <Tooltip.Root>
    <Tooltip.Trigger>
      {#snippet child({ props })}
        {#if href && !disabled}
          <!-- The caller resolves the typed destination, keeping this shared action route-agnostic. -->
          <!-- eslint-disable-next-line svelte/no-navigation-without-resolve -->
          <a {...props} class="record-action" class:primary {href} aria-label={label}
            ><Icon size={18} /></a
          >
        {:else}
          <button
            {...props}
            class="record-action"
            class:primary
            {type}
            {name}
            {value}
            {disabled}
            {onclick}
            aria-label={label}><Icon size={18} /></button
          >
        {/if}
      {/snippet}
    </Tooltip.Trigger>
    <Tooltip.Content side="bottom">{label}</Tooltip.Content>
  </Tooltip.Root>
</Tooltip.Provider>

<style>
  .record-action {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex: none;
    width: 40px;
    height: 40px;
    padding: 0;
    border: 1px solid var(--v2-line);
    border-radius: var(--crm-button-radius);
    background: var(--v2-card);
    color: var(--v2-ink);
    cursor: pointer;
    text-decoration: none;
  }
  .record-action:hover:not(:disabled) {
    border-color: var(--crm-focus);
    color: var(--crm-focus);
    background: var(--crm-canvas);
  }
  .record-action:focus-visible {
    outline: 2px solid var(--crm-focus);
    outline-offset: 3px;
  }
  .record-action:disabled {
    opacity: 0.5;
    cursor: default;
  }
  .primary {
    color: var(--crm-focus);
    border-color: var(--crm-focus);
  }
  @media (pointer: coarse) {
    .record-action {
      width: 44px;
      height: 44px;
    }
  }
</style>
