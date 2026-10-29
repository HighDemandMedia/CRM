<script>
  import { enhance } from '$app/forms';
  import { onMount } from 'svelte';
  import { useI18n } from '$lib/i18n/context.js';
  import { googleErrorMessage } from '$lib/utils/google-feedback.js';
  import ErrorNotice from './ErrorNotice.svelte';
  const { ui } = useI18n();
  let { pending = false, onManage } = $props();
  let calendars = $state(/** @type {any[]} */ ([]));
  let selected = $state('');
  let availability = $state(/** @type {string[]} */ ([])),
    savedAvailability = $state('');
  let loading = $state(false),
    loaded = $state(false),
    error = $state('');
  let search = $state('');
  const options = $derived(
    calendars.filter(
      (calendar) =>
        calendar.readable &&
        calendar.id !== selected &&
        !calendar.id.endsWith('#holiday@group.v.calendar.google.com')
    )
  );
  const changed = $derived(JSON.stringify([...availability].sort()) !== savedAvailability);
  onMount(() => {
    void load();
  });
  async function load() {
    if (loading) return;
    loading = true;
    error = '';
    try {
      const response = await fetch('/profile/google/calendars');
      const result = await response.json();
      if (!response.ok) throw new Error(googleErrorMessage(result.error));
      calendars = Array.isArray(result.calendars) ? result.calendars : [];
      selected = result.selected;
      availability = result.availability ?? [];
      savedAvailability = JSON.stringify([...availability].sort());
      loaded = true;
    } catch (cause) {
      error = googleErrorMessage(cause);
    } finally {
      loading = false;
    }
  }
</script>

<div class="calendar-settings" hidden={loaded && !options.length && !error && !loading}>
  {#if loading}<p role="status">{ui('Loading…')}</p>{/if}
  {#if error}<ErrorNotice message={ui(error)} /><button class="v2-btn v2-btn-sm" onclick={load}
      >{ui('Retry')}</button
    >{/if}
  {#if loaded}
    <form
      method="POST"
      action="?/googleManage"
      use:enhance={() => {
        const finish = onManage();
        return async (result) => {
          await finish(result);
          if (result.result.type === 'success') await load();
        };
      }}
    >
      <input type="hidden" name="service" value="calendar" />
      <input type="hidden" name="operation" value="calendar" />
      <input type="hidden" name="calendar_id" value={selected} />
      {#each availability.filter((id) => !options.some((calendar) => calendar.id === id)) as id (id)}
        <input type="hidden" name="availability_calendar_ids" value={id} />
      {/each}
      <fieldset disabled={pending}>
        <legend>{ui('Calendars for availability')}</legend>
        <input
          class="v2-input"
          type="search"
          aria-label={ui('Search calendars')}
          placeholder={ui('Search calendars')}
          bind:value={search}
        />
        <div class="calendar-options">
          {#each options as calendar (calendar.id)}
            <label
              class="calendar-option"
              hidden={!calendar.name.toLowerCase().includes(search.toLowerCase())}
            >
              <input
                type="checkbox"
                name="availability_calendar_ids"
                value={calendar.id}
                bind:group={availability}
              />
              <span>{calendar.name}</span>
            </label>
          {/each}
          {#if !options.some((c) => c.name.toLowerCase().includes(search.toLowerCase()))}<p>
              {ui('No results.')}
            </p>{/if}
        </div>
      </fieldset>
      <button
        class="v2-btn v2-btn-primary v2-btn-sm"
        disabled={pending || !changed || !selected || availability.length > 10}
        >{ui(pending ? 'Saving…' : 'Save changes')}</button
      >
      {#if availability.length > 10}<ErrorNotice
          message={ui('Select up to 10 additional calendars.')}
        />{/if}
    </form>
  {/if}
</div>

<style>
  .calendar-settings {
    margin-top: 16px;
    border-top: 1px solid var(--crm-border-soft);
    padding-top: 8px;
  }
  form {
    display: grid;
    gap: 12px;
    margin-top: 12px;
    max-width: 480px;
  }
  label {
    display: grid;
    gap: 6px;
    font-size: var(--crm-text-sm);
  }
  input[type='search'] {
    width: 100%;
    min-width: 0;
  }
  fieldset {
    padding: 0;
    border: 0;
    min-width: 0;
  }
  legend {
    font-size: var(--crm-text-sm);
    margin-bottom: 8px;
  }
  .calendar-options {
    max-height: 180px;
    overflow-y: auto;
    margin-top: 6px;
  }
  .calendar-option {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 9px 4px;
    cursor: pointer;
  }
  .calendar-option[hidden] {
    display: none;
  }
  .calendar-option span {
    overflow-wrap: anywhere;
  }
  .calendar-option input {
    width: 16px;
    height: 16px;
    flex-shrink: 0;
    accent-color: var(--v2-ink);
  }
  p {
    margin: 0;
    color: var(--v2-slate);
    font-size: var(--crm-text-xs);
    line-height: 1.5;
  }
  button {
    justify-self: start;
  }
</style>
