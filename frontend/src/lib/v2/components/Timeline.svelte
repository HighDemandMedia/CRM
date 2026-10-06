<script>
  import { useI18n } from '$lib/i18n/context.js';
  const { relativeDays } = useI18n();

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
      <div style="font-weight:500">{e.body}</div>
      <div class="v2-event-meta">{relativeDays(e.at) + (e.by ? ` · ${e.by}` : '')}</div>
    </div>
  {/each}
</div>
