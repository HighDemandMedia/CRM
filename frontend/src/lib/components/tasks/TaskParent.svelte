<script>
  let { parents, kind = $bindable(''), selected = $bindable('') } = $props();
  let query = $state('');
  const labels = { account: 'Company', opportunity: 'Deal', case: 'Ticket', lead: 'Lead' };
  const records = $derived(
    Object.entries(parents).flatMap(([type, items]) => items.map((item) => ({ ...item, type })))
  );
  const current = $derived(records.find((item) => item.type === kind && item.id === selected));
  const matches = $derived(
    query.trim()
      ? records
          .filter((item) =>
            `${item.name} ${labels[item.type]}`.toLowerCase().includes(query.trim().toLowerCase())
          )
          .slice(0, 20)
      : []
  );
</script>

<div class="parent-picker">
  <label for="task-association">Association</label>
  {#if kind && selected}<div class="chosen">
      <span><small>{labels[kind]}</small>{current?.name ?? 'Associated record'}</span><button
        type="button"
        aria-label="Remove association"
        onclick={() => {
          kind = '';
          selected = '';
        }}>×</button
      >
    </div>{/if}
  <input
    id="task-association"
    class="v2-input"
    placeholder="Search associations…"
    bind:value={query}
    autocomplete="off"
    onkeydown={(event) => {
      if (event.key === 'Escape') query = '';
      if (event.key === 'Enter') {
        event.preventDefault();
        if (matches.length === 1) {
          kind = matches[0].type;
          selected = matches[0].id;
          query = '';
        }
      }
    }}
  />
  {#if query.trim()}<div class="matches">
      {#each matches as item}<button
          type="button"
          onclick={() => {
            kind = item.type;
            selected = item.id;
            query = '';
          }}><small>{labels[item.type]}</small>{item.name}</button
        >{:else}<p>No matches.</p>{/each}
    </div>{/if}
  <input type="hidden" name="parent_kind" value={kind} />
  {#if kind}<input type="hidden" name={`parent_${kind}`} value={selected} />{/if}
</div>

<style>
  .parent-picker {
    display: grid;
    gap: 8px;
    margin-bottom: 18px;
    font-size: 12px;
  }
  .chosen {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: var(--v2-paper);
    padding: 10px;
    border-radius: 7px;
  }
  small {
    display: block;
    color: var(--v2-slate);
    font-size: 11px;
    margin-bottom: 3px;
  }
  button {
    cursor: pointer;
    font: inherit;
    border: 0;
    background: transparent;
    color: var(--v2-ink);
  }
  .chosen button {
    width: 28px;
    height: 28px;
    font-size: 20px;
  }
  .matches {
    max-height: 200px;
    overflow: auto;
    border: 1px solid var(--v2-line);
    border-radius: 7px;
  }
  .matches button {
    display: block;
    padding: 10px;
    width: 100%;
    text-align: left;
  }
  .matches button:hover {
    background: var(--v2-paper);
  }
  .matches p {
    padding: 10px;
    margin: 0;
  }
</style>
