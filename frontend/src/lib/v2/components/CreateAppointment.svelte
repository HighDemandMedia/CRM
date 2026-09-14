<script>
  import WeekAvailability from '$lib/v2/components/WeekAvailability.svelte';
  let unavailable = $state(true);
  let conflicting = $state(false),
    availabilityRefresh = $state(0);
  import { resolve } from '$app/paths';
  import { enhance } from '$app/forms';
  const dealSources = [
    ['META', 'Meta'],
    ['GOOGLE', 'Google'],
    ['TIKTOK', 'TikTok'],
    ['ORGANIC', 'Organic'],
    ['CALL', 'Call'],
    ['CUSTOMER_REFERAL', 'Customer Referal'],
    ['EMPLOYER_REFERAL', 'Employer Referal'],
    ['WALK_IN', 'Walk In']
  ];
  let createDeal = $state(true),
    dealName = $state(''),
    dealSource = $state('');
  import { dateKey } from '$lib/v2/calendar.js';
  /** @type {{hosts:any[],defaultHost?:string|null,selected:Date,onCreated:()=>void, action?:string, defaultAttendee?:{id:string,name:string,type:string}}} */
  let { hosts, defaultHost, selected, onCreated, action = '?/create', defaultAttendee } = $props();
  /** @type {HTMLDialogElement} */
  let dialog;
  /** @type {HTMLDialogElement} */
  let overlapDialog;
  /** @type {((confirmed:boolean)=>void)|null} */
  let resolveOverlap = null;
  function confirmOverlap() {
    return new Promise((resolve) => {
      resolveOverlap = resolve;
      overlapDialog.showModal();
    });
  }
  function finishConfirmation(confirmed) {
    const complete = resolveOverlap;
    resolveOverlap = null;
    overlapDialog.close();
    complete?.(confirmed);
  }
  let title = $state(''),
    host = $state(''),
    date = $state(''),
    start = $state('09:00'),
    end = $state('10:00'),
    notes = $state('');
  let busy = $state(false),
    error = $state('');
  const durationMinutes = () => {
    const parts = (value) => {
      const [h, m] = value.split(':').map(Number);
      return h * 60 + m;
    };
    return parts(end) - parts(start);
  };
  function setDuration(value) {
    const [h, m] = start.split(':').map(Number);
    const finish = Math.min(1439, h * 60 + m + Number(value));
    end = `${String(Math.floor(finish / 60)).padStart(2, '0')}:${String(finish % 60).padStart(2, '0')}`;
  }
  const iso = (time) => {
    const d = new Date(`${date}T${time}`);
    return Number.isFinite(d.getTime()) ? d.toISOString() : '';
  };

  let attendee = $state(''),
    search = $state('');
  let showResults = $state(false);
  function chooseAttendee(kind, record) {
    attendee = `${kind}:${record.id}`;
    search = record.name;
    dealName = `${record.name} - Deal`;
    dealSource = '';
    showResults = false;
  }
  let open = $state(false),
    loadingAttendees = $state(false),
    attendeeError = $state('');
  let choices = $state(
    /** @type {{contacts:any[],companies:any[]}} */ ({ contacts: [], companies: [] })
  );
  $effect(() => {
    if (!open || !showResults) return;
    const term = search;
    const controller = new AbortController();
    loadingAttendees = true;
    choices = { contacts: [], companies: [] };
    attendeeError = '';
    const timer = setTimeout(async () => {
      try {
        const response = await fetch(
          `${resolve('/calendar/attendees')}?${new URLSearchParams({ search: term })}`,
          { signal: controller.signal }
        );
        if (!response.ok) throw new Error();
        const result = await response.json();
        if (!controller.signal.aborted) {
          choices = result;
          attendeeError = '';
        }
      } catch {
        if (!controller.signal.aborted)
          attendeeError = 'Could not load attendees. Try searching again.';
      } finally {
        if (!controller.signal.aborted) loadingAttendees = false;
      }
    }, 250);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  });
</script>

<button
  class="v2-btn v2-btn-primary"
  onclick={() => {
    date = dateKey(selected);
    if (defaultAttendee) {
      attendee = `${defaultAttendee.type}:${defaultAttendee.id}`;
      search = defaultAttendee.name;
    }
    host = defaultHost || hosts[0]?.id || '';
    error = '';
    createDeal = true;
    dealName = attendee ? `${search} - Deal` : '';
    dealSource = '';
    open = true;
    dialog.showModal();
  }}>Schedule event</button
>
<dialog
  onclose={() => {
    open = false;
    showResults = false;
  }}
  bind:this={dialog}
  oncancel={(event) => {
    if (busy) event.preventDefault();
  }}
>
  <h2>Schedule event</h2>
  <form
    method="POST"
    {action}
    use:enhance={async ({ cancel, formData }) => {
      if (unavailable) {
        error = 'Select an available time for this host.';
        cancel();
        return;
      }
      if (createDeal && !attendee) {
        error = 'Select an attendee to create a deal, or uncheck Create a deal.';
        cancel();
        return;
      }
      if (search.trim() && !attendee) {
        error = 'Select an attendee from the results or clear the search.';
        cancel();
        return;
      }
      if (end <= start) {
        error = 'End time must be after start time.';
        cancel();
        return;
      }
      formData.delete('allow_overlap');
      if (conflicting) {
        if (!(await confirmOverlap())) {
          cancel();
          return;
        }
        formData.set('allow_overlap', 'true');
      }
      busy = true;
      error = '';
      return async ({ result, update }) => {
        busy = false;
        if (result.type === 'success') {
          attendee = '';
          search = '';
          title = '';
          notes = '';
          dialog.close();
          await update({ reset: false });
          onCreated();
        } else {
          availabilityRefresh++;
          error =
            result.type === 'failure'
              ? String(result.data?.message || 'Could not schedule event.')
              : 'Could not schedule event. Please try again.';
        }
      };
    }}
  >
    <div class="schedule-body">
      <fieldset disabled={busy}>
        <label
          >Title *<input
            class="v2-input"
            name="title"
            required
            maxlength="255"
            bind:value={title}
          /></label
        >
        <label
          >Host *<select class="v2-input" name="host" required bind:value={host}
            ><option value="">Select user</option>{#each hosts as user}<option value={user.id}
                >{user.name}</option
              >{/each}</select
          ></label
        >
        {#if !hosts.length}<p role="alert">
            No users available. Reload the page to try again.
          </p>{/if}
        <div
          class="attendee-search"
          onfocusout={(event) => {
            if (!event.currentTarget.contains(/** @type {Node|null} */ (event.relatedTarget)))
              showResults = false;
          }}
        >
          <label
            >Attendee
            <input
              class="v2-input"
              type="search"
              placeholder="Search contacts or companies"
              aria-label="Search attendees"
              autocomplete="off"
              bind:value={search}
              onfocus={() => (showResults = true)}
              oninput={() => {
                attendee = '';
                showResults = true;
              }}
              onkeydown={(event) => {
                if (event.key === 'Escape') {
                  event.preventDefault();
                  showResults = false;
                }
              }}
            />
          </label>
          <input type="hidden" name="attendee" value={attendee} />
          {#if showResults}
            <div class="attendee-results" aria-label="Attendee search results">
              {#if loadingAttendees}<p class="v2-sub" role="status">Searching…</p>
              {:else if attendeeError}<p class="v2-error" role="alert">{attendeeError}</p>
              {:else}
                {#if choices.contacts.length}<h3>Contacts</h3>
                  {#each choices.contacts as contact}<button
                      type="button"
                      class="attendee-result"
                      onclick={() => chooseAttendee('contact', contact)}>{contact.name}</button
                    >{/each}
                {/if}
                {#if choices.companies.length}<h3>Companies</h3>
                  {#each choices.companies as company}<button
                      type="button"
                      class="attendee-result"
                      onclick={() => chooseAttendee('company', company)}>{company.name}</button
                    >{/each}
                {/if}
                {#if !choices.contacts.length && !choices.companies.length}<p
                    class="v2-sub"
                    role="status"
                  >
                    No results.
                  </p>{/if}
              {/if}
            </div>
          {/if}
        </div>
        <label>Date *<input class="v2-input" type="date" required bind:value={date} /></label>
        <div class="times">
          <label
            >Start time *<input class="v2-input" type="time" required bind:value={start} /></label
          >
          <label>End time *<input class="v2-input" type="time" required bind:value={end} /></label>
        </div>

        <input type="hidden" name="starts_at" value={iso(start)} /><input
          type="hidden"
          name="ends_at"
          value={iso(end)}
        />
        <label
          >Duration<select
            class="v2-input"
            value={durationMinutes()}
            onchange={(e) => setDuration(e.currentTarget.value)}
          >
            {#if ![15, 30, 45, 60, 90, 120].includes(durationMinutes())}<option
                value={durationMinutes()}>Custom</option
              >{/if}
            {#each [15, 30, 45, 60, 90, 120] as duration}<option value={duration}
                >{duration} min</option
              >{/each}
          </select></label
        >
        <label
          >Internal notes<textarea
            class="v2-input"
            name="internal_notes"
            rows="4"
            maxlength="10000"
            bind:value={notes}></textarea></label
        >
        <label class="create-deal-toggle"
          ><input type="checkbox" name="create_deal" bind:checked={createDeal} />Create a deal for
          this event</label
        >
        {#if createDeal}
          <label
            >Deal name<input
              class="v2-input"
              name="deal_name"
              maxlength="255"
              required
              bind:value={dealName}
              placeholder="Attendee name - Deal"
            /></label
          >
          <label
            >Deal source<select class="v2-input" name="deal_source" bind:value={dealSource}
              ><option value="">Use attendee source</option
              >{#each dealSources as [value, label]}<option {value}>{label}</option>{/each}</select
            ></label
          >
          <p class="deal-defaults">Owner: selected Host · Prospecting · Medium priority</p>
        {/if}
      </fieldset>
      {#if open}<WeekAvailability
          {host}
          bind:date
          bind:start
          bind:end
          bind:blocked={unavailable}
          bind:conflicting
          refresh={availabilityRefresh}
          disabled={busy}
        />{/if}
    </div>
    {#if error}<p class="v2-error" role="alert">{error}</p>{/if}
    <div class="actions">
      <span class="selection-summary">{date} · {start} – {end}</span>
      <button class="v2-btn" type="button" disabled={busy} onclick={() => dialog.close()}
        >Cancel</button
      ><button class="v2-btn v2-btn-primary" disabled={busy || !hosts.length || unavailable}
        >{busy ? 'Saving…' : 'Schedule event'}</button
      >
    </div>
  </form>
</dialog>

<dialog
  class="overlap-confirm"
  bind:this={overlapDialog}
  aria-labelledby="overlap-confirm-title"
  aria-describedby="overlap-confirm-description"
  oncancel={(event) => {
    event.preventDefault();
    finishConfirmation(false);
  }}
  onclose={() => {
    const complete = resolveOverlap;
    resolveOverlap = null;
    complete?.(false);
  }}
>
  <div class="warning-icon" aria-hidden="true">!</div>
  <h2 id="overlap-confirm-title">Schedule overlapping event?</h2>
  <p id="overlap-confirm-description">
    This host already has an event at this time. Do you want to proceed?
  </p>
  <div class="confirm-buttons">
    <button type="button" class="v2-btn" onclick={() => finishConfirmation(false)}>Go back</button>
    <button type="button" class="v2-btn v2-btn-primary" onclick={() => finishConfirmation(true)}
      >Proceed anyway</button
    >
  </div>
</dialog>

<style>
  .create-deal-toggle {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .create-deal-toggle input {
    width: 16px;
  }
  .deal-defaults {
    font-size: 12px;
    color: var(--v2-slate);
    margin: 0;
  }

  dialog.overlap-confirm {
    width: min(430px, calc(100vw - 32px));
    height: fit-content;
    padding: 24px;
    border-radius: 14px;
    box-shadow: 0 20px 60px #0003;
  }
  .overlap-confirm h2 {
    padding: 0;
    border: 0;
    margin: 14px 0 8px;
    font-size: 19px;
  }
  .overlap-confirm p {
    font-size: 14px;
    line-height: 1.6;
    color: var(--v2-slate);
    margin: 0;
  }
  .warning-icon {
    display: grid;
    place-items: center;
    width: 38px;
    height: 38px;
    border-radius: 50%;
    background: #fee2e2;
    color: #b91c1c;
    font-size: 22px;
    font-weight: 600;
  }
  .confirm-buttons {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    margin-top: 24px;
  }

  .attendee-search {
    position: relative;
  }
  .attendee-results {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    z-index: 5;
    max-height: 220px;
    overflow-y: auto;
    padding: 6px;
    border: 1px solid var(--v2-line);
    border-radius: 6px;
    background: var(--v2-bg, white);
    box-shadow: 0 6px 16px #0002;
  }
  .attendee-results h3 {
    font-size: 11px;
    color: var(--v2-slate);
    margin: 6px 8px;
  }
  .attendee-results p {
    margin: 8px;
  }
  .attendee-result {
    display: block;
    width: 100%;
    padding: 8px;
    text-align: left;
    background: transparent;
    border: 0;
    border-radius: 4px;
    color: var(--v2-ink);
    cursor: pointer;
    font: inherit;
  }
  .attendee-result:hover,
  .attendee-result:focus-visible {
    background: var(--v2-line-soft);
  }

  dialog {
    margin: auto;
    width: min(1240px, calc(100vw - 32px));
    height: min(820px, 94vh);
    box-sizing: border-box;
    max-height: 94vh;
    overflow: hidden;
    padding: 0;
    border: 1px solid var(--v2-line);
    border-radius: 12px;
    color: var(--v2-ink);
    background: var(--v2-bg, white);
  }
  dialog::backdrop {
    background: #0005;
  }
  h2 {
    margin: 0;
    padding: 18px 24px;
    border-bottom: 1px solid var(--v2-line);
    font-size: 20px;
  }
  fieldset {
    border: 0;
    padding: 0;
    display: grid;
    gap: 14px;
    min-width: 0;
    padding: 20px;
    overflow-y: auto;
    align-content: start;
    border-right: 1px solid var(--v2-line);
  }
  label {
    display: grid;
    gap: 6px;
    font-size: 13px;
  }
  input,
  select,
  textarea {
    min-width: 0;
    width: 100%;
  }
  .times {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }
  .actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    padding: 14px 20px;
    border-top: 1px solid var(--v2-line);
  }
  form {
    display: flex;
    flex-direction: column;
    height: calc(100% - 61px);
    min-height: 0;
  }
  .schedule-body {
    display: grid;
    grid-template-columns: 320px minmax(0, 1fr);
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }
  .selection-summary {
    margin-right: auto;
    align-self: center;
    font-size: 12px;
    color: var(--v2-slate);
  }
  .v2-error {
    margin: 0;
    padding: 8px 20px;
  }
  @media (max-width: 760px) {
    .schedule-body {
      display: flex;
      flex-direction: column;
      overflow-y: auto;
    }
    fieldset {
      flex-shrink: 0;
      overflow: visible;
      border-right: 0;
    }
    .schedule-body :global(.week-picker) {
      min-height: 460px;
      flex-shrink: 0;
    }
    .selection-summary {
      display: none;
    }
  }
</style>
