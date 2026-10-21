<script>
  import { Toaster as Sonner } from 'svelte-sonner';
  import { mode } from 'mode-watcher';

  let { ...restProps } = $props();
</script>

<Sonner theme={mode.current} class="toaster group" richColors {...restProps} />
