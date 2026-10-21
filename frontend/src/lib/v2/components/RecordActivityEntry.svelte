<script>
  import { useI18n } from '$lib/i18n/context.js';
  import { activityParts, activityText } from '$lib/v2/activity-presentation.js';
  const { ui, exactTime } = useI18n();
  /** @type {{event: {body: string, at: string, by?: string|null, href?: string|null}}} */
  let { event } = $props();
  const parts = $derived(activityParts(event));
  const readable = (text) => activityText(text, exactTime, ui);
</script>

<div class="record-event">
  <div class="event-title">{readable(parts.summary)}</div>
  <div class="event-meta">
    {event.by || ui('Not recorded')} · <time datetime={event.at}>{exactTime(event.at)}</time>
  </div>
  {#if parts.details}
    <details>
      <summary>{ui('View changes')}</summary>
      <div class="event-changes">{readable(parts.details)}</div>
    </details>
  {/if}
</div>

<style>
  .record-event {
    min-width: 0;
    overflow-wrap: anywhere;
  }
  .event-title {
    font-size: var(--crm-text-sm);
    font-weight: 600;
    white-space: pre-wrap;
  }
  .event-meta {
    font-size: var(--crm-text-xs);
    color: var(--crm-text-muted);
    margin-top: var(--crm-space-1);
  }
  summary {
    width: fit-content;
    cursor: pointer;
    color: var(--crm-link);
    font-size: var(--crm-text-xs);
    padding-block: var(--crm-space-2);
  }
  .event-changes {
    white-space: pre-wrap;
    font-size: var(--crm-text-sm);
    line-height: var(--crm-leading);
    padding: var(--crm-space-3);
    border-radius: var(--crm-radius-sm);
    background: var(--crm-canvas);
  }
  @media (pointer: coarse) {
    summary {
      min-height: var(--crm-target-size);
      display: flex;
      align-items: center;
    }
  }
</style>
