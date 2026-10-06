<script>
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();

  import { untrack } from 'svelte';
  let { value = $bindable('') } = $props();
  let custom = $state(untrack(() => !['', '0', '1', '2', '3'].includes(String(value ?? ''))));
</script>

<label class="v2-field"
  ><span class="v2-label">{ui('Reminder')}</span>
  <select
    class="v2-input"
    value={custom ? 'custom' : String(value ?? '')}
    onchange={(event) => {
      const choice = event.currentTarget.value;
      custom = choice === 'custom';
      value = custom ? '7' : choice;
    }}
  >
    <option value="">{ui('No reminder')}</option>
    <option value="0">{ui('On due date')}</option>
    <option value="1">{ui('1 day before')}</option>
    <option value="2">{ui('2 days before')}</option>
    <option value="3">{ui('3 days before')}</option>
    <option value="custom">{ui('Custom…')}</option>
  </select>
</label>
{#if custom}
  <label class="v2-field"
    ><span class="v2-label">{ui('Days before due date')}</span>
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
