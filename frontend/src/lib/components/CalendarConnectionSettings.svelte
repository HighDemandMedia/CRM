<script>
  import { enhance } from '$app/forms';
  import { onMount } from 'svelte';
  import { useI18n } from '$lib/i18n/context.js';
  import { googleErrorMessage } from '$lib/utils/google-feedback.js';
  import ErrorNotice from './ErrorNotice.svelte';
  import { ChevronDown, X } from '@lucide/svelte';
  import * as Popover from '$lib/components/ui/popover/index.js';
  import ChoiceList from '$lib/v2/components/ChoiceList.svelte';
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
  let open = $state(false);
  const options = $derived(
    calendars.filter(
      (calendar) =>
        calendar.readable &&
        calendar.id !== selected &&
        !calendar.id.endsWith('#holiday@group.v.calendar.google.com')
    )
  );
  const choices = $derived(
    options.map((calendar) => ({ value: calendar.id, label: calendar.name }))
  );
  const chosen = $derived(options.filter((calendar) => availability.includes(calendar.id)));
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
      {#each availability as id (id)}
        <input type="hidden" name="availability_calendar_ids" value={id} />
      {/each}
      <fieldset disabled={pending}>
        <legend>{ui('Calendars for availability')}</legend>
        {#if chosen.length}
          <div class="selected-calendars">
            {#each chosen as calendar (calendar.id)}
              <span class="calendar-chip">
                <span>{calendar.name}</span>
                <button
                  type="button"
                  class="v2-btn v2-btn-icon"
                  disabled={pending}
                  aria-label={`${ui('Remove')}: ${calendar.name}`}
                  onclick={() => (availability = availability.filter((id) => id !== calendar.id))}
                  ><X size={15} aria-hidden="true" /></button
                >
              </span>
            {/each}
          </div>
        {/if}
        <Popover.Root bind:open onOpenChange={() => (search = '')}>
          <Popover.Trigger asChild class="">
            {#snippet child({ props })}
              <button
                {...props}
                type="button"
                class="v2-input calendar-trigger"
                disabled={pending}
                aria-label={ui('Calendars for availability')}
              >
                <span>{ui('Search calendars')}</span><ChevronDown size={15} aria-hidden="true" />
              </button>
            {/snippet}
          </Popover.Trigger>
          <Popover.Content
            align="start"
            collisionPadding={8}
            class="calendar-availability-popover"
            aria-label={ui('Calendars for availability')}
          >
            <ChoiceList
              options={choices}
              bind:value={availability}
              multiple
              label={ui('Calendars for availability')}
              bind:query={search}
              disabled={pending}
            />
          </Popover.Content>
        </Popover.Root>
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
  fieldset {
    padding: 0;
    border: 0;
    min-width: 0;
  }
  legend {
    font-size: var(--crm-text-sm);
    margin-bottom: 8px;
  }
  .selected-calendars {
    display: flex;
    flex-wrap: wrap;
    gap: var(--crm-space-2);
    margin-bottom: var(--crm-space-2);
  }
  .calendar-chip {
    display: inline-flex;
    align-items: center;
    gap: var(--crm-space-1);
    max-width: 100%;
    padding-left: var(--crm-space-2);
    background: var(--crm-surface-secondary);
    border: 1px solid var(--crm-border);
    border-radius: var(--crm-radius-md);
    font-size: var(--crm-text-sm);
  }
  .calendar-chip > span {
    min-width: 0;
    overflow-wrap: anywhere;
  }
  .calendar-chip button {
    flex-shrink: 0;
  }
  .calendar-trigger {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
    width: 100%;
    text-align: left;
    cursor: pointer;
  }
  :global(.calendar-availability-popover) {
    width: var(--bits-popover-anchor-width);
    max-height: var(--bits-popover-content-available-height);
    overflow: auto;
    padding: 0;
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
