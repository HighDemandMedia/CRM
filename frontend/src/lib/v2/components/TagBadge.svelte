<script>
  import { tagColors } from '$lib/v2/tag-colors.js';
  /** @type {{tag: any}} */
  let { tag } = $props();
  let color = $derived(
    tagColors[/** @type {keyof typeof tagColors} */ (tag.color)] ?? tagColors.blue
  );
</script>

<span class="tag-badge" style:background={`${color}25`} style:border-color={color}>{tag.name}</span>

<style>
  .tag-badge {
    display: inline-block;
    max-width: 100%;
    overflow-wrap: anywhere;
    padding: 3px var(--crm-space-2);
    border: 1px solid;
    border-radius: var(--crm-radius-lg);
    color: var(--crm-text);
    font-size: var(--crm-text-xs);
    line-height: 1.4;
  }
</style>
