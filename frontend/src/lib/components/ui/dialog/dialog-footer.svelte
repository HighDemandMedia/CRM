<script>
  import { cn } from '$lib/utils.js';
  let { ref = $bindable(null), class: className = undefined, children, ...restProps } = $props();
</script>

<div
  bind:this={ref}
  data-slot="dialog-footer"
  class={cn('flex flex-row justify-end gap-2', className)}
  {...restProps}
>
  {@render children?.()}
</div>
