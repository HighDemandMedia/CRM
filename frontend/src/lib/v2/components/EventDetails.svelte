<script>
  import { useI18n } from '$lib/i18n/context.js';
  const { ui, locale } = useI18n();

  import HostAvailability from '$lib/v2/components/HostAvailability.svelte';
  let unavailable = $state(true);
  import { deserialize } from '$app/forms';
  import { dateKey } from '$lib/v2/calendar.js';
  /** @type {{onChanged?:()=>void}} */
  let { onChanged = () => {} } = $props();
  let mode = $state('details'),
    busy = $state(false),
    failure = $state('');
  let editTitle = $state(''),
    editNotes = $state('');
  let date = $state(''),
    start = $state(''),
    end = $state('');
  import { tick } from 'svelte';
  import { resolve } from '$app/paths';
  import {
    CalendarDays,
    Clock3,
    UserRound,
    Users,
    Phone,
    Mail,
    Languages,
    FileText,
    X,
    ArrowUpRight
  } from '@lucide/svelte';
  let event = $state(/** @type {any} */ (null));
  /** @type {HTMLDivElement} */
  let panel;
  let left = $state(16),
    top = $state(16);
  export function close() {
    if (panel?.matches(':popover-open')) panel.hidePopover();
  }
  export async function open(record, anchor) {
    if (busy) return;
    event = record;
    editTitle = record.title || '';
    editNotes = record.notes || '';
    mode = 'details';
    failure = '';
    const first = new Date(record.start),
      last = new Date(record.end || record.start);
    const localTime = (d) =>
      `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
    date = dateKey(first);
    start = localTime(first);
    end = localTime(last);
    await tick();
    const rect = anchor.getBoundingClientRect();
    const width = Math.min(410, window.innerWidth - 32);
    left =
      rect.right + 14 + width <= window.innerWidth - 16
        ? rect.right + 14
        : rect.left - 14 - width >= 16
          ? rect.left - 14 - width
          : Math.max(16, (window.innerWidth - width) / 2);
    top = 16;
    panel.showPopover();
    await tick();
    top = Math.max(16, Math.min(rect.top - 12, window.innerHeight - panel.offsetHeight - 16));
  }
  const time = (value) =>
    new Date(value).toLocaleTimeString(locale(), { hour: 'numeric', minute: '2-digit' });

  async function manage(operation) {
    if (busy) return;
    if (operation === 'reschedule' && event.type === 'appointment' && unavailable) {
      failure = 'Select an available time for this host.';
      return;
    }
    failure = '';
    if (
      operation === 'reschedule' &&
      (!date ||
        !start ||
        (['appointment', 'google'].includes(event.type) && (!end || end <= start)))
    ) {
      failure = 'End time must be after start time.';
      return;
    }
    const body = new FormData();
    body.set('event_id', event.id);
    body.set('operation', operation);
    if (operation === 'details') {
      body.set('title', editTitle);
      body.set('internal_notes', editNotes);
    }
    if (operation === 'reschedule') {
      const startsAt = new Date(`${date}T${start}`),
        endsAt = new Date(`${date}T${end || start}`);
      if (!Number.isFinite(startsAt.getTime()) || !Number.isFinite(endsAt.getTime())) {
        failure = 'Choose a valid date and time.';
        return;
      }
      body.set('starts_at', startsAt.toISOString());
      body.set('ends_at', endsAt.toISOString());
    }
    busy = true;
    try {
      const response = await fetch('?/manage', {
        method: 'POST',
        body,
        headers: { 'x-sveltekit-action': 'true' }
      });
      const result = deserialize(await response.text());
      if (result.type !== 'success') {
        failure =
          result.type === 'failure'
            ? String(result.data?.message || 'Could not update event.')
            : 'Could not update event.';
        return;
      }
      close();
      onChanged();
    } catch {
      failure = 'Could not update event. Please try again.';
    } finally {
      busy = false;
    }
  }
</script>

<svelte:window onresize={close} />
<div
  bind:this={panel}
  popover="auto"
  role="dialog"
  aria-labelledby="event-popup-title"
  class="event-popup"
  style={`left:${left}px;top:${top}px;max-height:calc(100dvh - ${top + 16}px)`}
>
  {#if event}
    {@const attendee =
      event.attendee ??
      (event.recordId ? { id: event.recordId, type: event.type, name: event.title } : null)}
    {@const attendees = event.attendees?.length ? event.attendees : attendee ? [attendee] : []}
    <div class="popup-heading">
      <div class="calendar-icon"><CalendarDays size={21} /></div>
      <div class="heading-text">
        <span class="eyebrow">{ui('EVENT DETAILS')}</span>
        <h2 id="event-popup-title">{event.title}</h2>
      </div>
      <button class="close" type="button" aria-label={ui('Close event details')} onclick={close}
        ><X size={19} /></button
      >
    </div>
    <div class="schedule">
      <Clock3 size={17} />
      <div>
        <strong
          >{new Date(event.start).toLocaleDateString(locale(), {
            weekday: 'long',
            month: 'long',
            day: 'numeric'
          })}</strong
        ><span
          >{#if event.allDay}{ui('All day')}{:else}{time(event.start)}{#if event.end}
              – {time(event.end)}{/if}{/if}</span
        >
      </div>
    </div>
    <div class="people">
      {#if event.host}<div class="person-row">
          <UserRound size={18} />
          <div><span class="field-label">{ui('Host')}</span><strong>{event.host}</strong></div>
        </div>{/if}
      {#each attendees as person}
        <div class="person-row">
          <Users size={18} />
          <div>
            <span class="field-label"
              >{person.type === 'user'
                ? ui('User')
                : person.type === 'company'
                  ? ui('Company')
                  : ui('Contact')}
              {ui('· Attendee')}</span
            >
            {#if person.type === 'user'}<strong>{person.name}</strong>
            {:else}<a
                class="attendee-name"
                onclick={close}
                data-sveltekit-reload
                href={person.type === 'company'
                  ? resolve(`/accounts/${person.id}`)
                  : resolve(`/contacts/${person.id}`)}>{person.name}<ArrowUpRight size={15} /></a
              >{/if}
          </div>
        </div>
        {#if person.language || person.phone || person.email}<div class="contact-info">
            {#if person.language}<div>
                <Languages size={15} /><span>{person.language}</span>
              </div>{/if}
            {#if person.phone}<div><Phone size={15} /><span>{person.phone}</span></div>{/if}
            {#if person.email}<div><Mail size={15} /><span>{person.email}</span></div>{/if}
          </div>{/if}
      {/each}
    </div>
    {#if ['appointment', 'google'].includes(event.type)}<section class="notes">
        <h3><FileText size={16} />{ui('Meeting notes')}</h3>
        <p>{event.notes || ui('No notes.')}</p>
      </section>{/if}
    {#if event.type === 'google' && event.href}<a
        class="v2-btn"
        href={event.href}
        target="_blank"
        rel="noopener noreferrer">{ui('Open in Google Calendar')}</a
      >{/if}
    {#if event.canManage !== false}<div class="event-actions">
        {#if mode === 'details'}
          {#if ['appointment', 'google'].includes(event.type) && event.canReschedule !== false}<button
              class="v2-btn"
              onclick={() => (mode = 'edit-details')}>{ui('Edit details')}</button
            >{/if}
          {#if event.canReschedule !== false}<button
              class="v2-btn"
              onclick={() => {
                mode = 'reschedule';
                failure = '';
              }}>{ui('Reschedule')}</button
            >{/if}
          {#if event.canCancel !== false}<button
              class="v2-btn danger"
              onclick={() => {
                mode = 'cancel';
                failure = '';
              }}>{ui('Cancel event')}</button
            >{/if}
        {:else if mode === 'edit-details'}
          <form
            onsubmit={(submit) => {
              submit.preventDefault();
              void manage('details');
            }}
          >
            <fieldset disabled={busy}>
              <label
                >{ui('Title')}<input
                  class="v2-input"
                  required
                  maxlength="255"
                  bind:value={editTitle}
                /></label
              >
              <label
                >{ui('Meeting notes')}<textarea
                  class="v2-input"
                  rows="5"
                  maxlength="10000"
                  bind:value={editNotes}></textarea></label
              >
            </fieldset>
            <p class="v2-sub">
              {ui('Meeting notes are shared as the Google Calendar description when connected.')}
            </p>
            <button class="v2-btn" type="button" onclick={() => (mode = 'details')}
              >{ui('Cancel')}</button
            >
            <button class="v2-btn v2-btn-primary" disabled={busy}
              >{busy ? ui('Saving…') : ui('Save changes')}</button
            >
          </form>
        {:else if mode === 'reschedule'}
          <form
            onsubmit={(submit) => {
              submit.preventDefault();
              void manage('reschedule');
            }}
          >
            <h3>{ui('Reschedule event')}</h3>
            <fieldset disabled={busy}>
              <label
                >{ui('Date')}<input
                  class="v2-input"
                  type="date"
                  required
                  bind:value={date}
                /></label
              >
              <div class="time-fields">
                <label
                  >{ui('Start time')}<input
                    class="v2-input"
                    type="time"
                    required
                    bind:value={start}
                  /></label
                >
                {#if ['appointment', 'google'].includes(event.type)}<label
                    >{ui('End time')}<input
                      class="v2-input"
                      type="time"
                      required
                      bind:value={end}
                    /></label
                  >{/if}
              </div>
            </fieldset>
            {#if event.type === 'appointment'}<HostAvailability
                host={event.hostId}
                {date}
                {start}
                {end}
                exclude={event.id.split(':')[1]}
                bind:blocked={unavailable}
              />{/if}
            <div class="action-buttons">
              <button
                type="button"
                class="v2-btn"
                disabled={busy}
                onclick={() => {
                  mode = 'details';
                  failure = '';
                }}>{ui('Back')}</button
              ><button
                class="v2-btn v2-btn-primary"
                disabled={busy || (event.type === 'appointment' && unavailable)}
                >{busy ? ui('Saving…') : ui('Save changes')}</button
              >
            </div>
          </form>
        {:else}
          <div>
            <h3>{ui('Cancel this event?')}</h3>
            <p class="cancel-copy">{ui('It will be removed from the calendar.')}</p>
            <div class="action-buttons">
              <button
                class="v2-btn"
                disabled={busy}
                onclick={() => {
                  mode = 'details';
                  failure = '';
                }}>{ui('Keep event')}</button
              ><button class="v2-btn danger" disabled={busy} onclick={() => manage('cancel')}
                >{busy ? ui('Cancelling…') : ui('Yes, cancel event')}</button
              >
            </div>
          </div>
        {/if}
        {#if failure}<p class="v2-error" role="alert">{ui(failure)}</p>{/if}
      </div>{/if}
  {/if}
</div>

<style>
  .event-actions {
    display: flex;
    flex-wrap: wrap;
    gap: var(--crm-space-2);
    margin-top: var(--crm-space-5);
    padding-top: var(--crm-space-4);
    border-top: 1px solid var(--v2-line);
  }
  .event-actions form,
  .event-actions > div {
    width: 100%;
  }
  .event-actions fieldset {
    border: 0;
    padding: 0;
    display: grid;
    gap: var(--crm-space-3);
    min-width: 0;
  }
  .event-actions label {
    display: grid;
    gap: 5px;
    font-size: var(--crm-text-xs);
  }
  .event-actions input {
    width: 100%;
    min-width: 0;
  }
  .time-fields {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
  }
  .action-buttons {
    display: flex;
    justify-content: flex-end;
    gap: var(--crm-space-2);
    margin-top: 14px;
  }
  .danger {
    color: var(--crm-danger);
  }
  .cancel-copy {
    font-size: var(--crm-text-sm);
    line-height: 1.5;
  }

  .event-popup {
    position: fixed;
    inset: auto;
    margin: 0;
    width: min(410px, calc(100vw - 32px));
    max-height: calc(100dvh - 32px);
    overflow: auto;
    box-sizing: border-box;
    padding: var(--crm-space-6);
    border: 1px solid var(--v2-line, var(--crm-border));
    border-radius: var(--crm-radius-xl);
    background: var(--v2-bg, var(--crm-surface));
    color: var(--v2-ink, var(--crm-text));
    box-shadow: var(--crm-shadow-lg);
  }
  .event-popup:popover-open {
    animation: appear 160ms ease-out;
  }
  .event-popup::backdrop {
    background: transparent;
  }
  .popup-heading {
    display: flex;
    gap: var(--crm-space-3);
    align-items: flex-start;
  }
  .calendar-icon {
    display: grid;
    place-items: center;
    width: 42px;
    height: 42px;
    flex: none;
    border-radius: var(--crm-radius-lg);
    color: var(--crm-info);
    background: var(--crm-info-bg);
  }
  .heading-text {
    flex: 1;
    min-width: 0;
  }
  .eyebrow {
    color: var(--v2-slate);
    font-size: var(--crm-text-xs);
    font-weight: 600;
    letter-spacing: 1px;
  }
  h2 {
    margin: var(--crm-space-1) 0 0;
    font-size: var(--crm-text-lg);
    line-height: 1.35;
    font-weight: 650;
    overflow-wrap: anywhere;
  }
  .close {
    border: 0;
    background: transparent;
    color: var(--v2-slate);
    padding: 5px;
    border-radius: var(--crm-radius-sm);
    cursor: pointer;
    margin: -8px -8px 0 0;
  }
  .close:hover {
    background: var(--v2-line-soft);
  }
  .schedule {
    display: flex;
    gap: 11px;
    margin: var(--crm-space-6) 0;
    padding: 14px;
    background: var(--v2-line-soft, var(--crm-canvas));
    border-radius: var(--crm-radius-md);
    color: var(--v2-slate);
  }
  .schedule div {
    display: grid;
    gap: 5px;
    font-size: var(--crm-text-sm);
  }
  .schedule strong {
    color: var(--v2-ink);
    font-weight: 500;
  }
  .people {
    display: grid;
    gap: 18px;
  }
  .person-row {
    display: flex;
    align-items: flex-start;
    gap: var(--crm-space-3);
    color: var(--v2-slate);
  }
  .person-row div {
    min-width: 0;
    display: grid;
    gap: 5px;
  }
  .field-label {
    font-size: var(--crm-text-xs);
  }
  .person-row strong {
    font-size: var(--crm-text-sm);
    font-weight: 500;
    color: var(--v2-ink);
    overflow-wrap: anywhere;
  }
  .attendee-name {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: var(--crm-text-sm);
    font-weight: 600;
    color: var(--crm-info);
    text-decoration: none;
    overflow-wrap: anywhere;
  }
  .attendee-name:hover {
    text-decoration: underline;
  }
  .contact-info {
    display: grid;
    gap: 10px;
    padding-left: 30px;
    color: var(--v2-slate);
    font-size: var(--crm-text-xs);
  }
  .contact-info div {
    display: flex;
    gap: 9px;
    align-items: center;
    min-width: 0;
    overflow-wrap: anywhere;
  }
  .contact-info span {
    min-width: 0;
  }
  .notes {
    margin-top: var(--crm-space-6);
    padding-top: 18px;
    border-top: 1px solid var(--v2-line);
  }
  h3 {
    display: flex;
    align-items: center;
    gap: 9px;
    font-size: var(--crm-text-xs);
    font-weight: 500;
    margin: 0 0 10px;
    color: var(--v2-slate);
  }
  .notes p {
    margin: 0;
    font-size: var(--crm-text-sm);
    line-height: 1.65;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }
  @keyframes appear {
    from {
      opacity: 0;
      transform: translateY(5px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .event-popup:popover-open {
      animation: none;
    }
  }
</style>
