<script>
  import { resolve } from '$app/paths';
  import { untrack } from 'svelte';
  import LanguageSelect from '$lib/v2/components/LanguageSelect.svelte';
  import { enhance } from '$app/forms';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import { Mail, CalendarDays, Link2, UserRound } from '@lucide/svelte';

  /** @type {{data:any, form:any}} */
  let { data, form } = $props();
  let p = $derived(data.profile);
  let calendars = $state(/** @type {any[]} */ ([])),
    selectedCalendar = $state('primary'),
    calendarError = $state('');
  async function loadCalendars() {
    calendarError = '';
    try {
      const response = await fetch('/profile/google/calendars');
      const result = await response.json();
      if (!response.ok) throw new Error(result.error);
      calendars = result.calendars;
      selectedCalendar = result.selected;
    } catch (err) {
      calendarError = err instanceof Error ? err.message : 'Could not load calendars.';
    }
  }
  let name = $derived(`${p.user_details.first_name} ${p.user_details.last_name}`.trim());
  let activeTab = $state('info');
  const tabs = [
    { id: 'info', label: 'Profile info', icon: UserRound },
    { id: 'integrations', label: 'Integrations', icon: Link2 }
  ];
  $effect(() => {
    if (form?.scope === 'email' || form?.scope === 'google' || data.googleResult)
      activeTab = 'integrations';
  });
  function navigateTabs(event, index) {
    const keys = ['ArrowLeft', 'ArrowRight', 'Home', 'End'];
    if (!keys.includes(event.key)) return;
    event.preventDefault();
    const next =
      event.key === 'Home'
        ? 0
        : event.key === 'End'
          ? tabs.length - 1
          : (index + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
    activeTab = tabs[next].id;
    event.currentTarget.parentElement.querySelectorAll('[role="tab"]')[next].focus();
  }
  let editName = $state(untrack(() => name)),
    editPhone = $state(untrack(() => p.phone)),
    editLanguage = $state(untrack(() => p.language)),
    editTimezone = $state(untrack(() => p.timezone));
  let saving = $state(false);

  let dirty = $derived(
    editName !== name ||
      editPhone !== p.phone ||
      editLanguage !== p.language ||
      editTimezone !== p.timezone
  );
  $effect(() => {
    editName = name;
    editPhone = p.phone;
    editLanguage = p.language;
    editTimezone = p.timezone;
  });

  function resetDetails() {
    editName = name;
    editPhone = p.phone;
    editLanguage = p.language;
    editTimezone = p.timezone;
  }
  const onEdit = (/** @type {any} */ { formData }) => {
    for (const [key, previous] of Object.entries({
      name,
      phone: p.phone,
      language: p.language,
      timezone: p.timezone
    })) {
      if (formData.get(key) === previous) formData.delete(key);
    }
    saving = true;
    return async (/** @type {any} */ { result, update }) => {
      saving = false;
      await update({ reset: false });
    };
  };
</script>

<div class="profile-shell">
  <PageHeader title="Profile">
    {#snippet sub()}Your details, preferences and connected accounts{/snippet}
  </PageHeader>

  <div class="profile-tabs" role="tablist" aria-label="Profile sections">
    {#each tabs as tab, index}
      <button
        id={`profile-tab-${tab.id}`}
        role="tab"
        type="button"
        aria-selected={activeTab === tab.id}
        aria-controls={`profile-panel-${tab.id}`}
        tabindex={activeTab === tab.id ? 0 : -1}
        class:active={activeTab === tab.id}
        onclick={() => (activeTab = tab.id)}
        onkeydown={(event) => navigateTabs(event, index)}
      >
        <tab.icon size={16} /><span>{tab.label}</span>
      </button>
    {/each}
  </div>
  <div class="v2-scroll">
    <div class="profile-layout">
      <div
        id="profile-panel-info"
        role="tabpanel"
        aria-labelledby="profile-tab-info"
        hidden={activeTab !== 'info'}
        tabindex="0"
        class="profile-panel personal"
      >
        <div class="section-heading">
          <div>
            <h2>Personal information</h2>
            <p class="section-description">Manage your details and personal preferences.</p>
          </div>
        </div>
        <form class="details-form" method="POST" action="?/edit" use:enhance={onEdit}>
          <fieldset disabled={saving}>
            <div class="settings-group">
              <label
                >Full name<input
                  class="v2-input"
                  name="name"
                  bind:value={editName}
                  maxlength="255"
                  autocomplete="name"
                /></label
              >
              <label
                >Email<input
                  class="v2-input"
                  type="email"
                  value={p.user_details.email}
                  readonly
                  aria-describedby="email-help"
                /></label
              >
              <p id="email-help" class="help">Your sign-in email.</p>
              <label
                >Phone<input
                  class="v2-input"
                  name="phone"
                  bind:value={editPhone}
                  maxlength="20"
                  type="tel"
                  autocomplete="tel"
                /></label
              >
            </div>
            <div class="settings-group">
              <h3>Regional preferences</h3>
              <LanguageSelect bind:value={editLanguage} />
              <label
                >Time zone<select class="v2-input" name="timezone" bind:value={editTimezone}>
                  <option value=""
                    >Organization default · {p.organization_timezone.replaceAll('_', ' ')}</option
                  >
                  {#each data.timezones as zone}<option value={zone.name}>{zone.label}</option
                    >{/each}
                </select></label
              >
            </div>
            {#if p.teams.length}<div class="team-summary">
                <span>Teams</span><strong>{p.teams.join(', ')}</strong>
              </div>{/if}
          </fieldset>
          {#if !form?.scope && form?.message}<p class="feedback failure" role="alert">
              {form.message}
            </p>{/if}
          {#if !form?.scope && form?.saved && !dirty}<p class="feedback" role="status">
              Profile saved.
            </p>{/if}
          <div class="form-actions detail-actions">
            <button class="v2-btn v2-btn-primary" disabled={saving || !dirty}
              >{saving ? 'Saving…' : 'Save changes'}</button
            >
            {#if dirty}<button class="v2-btn" type="button" disabled={saving} onclick={resetDetails}
                >Cancel</button
              >{/if}
          </div>
        </form>
        <form class="details-form" method="POST" action="?/password" use:enhance>
          <fieldset>
            <h3>{data.hasPassword ? 'Change password' : 'Set your password'}</h3>
            {#if data.hasPassword}<label
                >Current password<input
                  class="v2-input"
                  type="password"
                  name="current_password"
                  required
                  autocomplete="current-password"
                  maxlength="128"
                /></label
              >{/if}
            <label
              >New password<input
                class="v2-input"
                type="password"
                name="password"
                required
                minlength="10"
                maxlength="128"
                autocomplete="new-password"
              /></label
            >
            <label
              >Confirm password<input
                class="v2-input"
                type="password"
                name="confirm_password"
                required
                minlength="10"
                maxlength="128"
                autocomplete="new-password"
              /></label
            >
          </fieldset>
          {#if form?.scope === 'password'}<p
              class="feedback"
              class:failure={form.message}
              role="status"
            >
              {form.message || 'Password saved.'}
            </p>{/if}
          <div class="form-actions">
            <button class="v2-btn v2-btn-primary">Save password</button>
          </div>
        </form>
      </div>
      <div
        id="profile-panel-integrations"
        role="tabpanel"
        aria-labelledby="profile-tab-integrations"
        hidden={activeTab !== 'integrations'}
        tabindex="0"
        class="profile-panel"
      >
        <div class="section-heading">
          <h2 id="integration-title"><Link2 size={17} />Connected accounts</h2>
          <span class="subtle-badge">Per user</span>
        </div>
        <p class="section-description">Manage your email and calendar connections.</p>
        {#if data.googleResult}<p class="feedback" role="status">
            {data.googleResult === 'settings'
              ? 'Manage your Google connections below.'
              : data.googleResult === 'connected'
                ? 'Google connected. The first synchronization is running.'
                : data.googleResult === 'cancelled'
                  ? 'Connection cancelled or expired. Try connecting again.'
                  : 'Could not connect Google. Check the configuration and required permissions, then try again.'}
          </p>{/if}
        {#if form?.scope === 'google'}<p
            class="feedback"
            class:failure={form.message}
            role="status"
          >
            {form.message || form.googleMessage}
          </p>{/if}
        {#each [{ key: 'gmail', service: 'gmail', title: 'Gmail' }, { key: 'google_calendar', service: 'calendar', title: 'Google Calendar' }] as item}
          {@const connection = p.integrations?.[item.key]}
          <div class="integration">
            <div class="integration-heading">
              <div class="service-icon">
                {#if item.service === 'gmail'}<Mail size={21} />{:else}<CalendarDays
                    size={21}
                  />{/if}
              </div>
              <div>
                <h3>{item.title}</h3>
                <p>{connection?.email || 'No account connected'}</p>
              </div>
              <span class="status-badge"
                >{connection?.status === 'connected'
                  ? 'Connected'
                  : connection?.status === 'reconnect'
                    ? 'Reconnect required'
                    : 'Not connected'}</span
              >
            </div>
            <p class="help">
              {item.service === 'gmail'
                ? 'Sent and received emails are matched to your contacts by email address. Only you can see your connected mailbox activity, including the message text. Initial import covers the last 90 days; attachments are not imported.'
                : 'Events synchronize in both directions. Your hosted CRM appointments and their meeting notes appear in Google Calendar. Google changes update the linked appointment. No invitation emails are sent by this sync.'}
            </p>
            {#if connection?.last_sync}<p class="help">
                Last sync: {new Date(connection.last_sync).toLocaleString()}
              </p>{/if}
            {#if item.service === 'calendar' && connection?.status === 'connected'}<p class="help">
                Calendar: {connection.calendar}. Sync includes the previous 90 days and the next 12
                months.
              </p>{/if}
            {#if connection?.error}<p class="feedback failure" role="status">
                {connection.error}
              </p>{/if}
            {#if !connection?.configured}<p class="setup-note">
                The CRM administrator needs to configure Google connections before you can connect.
              </p>{/if}
            <div class="integration-actions">
              <form method="POST" action="?/googleConnect">
                <input type="hidden" name="service" value={item.service} /><button
                  class="v2-btn v2-btn-primary v2-btn-sm"
                  disabled={!connection?.configured}
                  >{connection?.email ? 'Reconnect' : `Connect ${item.title}`}</button
                >
              </form>
              {#if connection?.status === 'connected'}<form
                  method="POST"
                  action="?/googleManage"
                  use:enhance
                >
                  <input type="hidden" name="service" value={item.service} /><button
                    class="v2-btn v2-btn-sm"
                    name="operation"
                    value="sync">Sync now</button
                  >
                </form>{/if}
              {#if connection?.email}<form method="POST" action="?/googleManage" use:enhance>
                  <input type="hidden" name="service" value={item.service} /><button
                    class="v2-btn v2-btn-sm"
                    name="operation"
                    value="disconnect">Disconnect</button
                  >
                </form>{/if}
              {#if item.service === 'calendar' && connection?.status === 'connected'}<button
                  class="v2-btn v2-btn-sm"
                  onclick={loadCalendars}>Choose calendar</button
                >{/if}
            </div>
            {#if item.service === 'calendar' && calendars.length}<form
                method="POST"
                action="?/googleManage"
                use:enhance
              >
                <input type="hidden" name="service" value="calendar" /><input
                  type="hidden"
                  name="operation"
                  value="calendar"
                /><label
                  >Calendar<select class="v2-input" name="calendar_id" bind:value={selectedCalendar}
                    >{#each calendars as calendar}<option value={calendar.id}
                        >{calendar.name}{calendar.writable ? '' : ' (read only)'}</option
                      >{/each}</select
                  ></label
                ><button class="v2-btn v2-btn-sm">Use this calendar</button>
              </form>{/if}
            {#if item.service === 'calendar' && calendarError}<p class="feedback failure">
                {calendarError}
              </p>{/if}
          </div>
        {/each}
      </div>
    </div>
  </div>
</div>

<style>
  .profile-shell {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    min-width: 0;
    background: var(--v2-bg, #fff);
  }
  .profile-shell > .v2-scroll {
    flex: 1;
    min-height: 0;
  }
  .settings-group {
    display: grid;
    gap: 20px;
  }
  .settings-group + .settings-group {
    padding-top: 26px;
    border-top: 1px solid var(--v2-line-soft);
  }
  .settings-group h3 {
    margin-bottom: 2px;
    font-size: 14px;
  }
  .settings-group .help {
    margin-top: -14px;
  }
  .details-form label {
    font-weight: 500;
    gap: 9px;
    font-size: 13px;
  }
  .details-form :global(select),
  .details-form :global(input) {
    min-height: 42px;
    background: var(--v2-bg, #fff);
    border-radius: 7px;
  }
  .details-form input[readonly] {
    background: var(--v2-line-soft);
    color: var(--v2-slate);
  }
  .team-summary {
    display: flex;
    gap: 12px;
    font-size: 12px;
    color: var(--v2-slate);
  }
  .team-summary strong {
    font-weight: 500;
    color: var(--v2-ink);
  }
  .detail-actions {
    margin-top: 28px;
    padding-top: 20px;
    border-top: 1px solid var(--v2-line-soft);
  }
  .section-heading .section-description {
    margin: 8px 0 0;
  }
  .integration,
  .setup-note {
    max-width: 680px;
  }

  .profile-tabs {
    display: flex;
    gap: 24px;
    padding: 0 24px;
    border-bottom: 1px solid var(--v2-line);
    flex-shrink: 0;
    overflow-x: auto;
  }
  .profile-tabs button {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 16px 0 13px;
    border: 0;
    border-bottom: 2px solid transparent;
    background: transparent;
    color: var(--v2-slate);
    font: inherit;
    font-size: 13px;
    white-space: nowrap;
    cursor: pointer;
  }
  .profile-tabs button.active {
    color: var(--v2-ink);
    border-bottom-color: var(--v2-ink);
    font-weight: 600;
  }
  .profile-tabs button:hover {
    color: var(--v2-ink);
  }
  .profile-tabs button:focus-visible {
    outline: 2px solid var(--v2-slate);
    outline-offset: -3px;
    border-radius: 4px;
  }
  .profile-layout {
    padding: 30px 32px;
    max-width: 1000px;
    width: 100%;
    box-sizing: border-box;
  }
  .profile-panel[hidden] {
    display: none;
  }
  .profile-panel:focus-visible {
    outline: 2px solid var(--v2-line);
    outline-offset: 3px;
  }

  .section-heading {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    margin-bottom: 18px;
  }
  h2 {
    display: flex;
    gap: 8px;
    align-items: center;
    margin: 0;
    font-size: 16px;
    font-weight: 600;
  }
  h3 {
    font-size: 14px;
    margin: 0;
    font-weight: 600;
  }
  .help {
    font-size: 11px;
    color: var(--v2-slate);
    line-height: 1.5;
    margin: 8px 0 0;
    overflow-wrap: anywhere;
  }
  label {
    display: grid;
    gap: 7px;
    font-size: 12px;
  }
  .details-form {
    max-width: 640px;
    margin-top: 26px;
  }
  .details-form fieldset {
    display: grid;
    gap: 26px;
  }
  fieldset {
    margin: 0;
    padding: 0;
    border: 0;
    min-width: 0;
  }
  .v2-input {
    width: 100%;
    min-width: 0;
  }
  .form-actions {
    display: flex;
    gap: 8px;
    margin-top: 18px;
  }
  .section-description {
    color: var(--v2-slate);
    font-size: 12px;
    line-height: 1.6;
    margin: 0 0 16px;
  }
  .integration + .integration {
    border-top: 1px solid var(--v2-line);
    padding-top: 22px;
    margin-top: 22px;
  }
  .integration-heading {
    display: flex;
    gap: 12px;
    align-items: center;
    margin-bottom: 18px;
    flex-wrap: wrap;
  }
  .integration-heading > div:nth-child(2) {
    flex: 1;
    min-width: 120px;
  }
  .integration-heading p {
    color: var(--v2-slate);
    font-size: 12px;
    margin: 4px 0 0;
  }
  .service-icon {
    display: grid;
    place-items: center;
    width: 40px;
    height: 40px;
    background: var(--v2-line-soft);
    border-radius: 10px;
    color: var(--v2-slate);
  }
  .status-badge,
  .subtle-badge {
    font-size: 10px;
    padding: 4px 8px;
    background: var(--v2-line-soft);
    color: var(--v2-slate);
    border-radius: 6px;
    white-space: nowrap;
  }
  .integration-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 12px;
  }
  .setup-note {
    margin: 20px 0 0;
    padding-top: 16px;
    border-top: 1px solid var(--v2-line);
    font-size: 11px;
    color: var(--v2-slate);
    line-height: 1.6;
  }
  .feedback {
    color: var(--v2-moss);
    font-size: 12px;
    margin: 12px 0 0;
  }
  .feedback.failure {
    color: var(--v2-rust);
  }

  @media (max-width: 600px) {
    .profile-layout {
      padding: 14px;
    }
    .profile-tabs {
      gap: 16px;
      padding: 0 14px;
    }
    .profile-tabs button {
      font-size: 12px;
      gap: 5px;
    }
  }
</style>
