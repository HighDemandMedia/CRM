<script>
  import ErrorNotice from '$lib/components/ErrorNotice.svelte';
  import { googleErrorMessage, googleCallbackMessage } from '$lib/utils/google-feedback.js';
  import { useI18n } from '$lib/i18n/context.js';
  const { ui, locale } = useI18n();

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
  let loadingCalendars = $state(false);
  let googlePending = $state(false);
  let googleActionError = $state('');
  const onGoogleManage = () => {
    googlePending = true;
    googleActionError = '';
    return async ({ result, update }) => {
      try {
        if (result.type === 'error') {
          googleActionError = googleErrorMessage(result.error);
          return;
        }
        await update({ reset: false });
      } catch {
        googleActionError = googleErrorMessage(null);
      } finally {
        googlePending = false;
      }
    };
  };
  async function loadCalendars() {
    calendarError = '';
    loadingCalendars = true;
    try {
      const response = await fetch('/profile/google/calendars');
      const result = await response.json();
      if (!response.ok) throw new Error(googleErrorMessage(result.error));
      if (!Array.isArray(result.calendars)) throw new Error('Invalid calendar response');
      calendars = result.calendars;
      selectedCalendar = result.selected;
    } catch (err) {
      calendarError = googleErrorMessage(err);
    } finally {
      loadingCalendars = false;
    }
  }
  let name = $derived(`${p.user_details.first_name} ${p.user_details.last_name}`.trim());
  let activeTab = $state('info');
  const tabs = [
    { id: 'info', label: 'Profile info', icon: UserRound },
    { id: 'integrations', label: 'Integrations', icon: Link2 }
  ];
  $effect(() => {
    if (
      form?.scope === 'email' ||
      form?.scope === 'google' ||
      data.googleResult ||
      data.integrationTab
    )
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
    editUiLanguage = $state(untrack(() => p.ui_language)),
    editLanguage = $state(untrack(() => p.language)),
    editTimezone = $state(untrack(() => p.timezone));
  let saving = $state(false);

  let dirty = $derived(
    editName !== name ||
      editPhone !== p.phone ||
      editUiLanguage !== p.ui_language ||
      editLanguage !== p.language ||
      editTimezone !== p.timezone
  );
  $effect(() => {
    editName = name;
    editPhone = p.phone;
    editUiLanguage = p.ui_language;
    editLanguage = p.language;
    editTimezone = p.timezone;
  });

  function resetDetails() {
    editName = name;
    editPhone = p.phone;
    editUiLanguage = p.ui_language;
    editLanguage = p.language;
    editTimezone = p.timezone;
  }
  const onEdit = (/** @type {any} */ { formData }) => {
    for (const [key, previous] of Object.entries({
      name,
      phone: p.phone,
      ui_language: p.ui_language,
      language: p.language,
      timezone: p.timezone
    })) {
      if (!data.onboarding && formData.get(key) === previous) formData.delete(key);
    }
    saving = true;
    return async (/** @type {any} */ { result, update }) => {
      saving = false;
      await update({ reset: false });
    };
  };
</script>

<div class="profile-shell">
  <PageHeader title={data.onboarding ? ui('Complete your profile') : ui('Profile')}>
    {#snippet sub()}{data.onboarding
        ? ui('Confirm your name, language and time zone before you start.')
        : ui('Your details, preferences and connected accounts')}{/snippet}
  </PageHeader>

  {#if !data.onboarding}<div
      class="profile-tabs"
      role="tablist"
      aria-label={ui('Profile sections')}
    >
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
          <tab.icon size={16} /><span>{ui(tab.label)}</span>
        </button>
      {/each}
    </div>{/if}
  <div class="v2-scroll">
    <div class="profile-layout">
      <div
        id="profile-panel-info"
        role="tabpanel"
        aria-labelledby={data.onboarding ? 'personal-information-title' : 'profile-tab-info'}
        hidden={activeTab !== 'info'}
        tabindex="0"
        class="profile-panel personal"
      >
        <div class="section-heading">
          <div>
            <h2 id="personal-information-title">{ui('Personal information')}</h2>
            <p class="section-description">{ui('Manage your details and personal preferences.')}</p>
          </div>
        </div>
        <form class="details-form" method="POST" action="?/edit" use:enhance={onEdit}>
          {#if data.onboarding}<input type="hidden" name="complete_setup" value="1" />{/if}
          <fieldset disabled={saving}>
            <div class="settings-group">
              <label
                >{ui('Full name')}<input
                  class="v2-input"
                  name="name"
                  required={data.onboarding}
                  bind:value={editName}
                  maxlength="255"
                  autocomplete="name"
                /></label
              >
              <label
                >{ui('Email')}<input
                  class="v2-input"
                  type="email"
                  value={p.user_details.email}
                  readonly
                  aria-describedby="email-help"
                /></label
              >
              <p id="email-help" class="help">{ui('Your sign-in email.')}</p>
              <label
                >{ui('Phone')}<input
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
              <h3>{ui('Regional preferences')}</h3>
              <label
                >{ui('CRM language')}
                <select class="v2-input" name="ui_language" bind:value={editUiLanguage}>
                  <option value="en">English</option><option value="es">Español</option>
                </select>
              </label>
              <p class="help">
                {ui('Only changes your interface. Applies across your organizations and devices.')}
              </p>
              <LanguageSelect bind:value={editLanguage} />
              <label
                >{ui('Time zone')}<select
                  class="v2-input"
                  name="timezone"
                  bind:value={editTimezone}
                >
                  <option value=""
                    >{ui('Organization default ·')}
                    {p.organization_timezone.replaceAll('_', ' ')}</option
                  >
                  {#each data.timezones as zone}<option value={zone.name}>{zone.label}</option
                    >{/each}
                </select></label
              >
            </div>
            {#if p.teams.length}<div class="team-summary">
                <span>{ui('Teams')}</span><strong>{p.teams.join(', ')}</strong>
              </div>{/if}
          </fieldset>
          {#if !form?.scope && form?.message}<p class="feedback failure" role="alert">
              {ui(form.message)}
            </p>{/if}
          {#if !form?.scope && form?.saved && !dirty}<p class="feedback" role="status">
              {ui('Profile saved.')}
            </p>{/if}
          <div class="form-actions detail-actions">
            <button class="v2-btn v2-btn-primary" disabled={saving || (!dirty && !data.onboarding)}
              >{saving
                ? ui('Saving…')
                : data.onboarding
                  ? p.setup_step === 'profile_organization'
                    ? ui('Continue to organization')
                    : ui('Save and open CRM')
                  : ui('Save changes')}</button
            >
            {#if dirty && !data.onboarding}<button
                class="v2-btn"
                type="button"
                disabled={saving}
                onclick={resetDetails}>{ui('Cancel')}</button
              >{/if}
          </div>
        </form>
        {#if !data.onboarding}<form
            class="details-form"
            method="POST"
            action="?/password"
            use:enhance
          >
            <fieldset>
              <h3>{data.hasPassword ? ui('Change password') : ui('Set your password')}</h3>
              {#if data.hasPassword}<label
                  >{ui('Current password')}<input
                    class="v2-input"
                    type="password"
                    name="current_password"
                    required
                    autocomplete="current-password"
                    maxlength="128"
                  /></label
                >{/if}
              <label
                >{ui('New password')}<input
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
                >{ui('Confirm password')}<input
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
                {ui(form.message || 'Password saved.')}
              </p>{/if}
            <div class="form-actions">
              <button class="v2-btn v2-btn-primary">{ui('Save password')}</button>
            </div>
          </form>{/if}
      </div>
      {#if !data.onboarding}<div
          id="profile-panel-integrations"
          role="tabpanel"
          aria-labelledby="profile-tab-integrations"
          hidden={activeTab !== 'integrations'}
          tabindex="0"
          class="profile-panel"
        >
          <div class="section-heading">
            <h2 id="integration-title"><Link2 size={17} />{ui('Connected accounts')}</h2>
            <span class="subtle-badge">{ui('Per user')}</span>
          </div>
          <p class="section-description">{ui('Manage your email and calendar connections.')}</p>
          {#if googleCallbackMessage(data.googleResult)}
            <ErrorNotice message={ui(googleCallbackMessage(data.googleResult))} />
          {:else if data.googleResult === 'connected'}
            <p class="feedback" role="status">
              {ui(
                'Google connected. Check the connection status below for synchronization progress.'
              )}
            </p>
          {/if}
          {#if googleActionError}<ErrorNotice message={ui(googleActionError)} />{/if}
          {#if form?.scope === 'google'}
            {#if form.message}<ErrorNotice message={ui(form.message)} />
            {:else}<p class="feedback" role="status">{ui(form.googleMessage)}</p>{/if}
          {/if}
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
                  <p>{connection?.email || ui('No account connected')}</p>
                </div>
                <span class="status-badge"
                  >{!connection?.configured
                    ? ui('Setup required')
                    : connection?.status === 'connected'
                      ? ui('Connected')
                      : connection?.status === 'reconnect'
                        ? ui('Reconnect required')
                        : ui('Not connected')}</span
                >
              </div>
              <p class="help">
                {item.service === 'gmail'
                  ? ui(
                      'Sent and received emails are matched to your contacts by email address. Only you can see your connected mailbox activity, including the message text. Initial import covers the last 90 days; attachments are not imported.'
                    )
                  : ui(
                      'Events synchronize in both directions. Your hosted CRM appointments and their meeting notes appear in Google Calendar. Google changes update the linked appointment. No invitation emails are sent by this sync.'
                    )}
              </p>
              {#if connection?.last_sync}<p class="help">
                  {ui('Last sync:')}
                  {new Date(connection.last_sync).toLocaleString(locale())}
                </p>{/if}
              {#if item.service === 'calendar' && connection?.status === 'connected'}<p
                  class="help"
                >
                  {ui('Calendar:')}
                  {connection.calendar}{ui(
                    '. Sync includes the previous 90 days and the next 12 months.'
                  )}
                </p>{/if}
              {#if connection?.error}<ErrorNotice
                  message={ui(googleErrorMessage(connection.error))}
                />{/if}
              {#if !connection?.configured}<p class="setup-note">
                  {ui(
                    'The CRM administrator needs to configure Google connections before you can connect.'
                  )}
                </p>{/if}
              <div class="integration-actions">
                <form method="POST" action="?/googleConnect">
                  <input type="hidden" name="service" value={item.service} /><button
                    class="v2-btn v2-btn-primary v2-btn-sm"
                    disabled={!connection?.configured || googlePending}
                    >{connection?.email ? ui('Reconnect') : ui(`Connect ${item.title}`)}</button
                  >
                </form>
                {#if connection?.status === 'connected'}<form
                    method="POST"
                    action="?/googleManage"
                    use:enhance={onGoogleManage}
                  >
                    <input type="hidden" name="service" value={item.service} /><button
                      class="v2-btn v2-btn-sm"
                      disabled={googlePending}
                      name="operation"
                      value="sync">{ui('Sync now')}</button
                    >
                  </form>{/if}
                {#if connection?.email}<form
                    method="POST"
                    action="?/googleManage"
                    use:enhance={onGoogleManage}
                  >
                    <input type="hidden" name="service" value={item.service} /><button
                      class="v2-btn v2-btn-sm"
                      disabled={googlePending}
                      name="operation"
                      value="disconnect">{ui('Disconnect')}</button
                    >
                  </form>{/if}
                {#if item.service === 'calendar' && connection?.status === 'connected'}<button
                    class="v2-btn v2-btn-sm"
                    disabled={loadingCalendars || googlePending}
                    onclick={loadCalendars}
                    >{ui(loadingCalendars ? 'Loading…' : 'Choose calendar')}</button
                  >{/if}
              </div>
              {#if item.service === 'calendar' && calendars.length}<form
                  method="POST"
                  action="?/googleManage"
                  use:enhance={onGoogleManage}
                >
                  <input type="hidden" name="service" value="calendar" /><input
                    type="hidden"
                    name="operation"
                    value="calendar"
                  /><label
                    >{ui('Calendar')}<select
                      class="v2-input"
                      name="calendar_id"
                      bind:value={selectedCalendar}
                      >{#each calendars as calendar}<option value={calendar.id}
                          >{calendar.name}{calendar.writable ? '' : ui(' (read only)')}</option
                        >{/each}</select
                    ></label
                  ><button class="v2-btn v2-btn-sm" disabled={googlePending}
                    >{ui('Use this calendar')}</button
                  >
                </form>{/if}
              {#if item.service === 'calendar' && calendarError}<ErrorNotice
                  message={ui(calendarError)}
                />{/if}
            </div>
          {/each}
        </div>{/if}
    </div>
  </div>
</div>

<style>
  .profile-panel :global(.crm-error-notice) {
    margin-block: var(--crm-space-3);
  }
  .profile-shell {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    min-width: 0;
    background: var(--v2-bg, var(--crm-surface));
  }
  .profile-shell > .v2-scroll {
    flex: 1;
    min-height: 0;
  }
  .settings-group {
    display: grid;
    gap: var(--crm-space-5);
  }
  .settings-group + .settings-group {
    padding-top: 26px;
    border-top: 1px solid var(--v2-line-soft);
  }
  .settings-group h3 {
    margin-bottom: 2px;
    font-size: var(--crm-text-sm);
  }
  .settings-group .help {
    margin-top: -14px;
  }
  .details-form label {
    font-weight: 500;
    gap: 9px;
    font-size: var(--crm-text-sm);
  }
  .details-form :global(select),
  .details-form :global(input) {
    min-height: 42px;
    background: var(--v2-bg, var(--crm-surface));
    border-radius: var(--crm-radius-md);
  }
  .details-form input[readonly] {
    background: var(--v2-line-soft);
    color: var(--v2-slate);
  }
  .team-summary {
    display: flex;
    gap: var(--crm-space-3);
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
  }
  .team-summary strong {
    font-weight: 500;
    color: var(--v2-ink);
  }
  .detail-actions {
    margin-top: 28px;
    padding-top: var(--crm-space-5);
    border-top: 1px solid var(--v2-line-soft);
  }
  .section-heading .section-description {
    margin: var(--crm-space-2) 0 0;
  }
  .integration,
  .setup-note {
    max-width: 680px;
  }

  .profile-tabs {
    display: flex;
    gap: var(--crm-space-6);
    padding: 0 var(--crm-space-6);
    border-bottom: 1px solid var(--v2-line);
    flex-shrink: 0;
    overflow-x: auto;
  }
  .profile-tabs button {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: var(--crm-space-2);
    padding: var(--crm-space-4) 0 13px;
    border: 0;
    border-bottom: 2px solid transparent;
    background: transparent;
    color: var(--v2-slate);
    font: inherit;
    font-size: var(--crm-text-sm);
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
    border-radius: var(--crm-radius-sm);
  }
  .profile-layout {
    padding: 30px var(--crm-space-8);
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
    gap: var(--crm-space-3);
    margin-bottom: 18px;
  }
  h2 {
    display: flex;
    gap: var(--crm-space-2);
    align-items: center;
    margin: 0;
    font-size: var(--crm-text-base);
    font-weight: 600;
  }
  h3 {
    font-size: var(--crm-text-sm);
    margin: 0;
    font-weight: 600;
  }
  .help {
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
    line-height: 1.5;
    margin: var(--crm-space-2) 0 0;
    overflow-wrap: anywhere;
  }
  label {
    display: grid;
    gap: 7px;
    font-size: var(--crm-text-xs);
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
    gap: var(--crm-space-2);
    margin-top: 18px;
  }
  .section-description {
    color: var(--v2-slate);
    font-size: var(--crm-text-xs);
    line-height: 1.6;
    margin: 0 0 var(--crm-space-4);
  }
  .integration + .integration {
    border-top: 1px solid var(--v2-line);
    padding-top: var(--crm-space-6);
    margin-top: var(--crm-space-6);
  }
  .integration-heading {
    display: flex;
    gap: var(--crm-space-3);
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
    font-size: var(--crm-text-xs);
    margin: var(--crm-space-1) 0 0;
  }
  .service-icon {
    display: grid;
    place-items: center;
    width: 40px;
    height: 40px;
    background: var(--v2-line-soft);
    border-radius: var(--crm-radius-md);
    color: var(--v2-slate);
  }
  .status-badge,
  .subtle-badge {
    font-size: var(--crm-text-xs);
    padding: var(--crm-space-1) var(--crm-space-2);
    background: var(--v2-line-soft);
    color: var(--v2-slate);
    border-radius: var(--crm-radius-sm);
    white-space: nowrap;
  }
  .integration-actions {
    display: flex;
    flex-wrap: wrap;
    gap: var(--crm-space-2);
    margin-top: var(--crm-space-3);
  }
  .setup-note {
    margin: var(--crm-space-5) 0 0;
    padding-top: var(--crm-space-4);
    border-top: 1px solid var(--v2-line);
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
    line-height: 1.6;
  }
  .feedback {
    color: var(--v2-moss);
    font-size: var(--crm-text-xs);
    margin: var(--crm-space-3) 0 0;
  }
  .feedback.failure {
    color: var(--v2-rust);
  }

  @media (max-width: 600px) {
    .profile-layout {
      padding: 14px;
    }
    .profile-tabs {
      gap: var(--crm-space-4);
      padding: 0 14px;
    }
    .profile-tabs button {
      font-size: var(--crm-text-xs);
      gap: 5px;
    }
  }
</style>
