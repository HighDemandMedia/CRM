<script>
  import { LoaderCircle } from '@lucide/svelte';
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();
  /** @type {{saving:boolean,dirty:boolean,blocked?:boolean,oncancel:()=>void}} */
  let { saving, dirty, blocked = false, oncancel } = $props();
</script>

<div class="record-edit-actions" aria-label={ui('Save changes')}>
  <button type="button" class="v2-btn" disabled={saving || blocked} onclick={oncancel}
    >{ui('Cancel')}</button
  >
  <button type="submit" class="v2-btn v2-btn-primary" disabled={saving || blocked || !dirty}>
    {#if saving}<LoaderCircle size={15} class="saving-icon" />{/if}
    {saving ? ui('Saving…') : ui('Save')}
  </button>
</div>

<style>
  .record-edit-actions {
    position: sticky;
    top: 0;
    z-index: 5;
    display: flex;
    justify-content: flex-end;
    gap: var(--crm-space-2);
    padding: var(--crm-space-2) 0;
    margin-bottom: var(--crm-space-3);
    background: var(--crm-surface, #fff);
    border-bottom: 1px solid var(--v2-line);
  }
  button {
    min-height: var(--crm-target-size);
  }
  :global(.saving-icon) {
    animation: turn 1s linear infinite;
  }
  @keyframes turn {
    to {
      transform: rotate(360deg);
    }
  }
  @media (prefers-reduced-motion: reduce) {
    :global(.saving-icon) {
      animation: none;
    }
  }
</style>
