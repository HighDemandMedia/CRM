<script>
  import { Sun, Moon } from '@lucide/svelte';
  import { mode, setMode } from 'mode-watcher';
  import { useI18n } from '$lib/i18n/context.js';

  const { ui } = useI18n();
</script>

<section class="appearance" aria-labelledby="appearance-title">
  <h3 id="appearance-title">{ui('Appearance')}</h3>
  <div class="themes" role="group" aria-labelledby="appearance-title">
    <button
      class="v2-btn"
      class:selected={mode.current === 'light'}
      type="button"
      disabled={mode.current === undefined}
      aria-pressed={mode.current === 'light'}
      onclick={() => setMode('light')}><Sun size={16} aria-hidden="true" />{ui('Light')}</button
    >
    <button
      class="v2-btn"
      class:selected={mode.current === 'dark'}
      type="button"
      disabled={mode.current === undefined}
      aria-pressed={mode.current === 'dark'}
      onclick={() => setMode('dark')}><Moon size={16} aria-hidden="true" />{ui('Dark')}</button
    >
  </div>
</section>

<style>
  .appearance {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--crm-space-4);
    padding-block: var(--crm-space-5);
    border-top: 1px solid var(--crm-border-soft);
  }
  h3 {
    margin: 0;
    font-size: var(--crm-text-sm);
    font-weight: 600;
  }
  .themes {
    display: flex;
    gap: var(--crm-space-2);
  }
  .v2-btn.selected {
    color: var(--crm-link);
    background: var(--crm-surface-selected);
    border-color: var(--crm-focus);
  }
</style>
