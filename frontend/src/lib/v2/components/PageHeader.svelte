<script>
  /**
   * @type {{
   *   title: string,
   *   record?: boolean,
   *   center?: boolean,
   *   compact?: boolean,
   *   width?: string,
   *   leading?: import('svelte').Snippet,
   *   sub?: import('svelte').Snippet,
   *   crumb?: import('svelte').Snippet,
   *   actions?: import('svelte').Snippet
   * }}
   *
   * `center` narrows the header to a form column so it sits above a centred
   * `.v2-form` (or other centred body) rather than spanning the full width.
   * `width` overrides that column's outer width for pages whose body is wider
   * than the standard 560px form, pass the body's own max-width.
   *
   * `leading` renders before the title block. An avatar or record mark. It is
   * centred against the text so it sits beside the name, not the crumb.
   */
  let {
    title,
    record = false,
    center = false,
    compact = false,
    width,
    leading,
    sub,
    crumb,
    actions
  } = $props();
</script>

<header
  class="v2-header"
  class:is-centered={center}
  class:is-compact={compact}
  style={center && width ? `--v2-header-col:${width}` : null}
>
  {#if leading}<div style="align-self:center;flex:none">{@render leading()}</div>{/if}
  <div class="heading" style="min-width:0">
    {#if crumb}<div class="v2-crumb">{@render crumb()}</div>{/if}
    <h1 class={record ? 'v2-record-title' : 'v2-page-title'}>{title}</h1>
    {#if sub}<div class="v2-sub">{@render sub()}</div>{/if}
  </div>
  {#if actions}<div class="v2-actions">{@render actions()}</div>{/if}
</header>

<style>
  .v2-sub {
    margin-top: 5px;
  }
  .v2-header.is-compact {
    align-items: center;
    gap: var(--crm-space-2);
    padding: var(--crm-space-3) var(--crm-space-3) 0;
  }
  .is-compact .heading {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    column-gap: var(--crm-space-3);
    row-gap: var(--crm-space-1);
  }
  .is-compact .v2-sub {
    margin-top: 0;
  }
  .v2-header.is-compact .v2-actions {
    width: auto;
    margin-left: auto;
    padding-top: 0;
    flex-wrap: wrap;
  }
</style>
