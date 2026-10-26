<script>
  import { List, Columns3 } from '@lucide/svelte';
  import { toast } from 'svelte-sonner';
  import { useI18n } from '$lib/i18n/context.js';

  /** @type {{ view: string, onchange: (view: 'list' | 'pipeline') => void | Promise<void> }} */
  let { view = 'list', onchange } = $props();
  const { ui } = useI18n();
  let pending = $state(false);
  const pipeline = $derived(view === 'pipeline');

  async function toggle() {
    if (pending) return;
    pending = true;
    try {
      await onchange(pipeline ? 'list' : 'pipeline');
    } catch {
      toast.error(ui('Could not change view. Please try again.'));
    } finally {
      pending = false;
    }
  }
</script>

<button
  type="button"
  class="view-switch"
  class:pipeline
  role="switch"
  aria-label={ui('Pipeline view')}
  aria-checked={pipeline}
  aria-busy={pending}
  disabled={pending}
  title={ui(pipeline ? 'Switch to list view' : 'Switch to pipeline view')}
  onclick={toggle}
>
  <span class="thumb" aria-hidden="true"></span>
  <span class="option" class:selected={!pipeline} aria-hidden="true"><List size={17} /></span>
  <span class="option" class:selected={pipeline} aria-hidden="true"><Columns3 size={17} /></span>
</button>

<style>
  .view-switch {
    position: relative;
    display: inline-grid;
    grid-template-columns: repeat(2, 1fr);
    align-items: center;
    flex-shrink: 0;
    width: 76px;
    height: 36px;
    padding: 3px;
    border: 1px solid var(--v2-line);
    border-radius: var(--crm-button-radius);
    background: var(--v2-card);
    color: var(--v2-muted);
    cursor: pointer;
  }
  .thumb {
    position: absolute;
    inset: 3px auto 3px 3px;
    width: calc((100% - 6px) / 2);
    border-radius: var(--crm-button-radius);
    background: var(--crm-action-bg);
    transition: transform 150ms ease;
  }
  .pipeline .thumb {
    transform: translateX(100%);
  }
  .option {
    position: relative;
    display: grid;
    place-items: center;
  }
  .selected {
    color: var(--crm-primary-text);
  }
  .view-switch:hover {
    border-color: var(--v2-slate);
  }
  .view-switch:focus-visible {
    outline: 2px solid var(--crm-link);
    outline-offset: 3px;
  }
  .view-switch:disabled {
    cursor: wait;
    opacity: 0.65;
  }
  @media (prefers-reduced-motion: reduce) {
    .thumb {
      transition: none;
    }
  }
</style>
