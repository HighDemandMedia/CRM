<script>
  import { setContext, onMount, tick } from 'svelte';
  import { beforeNavigate, goto } from '$app/navigation';
  import { X } from '@lucide/svelte';
  let { url, title, component: Component, data, onclose, oncreated } = $props();
  let dialog,
    form = $state(null),
    busy = $state(false);
  let baseline = '';
  const fingerprint = () => {
    const node = dialog?.querySelector('form');
    return node
      ? JSON.stringify(
          [...new FormData(node)].map(([k, v]) => [k, typeof v === 'string' ? v : v.name])
        )
      : '';
  };
  setContext('creation-panel', {
    get url() {
      return url;
    },
    busy: () => busy,
    setBusy: (value) => (busy = value),
    async result(result) {
      if (result.type === 'redirect') {
        const target = new URL(result.location, url);
        const module = new URL(url).pathname.replace(/\/(new|[0-9a-f-]{36}\/edit)\/?$/i, '');
        if (
          target.origin === new URL(url).origin &&
          (target.pathname === module || target.pathname.startsWith(`${module}/`))
        ) {
          await oncreated();
        } else
          form = {
            error:
              'Your session may have expired. Keep this form open and sign in again in another tab.'
          };
      } else if (result.type === 'failure') form = result.data;
      else if (result.type === 'success') await oncreated();
      else form = { error: 'Could not save. Your entries are still here. Please try again.' };
    }
  });
  function close() {
    if (busy) return;
    onclose();
  }
  beforeNavigate((navigation) => {
    if (navigation.willUnload) {
      if (busy || fingerprint() !== baseline) navigation.cancel();
      return;
    }
    navigation.cancel();
    close();
  });
  onMount(() => {
    dialog.showModal();
    baseline = fingerprint();
    // Cancel/breadcrumb links in existing forms close the panel without changing the background route.
    const links = async (event) => {
      const link = event.target.closest('a');
      if (link) {
        event.preventDefault();
        event.stopPropagation();
        if (busy) return;
        const destination = link.hasAttribute('data-open-record') ? link.href : null;
        close();
        if (destination) {
          await tick();
          await goto(destination);
        }
      }
    };
    dialog.addEventListener('click', links, true);
    const element = dialog;
    return () => {
      element.removeEventListener('click', links, true);
      element.close();
    };
  });
</script>

<dialog
  bind:this={dialog}
  class="create-panel"
  aria-label={title}
  oncancel={(e) => {
    e.preventDefault();
    close();
  }}
>
  <header>
    <h2>{title}</h2>
    <button
      type="button"
      class="v2-btn v2-btn-quiet"
      aria-label="Close form"
      disabled={busy}
      onclick={close}><X size={19} /></button
    >
  </header>
  <div class="body" inert={busy} aria-busy={busy}>
    <Component {data} {form} />
  </div>
  {#if busy}<div class="saving" role="status">Saving…</div>{/if}
</dialog>

<style>
  .create-panel {
    position: fixed;
    inset: 0 0 0 auto;
    margin: 0;
    width: min(620px, 100vw);
    height: 100dvh;
    max-height: 100dvh;
    max-width: 100vw;
    padding: 0;
    border: 0;
    border-left: 1px solid var(--v2-line);
    background: var(--v2-bg);
    color: var(--v2-ink);
    box-shadow: -12px 0 40px #0002;
    overflow: hidden;
  }
  .create-panel[open] {
    display: flex;
    flex-direction: column;
    animation: enter 0.18s ease-out;
  }
  .create-panel::backdrop {
    background: #15151b26;
  }
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 18px 24px;
    border-bottom: 1px solid var(--v2-line);
    flex-shrink: 0;
    background: var(--v2-card);
  }
  h2 {
    font-size: 19px;
    margin: 0;
  }
  .body {
    flex: 1;
    min-height: 0;
    overflow: auto;
    padding: 0 24px;
  }
  .body :global(.v2-header) {
    display: none;
  }
  .body :global(.v2-scroll) {
    overflow: visible;
    padding: 18px 0 !important;
  }
  .body :global(form) {
    width: 100%;
    max-width: none !important;
    margin: 0 !important;
    padding: 0 !important;
    background: transparent !important;
  }
  .body :global(form > .actions),
  .body :global(form > div:last-child:has(> button[type='submit'])),
  .body :global(form > div:last-child:has(> a.v2-btn)) {
    position: sticky;
    bottom: 0;
    background: var(--v2-bg);
    padding: 16px 0;
    margin-bottom: 0;
    border-top: 1px solid var(--v2-line);
    z-index: 10;
  }
  .saving {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    background: var(--v2-card);
    padding: 18px 24px;
    border-top: 1px solid var(--v2-line);
  }
  @keyframes enter {
    from {
      transform: translateX(28px);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .create-panel[open] {
      animation: none;
    }
  }
  @media (max-width: 600px) {
    .body {
      padding: 0 16px;
    }
    header {
      padding: 16px;
    }
  }
</style>
