<script>
  import RecordActivityEntry from './RecordActivityEntry.svelte';

  /**
   * Newest first. The filled dot marks the latest event only. Everything
   * else is a hairline, so the eye lands on "what happened last".
   *
   * @type {{ events: Array<{ id: string, body: string, at: string, by?: string|null, type?: string }> }}
   */
  let { events = [] } = $props();
</script>

<div class="v2-timeline">
  {#each events as e, i (e.id)}
    <div class="v2-event" class:latest={i === 0}>
      <RecordActivityEntry event={e} />
    </div>
  {/each}
</div>
