<script>
  /** @type {{entries:Array<[string,any]>}} */
  let { entries } = $props();
</script>

<dl>
  {#each entries as [label, value]}<div>
      <dt>{label}</dt>
      <dd>{value ?? '—'}</dd>
    </div>{/each}
</dl>

<style>
  dl {
    display: grid;
    gap: 18px;
    margin: 18px 0;
  }
  dt {
    font-size: 11px;
    color: var(--v2-slate);
    margin-bottom: 5px;
  }
  dd {
    margin: 0;
    font-size: 13px;
    line-height: 1.5;
    overflow-wrap: anywhere;
    white-space: pre-wrap;
  }
</style>
