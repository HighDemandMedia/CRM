<script>
  import { onMount } from 'svelte';
  /** @type {{value?:string|null}} */
  let { value = $bindable('') } = $props();
  let local = $state('');
  let ready = $state(false);
  onMount(() => {
    if (value) {
      const d = new Date(value);
      const pad = (n) => String(n).padStart(2, '0');
      if (Number.isFinite(d.getTime()))
        local = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
    }
    ready = true;
  });
</script>

<label
  >Appointment
  <input
    class="v2-input"
    type="datetime-local"
    disabled={!ready}
    bind:value={local}
    onchange={() => {
      value = local ? new Date(local).toISOString() : '';
    }}
  />
  <input type="hidden" name="appointment_at" value={value ?? ''} />
</label>

<style>
  label {
    display: grid;
    gap: 6px;
  }
  input {
    min-width: 0;
    width: 100%;
  }
</style>
