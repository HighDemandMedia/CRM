<script>
  import { untrack } from 'svelte';
  let { value = $bindable('') } = $props();
  let custom = $state(untrack(() => !['', '0', '1', '2', '3'].includes(String(value ?? ''))));
</script>

<label class="v2-field"
  ><span class="v2-label">Reminder</span>
  <select
    class="v2-input"
    value={custom ? 'custom' : String(value ?? '')}
    onchange={(event) => {
      const choice = event.currentTarget.value;
      custom = choice === 'custom';
      value = custom ? '7' : choice;
    }}
  >
    <option value="">No reminder</option>
    <option value="0">On due date</option>
    <option value="1">1 day before</option>
    <option value="2">2 days before</option>
    <option value="3">3 days before</option>
    <option value="custom">Custom…</option>
  </select>
</label>
{#if custom}
  <label class="v2-field"
    ><span class="v2-label">Days before due date</span>
    <input
      class="v2-input"
      type="number"
      min="0"
      max="365"
      step="1"
      required
      {value}
      oninput={(event) => (value = event.currentTarget.value)}
    />
  </label>
{/if}
<input type="hidden" name="reminder_days" value={value ?? ''} />
