<script>
  import { beforeNavigate, afterNavigate } from '$app/navigation';
  import { tick } from 'svelte';

  let { enabled = false } = $props();
  let started = 0;
  let sequence = 0;
  let sample = $state(0);
  let duration = $state(0);
  beforeNavigate(() => {
    sequence++;
    started = enabled ? performance.now() : 0;
  });
  afterNavigate(async () => {
    if (!started || !enabled) return;
    const current = sequence;
    const start = started;
    started = 0;
    await tick();
    requestAnimationFrame(() => {
      if (current !== sequence) return;
      duration = Math.round(performance.now() - start);
      sample++;
    });
  });
</script>

{#if enabled}
  <!-- Optional diagnostics, enabled by server configuration; no user data. -->
  <output hidden data-navigation-sample={sample} data-navigation-ms={duration}></output>
{/if}
