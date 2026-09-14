<script>
  import HostAvailability from '$lib/v2/components/HostAvailability.svelte';
  let unavailable = $state(true);
  import { resolve } from '$app/paths';
  import { enhance } from '$app/forms';
  import { dateKey } from '$lib/v2/calendar.js';
  /** @type {{hosts:any[],defaultHost?:string|null,selected:Date,onCreated:()=>void, action?:string, defaultAttendee?:{id:string,name:string,type:string}}} */
  let { hosts, defaultHost, selected, onCreated, action = '?/create', defaultAttendee } = $props();
  /** @type {HTMLDialogElement} */
  let dialog;
  let title = $state(''),
    host = $state(''),
    date = $state(''),
    start = $state('09:00'),
    end = $state('10:00'),
    notes = $state('');
  let busy = $state(false),
    error = $state('');
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
    use:enhance={({ cancel }) => {
      if (unavailable) {
        error = 'Select an available time for this host.';
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
        } else
          error =
            result.type === 'failure'
              ? String(result.data?.message || 'Could not schedule event.')
              : 'Could not schedule event. Please try again.';
      };
    }}
  >
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
      {#if !hosts.length}<p role="alert">No users available. Reload the page to try again.</p>{/if}
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
        <label>Start time *<input class="v2-input" type="time" required bind:value={start} /></label
        >
        <label>End time *<input class="v2-input" type="time" required bind:value={end} /></label>
      </div>
      <HostAvailability {host} {date} {start} {end} active={open} bind:blocked={unavailable} />
      <input type="hidden" name="starts_at" value={iso(start)} /><input
        type="hidden"
        name="ends_at"
        value={iso(end)}
      />
      <label
        >Internal notes<textarea
          class="v2-input"
          name="internal_notes"
          rows="4"
          maxlength="10000"
          bind:value={notes}></textarea></label
      >
    </fieldset>
    {#if error}<p class="v2-error" role="alert">{error}</p>{/if}
    <div class="actions">
      <button class="v2-btn" type="button" disabled={busy} onclick={() => dialog.close()}
        >Cancel</button
      ><button class="v2-btn v2-btn-primary" disabled={busy || !hosts.length || unavailable}
        >{busy ? 'Saving…' : 'Schedule event'}</button
      >
    </div>
  </form>
</dialog>

<style>
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
    width: min(480px, calc(100vw - 32px));
    max-height: 90vh;
    overflow: auto;
    padding: 24px;
    border: 1px solid var(--v2-line);
    border-radius: 12px;
    color: var(--v2-ink);
    background: var(--v2-bg, white);
  }
  dialog::backdrop {
    background: #0005;
  }
  h2 {
    margin: 0 0 20px;
    font-size: 20px;
  }
  fieldset {
    border: 0;
    padding: 0;
    display: grid;
    gap: 14px;
    min-width: 0;
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
    margin-top: 20px;
  }
</style>
