<script>
  import { onMount } from 'svelte';
  import { X } from '@lucide/svelte';
  let { title, subtitle = '', busy = false, onclose, children } = $props();
  let dialog;
  onMount(() => {
    dialog.showModal();
    return () => dialog?.close();
  });
</script>

<dialog
  bind:this={dialog}
  aria-label={title}
  oncancel={(e) => {
    e.preventDefault();
    if (!busy) onclose();
  }}
>
  <header>
    <div>
      <h2>{title}</h2>
      {#if subtitle}<p>{subtitle}</p>{/if}
    </div>
    <button
      type="button"
      class="v2-btn v2-btn-quiet"
      aria-label="Close panel"
      disabled={busy}
      onclick={onclose}><X size={19} /></button
    >
  </header>
  <div class="content">{@render children()}</div>
</dialog>

<style>
  dialog {
    position: fixed;
    inset: 0 0 0 auto;
    margin: 0;
    width: min(480px, 100vw);
    max-width: 100vw;
    height: 100dvh;
    max-height: 100dvh;
    padding: 0;
    border: 0;
    border-left: 1px solid var(--v2-line);
    background: var(--v2-card, #fff);
    color: var(--v2-ink);
    text-align: left;
    box-shadow: -16px 0 60px #0002;
    overflow: hidden;
  }
  dialog[open] {
    display: flex;
    flex-direction: column;
    animation: arrive 0.16s ease-out;
  }
  dialog::backdrop {
    background: #17151b55;
  }
  header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    padding: 24px;
    border-bottom: 1px solid var(--v2-line-soft);
    flex-shrink: 0;
  }
  h2 {
    font-size: 20px;
    font-weight: 600;
    margin: 0;
  }
  p {
    font-size: 13px;
    color: var(--v2-slate);
    margin: 6px 0 0;
    line-height: 1.5;
  }
  .content {
    min-height: 0;
    flex: 1;
    display: flex;
    flex-direction: column;
  }
  .content :global(.panel-form) {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
  }
  .content :global(.panel-body) {
    padding: 24px;
    min-height: 0;
    overflow: auto;
    overscroll-behavior: contain;
    scrollbar-gutter: stable;
    flex: 1;
  }
  .content :global(.panel-footer) {
    padding: 18px 24px;
    border-top: 1px solid var(--v2-line-soft);
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    flex-shrink: 0;
  }
  .content :global(.field) {
    display: grid;
    gap: 8px;
    font-size: 13px;
    font-weight: 500;
    margin-bottom: 22px;
  }
  .content :global(.field .v2-input) {
    width: 100%;
    font-weight: 400;
    min-height: 40px;
  }
  .content :global(.field small) {
    font-size: 12px;
    font-weight: 400;
    color: var(--v2-slate);
    line-height: 1.5;
  }
  .content :global(.panel-error) {
    font-size: 13px;
    color: var(--v2-rust);
    margin: 14px 0;
    line-height: 1.5;
  }
  @keyframes arrive {
    from {
      transform: translateX(24px);
      opacity: 0.5;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }
  @media (prefers-reduced-motion: reduce) {
    dialog[open] {
      animation: none;
    }
  }
</style>
