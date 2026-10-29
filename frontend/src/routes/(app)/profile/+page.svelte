<script>
  import imgGmail from '$lib/assets/images/gmail.png';
  import imgCalendar from '$lib/assets/images/google-calendar.png';
  import CalendarConnectionSettings from '$lib/components/CalendarConnectionSettings.svelte';
  import Notice from '$lib/components/Notice.svelte';
  import ErrorNotice from '$lib/components/ErrorNotice.svelte';
  import GoogleConnectionDialog from '$lib/components/GoogleConnectionDialog.svelte';
  import { googleErrorMessage, googleCallbackMessage } from '$lib/utils/google-feedback.js';
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();

  import { resolve } from '$app/paths';
  import { replaceState } from '$app/navigation';
  import { page } from '$app/state';
  import { untrack } from 'svelte';
  import LanguageSelect from '$lib/v2/components/LanguageSelect.svelte';
  import { enhance } from '$app/forms';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import { Link2, UserRound } from '@lucide/svelte';

  /** @type {{data:any, form:any}} */
  let { data, form } = $props();
  let p = $derived(data.profile);
  const googleAccounts = $derived(
    [
      { service: 'gmail', ...p.integrations?.gmail },
      { service: 'calendar', ...p.integrations?.google_calendar }
    ]
      .filter((account) => !account.independent_disconnect)
      .filter(
        (account, index, accounts) =>
          account.email &&
          accounts.findIndex(
            (other) => other.email?.toLowerCase() === account.email.toLowerCase()
          ) === index
      )
  );
  let googlePending = $state(false);
  let googleActionError = $state('');
  const onGoogleManage = () => {
    // Callback feedback must not reappear on reload after a newer connection action.
    if (page.url.searchParams.has('google')) {
      const url = new URL(page.url);
      url.searchParams.delete('google');
      url.searchParams.set('tab', 'integrations');
      // The path is resolved separately to preserve the current query and fragment.
      // eslint-disable-next-line svelte/no-navigation-without-resolve
      replaceState(`${resolve('/profile')}${url.search}${url.hash}`, page.state);
    }
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
    return async (/** @type {any} */ { update }) => {
      saving = false;
      await update({ reset: false });
    };
  };
</script>

<div class="profile-shell crm-settings-fields">
  <PageHeader title={data.onboarding ? ui('Complete your profile') : ui('Profile')}>
    {#snippet sub()}{data.onboarding
        ? ui('Confirm your name, language and time zone before you start.')
        : ui('Your details, preferences and connected accounts')}{/snippet}
  </PageHeader>

  {#if !data.onboarding}<div
      class="profile-tabs crm-preferences-tabs"
      role="tablist"
      aria-label={ui('Profile sections')}
    >
      {#each tabs as tab, index (tab.id)}
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
    <div class="profile-layout crm-settings-content crm-preferences-body">
      <div
        id="profile-panel-info"
        role="tabpanel"
        aria-labelledby={data.onboarding ? 'personal-information-title' : 'profile-tab-info'}
        hidden={activeTab !== 'info'}
        tabindex="0"
        class="profile-panel personal crm-preferences-card"
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
              <div class="field-group">
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
              </div>
              <label class="phone-field"
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
              <div class="field-group">
                <label
                  >{ui('CRM language')}
                  <select class="v2-input" name="ui_language" bind:value={editUiLanguage}>
                    <option value="en">English</option><option value="es">Español</option>
                  </select>
                </label>
                <p class="help">
                  {ui(
                    'Only changes your interface. Applies across your organizations and devices.'
                  )}
                </p>
              </div>
              <LanguageSelect bind:value={editLanguage} />
              <label class="wide"
                >{ui('Time zone')}<select
                  class="v2-input"
                  name="timezone"
                  bind:value={editTimezone}
                >
                  <option value=""
                    >{ui('Organization default ·')}
                    {p.organization_timezone.replaceAll('_', ' ')}</option
                  >
                  {#each data.timezones as zone (zone.name)}<option value={zone.name}
                      >{zone.label}</option
                    >{/each}
                </select></label
              >
            </div>
            {#if p.teams.length}<div class="team-summary">
                <span>{ui('Teams')}</span><strong>{p.teams.join(', ')}</strong>
              </div>{/if}
          </fieldset>
          {#if !form?.scope && form?.message}<Notice message={ui(form.message)} />{/if}
          {#if !form?.scope && form?.saved && !dirty}<Notice
              tone="success"
              message={ui('Profile saved.')}
            />{/if}
          {#if dirty || data.onboarding}<div class="crm-settings-actions">
              <button
                class="v2-btn v2-btn-primary"
                disabled={saving || (!dirty && !data.onboarding)}
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
            </div>{/if}
        </form>
        {#if !data.onboarding}<form
            class="details-form password-form"
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
            {#if form?.scope === 'password'}<Notice
                tone={form.message ? 'error' : 'success'}
                message={ui(form.message || 'Password saved.')}
              />{/if}
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
          class="profile-panel crm-preferences-card"
        >
          <div class="section-heading">
            <h2 id="integration-title"><Link2 size={17} />{ui('Connected accounts')}</h2>
          </div>
          {#if !p.integrations?.gmail?.configured || !p.integrations?.google_calendar?.configured}
            <Notice
              tone="info"
              message={ui('Google setup is required. Contact your CRM administrator.')}
            />
          {/if}
          {#if form?.scope !== 'google' && !googleActionError && !googlePending}
            {#if googleCallbackMessage(data.googleResult)}
              <ErrorNotice message={ui(googleCallbackMessage(data.googleResult))} />
            {:else if data.googleResult === 'connected'}
              <Notice tone="success" message={ui('Google connected.')} />
            {/if}
          {/if}
          {#if googleActionError}<ErrorNotice message={ui(googleActionError)} />{/if}
          {#if form?.scope === 'google'}
            {#if form.message}<ErrorNotice message={ui(form.message)} />
            {:else}<Notice tone="success" message={ui(form.googleMessage)} />{/if}
          {/if}
          {#each [{ key: 'gmail', service: 'gmail', title: 'Gmail' }, { key: 'google_calendar', service: 'calendar', title: 'Google Calendar' }] as item (item.key)}
            {@const connection = p.integrations?.[item.key]}
            <section class="integration" aria-labelledby={`integration-${item.key}`}>
              <div class="integration-heading">
                <div class="service-icon">
                  <img
                    src={item.service === 'gmail' ? imgGmail : imgCalendar}
                    alt=""
                    width="28"
                    height="28"
                  />
                </div>
                <div>
                  <h3 id={`integration-${item.key}`}>{item.title}</h3>
                  <p>{connection?.email || ui('No account connected')}</p>
                  <span
                    class="connection-status"
                    class:connected={connection?.configured && connection?.status === 'connected'}
                  >
                    <span class="status-dot" aria-hidden="true"></span>
                    {!connection?.configured
                      ? ui('Setup required')
                      : connection?.status === 'connected'
                        ? ui('Connected')
                        : connection?.status === 'reconnect'
                          ? ui('Reconnect required')
                          : ui('Not connected')}
                  </span>
                </div>
                <div class="integration-actions">
                  {#if connection?.status !== 'connected' || connection?.migration_available}
                    <GoogleConnectionDialog
                      service={item.service}
                      label={connection?.email ? 'Reconnect' : `Connect ${item.title}`}
                      disabled={!connection?.configured || googlePending}
                    />
                  {/if}
                  {#if connection?.email}
                    <form method="POST" action="?/googleManage" use:enhance={onGoogleManage}>
                      <input type="hidden" name="service" value={item.service} />
                      <button
                        class="v2-btn v2-btn-sm"
                        disabled={googlePending}
                        name="operation"
                        value="disconnect"
                        aria-label={ui(
                          item.service === 'gmail'
                            ? 'Disconnect Gmail'
                            : 'Disconnect Google Calendar'
                        )}>{ui('Disconnect')}</button
                      >
                    </form>
                  {/if}
                </div>
              </div>
              {#if connection?.status !== 'connected'}
                <p class="help">
                  {item.service === 'gmail'
                    ? ui('View contact emails. Your mailbox stays private.')
                    : ui('Sync appointments and guest responses.')}
                  <a
                    href={resolve(
                      item.service === 'gmail'
                        ? '/help/knowledge/gmail-records'
                        : '/help/knowledge/google-calendar'
                    )}>{ui(item.service === 'gmail' ? 'Gmail guide' : 'Calendar guide')}</a
                  >
                </p>
              {/if}
              {#if connection?.error}<ErrorNotice
                  message={ui(googleErrorMessage(connection.error))}
                />{/if}
              {#if item.service === 'calendar' && connection?.status === 'connected'}
                <CalendarConnectionSettings pending={googlePending} onManage={onGoogleManage} />
              {/if}
            </section>
          {/each}
          {#if googleAccounts.length}<details class="connection-settings google-advanced">
              <summary>{ui('Advanced options')}</summary>
              {#each googleAccounts as account (account.email)}
                <div class="google-account-access">
                  <strong>{account.email}</strong>
                  <GoogleConnectionDialog
                    service={account.service}
                    accountEmail={account.email}
                    label="Revoke shared Google access"
                    revoke
                    onManage={onGoogleManage}
                    disabled={googlePending}
                  />
                </div>
              {/each}
            </details>{/if}
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
    background: var(--crm-canvas);
  }
  .profile-shell > .v2-scroll {
    flex: 1;
    min-height: 0;
  }
  .settings-group {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    align-items: start;
    gap: var(--crm-space-4);
  }
  .settings-group + .settings-group {
    padding-top: var(--crm-space-5);
    border-top: 1px solid var(--v2-line-soft);
  }
  .settings-group h3 {
    margin-bottom: 2px;
    font-size: var(--crm-text-sm);
  }
  .settings-group h3,
  .settings-group .wide {
    grid-column: 1 / -1;
  }
  .field-group {
    min-width: 0;
  }
  .details-form label {
    font-weight: 500;
    gap: var(--crm-space-2);
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
  .section-heading .section-description {
    margin: var(--crm-space-2) 0 0;
  }
  .integration {
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
    padding: var(--crm-space-5) var(--crm-page-gutter);
  }
  .profile-panel {
    background: var(--crm-surface);
    border: 1px solid var(--crm-border-soft);
    border-radius: var(--crm-radius-lg);
    box-shadow: var(--crm-panel-shadow);
    padding: var(--crm-space-5);
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
    margin-bottom: var(--crm-space-4);
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
    margin-top: 0;
  }
  .password-form {
    max-width: 560px;
    padding-top: var(--crm-space-5);
    border-top: 1px solid var(--crm-border-soft);
  }
  .phone-field {
    max-width: 22rem;
  }
  .details-form fieldset {
    display: grid;
    gap: var(--crm-space-5);
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
  .integration {
    padding: var(--crm-space-5);
    border: 1px solid var(--v2-line);
    border-radius: var(--crm-radius-md);
  }
  .integration + .integration {
    margin-top: var(--crm-space-4);
  }
  .connection-settings {
    margin-top: var(--crm-space-4);
  }
  .connection-settings summary {
    width: fit-content;
    cursor: pointer;
    color: var(--v2-slate);
    font-size: var(--crm-text-xs);
    padding-block: var(--crm-space-2);
  }
  .connection-settings summary:focus-visible {
    outline: 2px solid var(--v2-ink);
    outline-offset: 3px;
    border-radius: var(--crm-radius-sm);
  }
  .google-advanced {
    border-top: 1px solid var(--v2-line);
    padding-top: var(--crm-space-2);
  }
  .google-account-access {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: var(--crm-space-3);
    padding-block: var(--crm-space-3);
  }
  .google-account-access strong {
    font-size: var(--crm-text-sm);
    overflow-wrap: anywhere;
    min-width: 0;
  }
  .connection-status.connected {
    color: var(--v2-moss);
  }
  .integration-heading {
    display: flex;
    gap: var(--crm-space-3);
    align-items: center;
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
    flex-shrink: 0;
    display: grid;
    place-items: center;
    width: 40px;
    height: 40px;
    border-radius: var(--crm-radius-md);
  }
  .connection-status {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: var(--crm-space-1);
    color: var(--v2-slate);
    font-size: var(--crm-text-xs);
  }
  .status-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: currentColor;
    flex-shrink: 0;
  }
  .integration .help a {
    font-size: var(--crm-text-xs);
    text-decoration: underline;
    text-underline-offset: 0.2em;
  }
  .integration .help a {
    display: inline-block;
    margin-inline-start: var(--crm-space-1);
  }
  .integration-heading p {
    overflow-wrap: anywhere;
  }
  .integration-actions {
    display: flex;
    flex-wrap: wrap;
    gap: var(--crm-space-2);
  }

  @container (max-width: 600px) {
    .integration-actions {
      flex-basis: 100%;
    }
    .settings-group {
      grid-template-columns: 1fr;
    }
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
