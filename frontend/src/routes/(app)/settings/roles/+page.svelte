<script>
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();

  import { enhance } from '$app/forms';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import { Plus, ShieldCheck, Pencil, Copy, ChevronLeft } from '@lucide/svelte';
  let { data, form } = $props();
  let editing = $state(null),
    busy = $state(false),
    error = $state('');
  let expandedModules = $state({});
  const scopes = [
    ['own', 'Personal'],
    ['team', 'Team'],
    ['organization', 'Organization']
  ];
  const dependent = ['stage', 'notes', 'attachments', 'associations', 'reassign'];
  const actionHints = {
    view: 'Lists, profiles, search and visible record data.',
    create: 'Create new records.',
    edit: 'Change existing property values.',
    stage: 'Move between stages; entry rules still apply.',
    notes: 'Add notes; edit or remove your own notes.',
    attachments: 'Upload files to records within this set’s access level.',
    delete_attachments:
      'Delete attachments after confirmation, within this set’s access level. Does not allow deleting records.',
    associations: 'Add or remove links. Access is checked on both records.',
    delete: 'Permanently delete records after confirmation.',
    export: 'Download visible records as CSV.',
    reassign: 'Choose owners or teams within this set’s access level.',
    cancel: 'Cancel scheduled events.',
    override_conflicts: 'Confirm a booking that overlaps another event.'
  };
  function edit(role) {
    error = '';
    const base = role || { name: '', description: '', scope: 'own', rules: {}, member_count: 0 };
    expandedModules = Object.fromEntries(
      data.catalog.map((module) => [
        module.key,
        ['contacts', 'calendar', 'reports'].includes(module.key)
      ])
    );
    editing = structuredClone(base);
    editing.enabled = Object.fromEntries(
      data.catalog.map((module) => [
        module.key,
        Object.fromEntries(
          module.actions.map((action) => {
            const value = base.rules?.[module.key]?.[action.key];
            return [action.key, action.boolean ? value === true : !!value && value !== 'none'];
          })
        )
      ])
    );
  }
  function toggle(module, action, checked) {
    const row = editing.enabled[module];
    row[action] = checked;
    if (action === 'view' && !checked) for (const key of Object.keys(row)) row[key] = false;
    if (action === 'edit' && !checked && !['calendar', 'reports'].includes(module))
      for (const key of dependent) row[key] = false;
    if (checked && dependent.includes(action) && !['calendar', 'reports'].includes(module))
      row.edit = true;
  }
  function rulesForSave() {
    return Object.fromEntries(
      data.catalog.map((module) => [
        module.key,
        Object.fromEntries(
          module.actions.map((action) => [
            action.key,
            action.boolean
              ? editing.enabled[module.key][action.key]
              : editing.enabled[module.key][action.key]
                ? editing.scope
                : 'none'
          ])
        )
      ])
    );
  }
  function hint(module, action) {
    if (module === 'reports')
      return action === 'view'
        ? 'Reports include only records this user can view, within the selected access level.'
        : 'Also requires Export on each object included in the report.';
    if (module === 'calendar' && action === 'reassign')
      return 'Schedule for another host within this set’s access level.';
    if (module === 'calendar' && action === 'edit')
      return 'Change event dates and times within this set’s access level.';
    if (module === 'calendar' && action === 'create')
      return 'Schedule events. Creating an associated deal also requires Deals permissions.';
    return actionHints[action];
  }
</script>

<PageHeader title={ui('Roles & Permissions')}>
  {#snippet sub()}{ui('Choose what each role can do and which records it can access.')}{/snippet}
  {#snippet actions()}{#if !data.forbidden && !editing}<button
        class="v2-btn v2-btn-primary"
        onclick={() => edit(null)}><Plus size={15} />{ui('New permission set')}</button
      >{/if}{/snippet}
</PageHeader>
<div class="v2-scroll">
  <div class="roles-content">
    {#if data.forbidden}<p>{ui('Only organization admins can manage roles and permissions.')}</p>
    {:else if editing}
      <form
        method="POST"
        action="?/save"
        use:enhance={() => {
          busy = true;
          return async ({ result, update }) => {
            try {
              if (result.type === 'success') {
                await update();
                editing = null;
              } else {
                error =
                  result.type === 'failure'
                    ? String(result.data?.error || 'Could not save role.')
                    : 'Could not save role.';
              }
            } finally {
              busy = false;
            }
          };
        }}
      >
        <input type="hidden" name="id" value={editing.id || ''} /><input
          type="hidden"
          name="rules"
          value={JSON.stringify(rulesForSave())}
        />
        <button class="back" type="button" disabled={busy} onclick={() => (editing = null)}
          ><ChevronLeft size={15} />{ui('Permission sets')}</button
        >
        <fieldset disabled={busy}>
          <div class="identity">
            <label
              >{ui('Permission set name')}<input
                class="v2-input"
                name="name"
                readonly={editing.id && ['Member', 'Manager'].includes(editing.name)}
                bind:value={editing.name}
                required
                maxlength="80"
              /></label
            ><label
              >{ui('Description')}<input
                class="v2-input"
                name="description"
                bind:value={editing.description}
                maxlength="255"
              /></label
            >
          </div>
          <div class="scope-panel">
            {#if editing.id && ['Member', 'Manager'].includes(editing.name)}
              <div class="fixed-scope">
                <span>{ui('Access level')}</span><strong
                  >{editing.name === 'Member' ? ui('Personal') : ui('Team')}</strong
                >
              </div>
              <input type="hidden" name="scope" value={editing.scope} />
            {:else}<label
                >{ui('Access level')}<select
                  name="scope"
                  class="v2-input"
                  bind:value={editing.scope}
                  >{#each scopes as [value, label]}<option {value}>{label}</option>{/each}</select
                ></label
              >{/if}
            <p>
              {editing.scope === 'own'
                ? ui('Assigned records and events you host. Events you attend are also visible.')
                : editing.scope === 'team'
                  ? ui(
                      'Your records and records assigned to your teams or their members. Calendar access includes events hosted by team members.'
                    )
                  : ui('Records and events across this organization.')}
            </p>
          </div>
          <div class="permission-groups">
            {#each data.catalog as module (module.key)}
              <details class="permission-group" bind:open={expandedModules[module.key]}>
                <summary
                  ><span>{module.label}</span><small
                    >{Object.values(editing.enabled[module.key]).filter(Boolean).length}
                    {ui('enabled')}</small
                  ></summary
                >
                <div class="permission-options">
                  {#each module.actions as action}
                    <label
                      class="permission-option"
                      class:muted={action.key !== 'view' && !editing.enabled[module.key].view}
                    >
                      <input
                        type="checkbox"
                        aria-label={`${module.label}: ${action.key}`}
                        checked={editing.enabled[module.key][action.key]}
                        disabled={action.key !== 'view' && !editing.enabled[module.key].view}
                        onchange={(event) =>
                          toggle(module.key, action.key, event.currentTarget.checked)}
                      />
                      <span
                        ><strong>{action.label}</strong><small>{hint(module.key, action.key)}</small
                        ></span
                      >
                    </label>
                  {/each}
                </div>
              </details>
            {/each}
          </div>
        </fieldset>
        {#if editing.member_count}<p class="hint">
            {ui('Saving updates access for')}
            {editing.member_count}
            {ui('assigned users on their next request.')}
          </p>{/if}
        {#if error}<p class="error" role="alert">{ui(error)}</p>{/if}
        <div class="save-actions">
          <button class="v2-btn" type="button" disabled={busy} onclick={() => (editing = null)}
            >{ui('Cancel')}</button
          ><button class="v2-btn v2-btn-primary" disabled={busy}
            >{busy ? ui('Saving…') : ui('Save permission set')}</button
          >
        </div>
      </form>
    {:else}
      <div class="role">
        <div>
          <h2><ShieldCheck size={17} />{ui('Super Admin')}</h2>
          <p>
            {ui(
              'Organization creator. Full access and exclusive control over other administrators.'
            )}
          </p>
        </div>
        <span class="protected">{ui('Creator only')}</span>
      </div>
      <div class="role">
        <div>
          <h2><ShieldCheck size={17} />{ui('Admin')}</h2>
          <p>
            {ui(
              'Full organization access. Manages users, teams, permission sets and CRM configuration.'
            )}
          </p>
        </div>
        <span class="protected">{ui('System role')}</span>
      </div>
      {#each data.roles as role}<div class="role">
          <div>
            <h2>
              {role.name}<span class="scope-badge"
                >{scopes.find(([key]) => key === role.scope)?.[1]}</span
              >
            </h2>
            <p>
              {role.description ||
                (['Member', 'Manager'].includes(role.name)
                  ? 'Default permission set'
                  : 'Custom permission set')} · {role.member_count}
              {role.member_count === 1 ? ui('user') : ui('users')}
            </p>
          </div>
          <div class="actions">
            <button
              class="v2-btn v2-btn-sm"
              onclick={() =>
                edit({ ...role, id: null, name: `${role.name} copy`, member_count: 0 })}
              aria-label={`Duplicate ${role.name}`}><Copy size={13} />{ui('Duplicate')}</button
            ><button
              class="v2-btn v2-btn-sm"
              onclick={() => edit(role)}
              aria-label={`Edit permissions for ${role.name}`}
              ><Pencil size={13} />{ui('Edit permissions')}</button
            >
          </div>
        </div>{/each}
      {#if form?.saved}<p class="success" role="status">{ui('Permission set saved.')}</p>{/if}
    {/if}
  </div>
</div>

<style>
  .roles-content {
    padding: var(--crm-space-6) 28px;
    max-width: 1150px;
    container-type: inline-size;
  }
  .role {
    display: flex;
    gap: var(--crm-space-5);
    align-items: center;
    justify-content: space-between;
    padding: var(--crm-space-6) 0;
    border-bottom: 1px solid var(--v2-line-soft);
  }
  h2 {
    font-size: var(--crm-text-sm);
    margin: 0;
    display: flex;
    align-items: center;
    gap: var(--crm-space-2);
  }
  .role p,
  .hint {
    color: var(--v2-slate);
    font-size: var(--crm-text-xs);
    line-height: 1.6;
  }
  .protected,
  .scope-badge {
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
  }
  .scope-badge {
    border: 1px solid var(--v2-line);
    border-radius: var(--crm-radius-sm);
    padding: 3px 6px;
    font-weight: 400;
  }
  .identity {
    display: grid;
    grid-template-columns: 1fr 2fr;
    gap: var(--crm-space-5);
    margin-bottom: var(--crm-space-6);
  }
  label {
    display: grid;
    gap: var(--crm-space-2);
    font-size: var(--crm-text-sm);
  }
  .scope-panel {
    display: flex;
    align-items: center;
    gap: 28px;
    padding: 18px var(--crm-space-5);
    background: var(--v2-surface, var(--crm-surface));
    border: 1px solid var(--v2-line);
    border-radius: var(--crm-radius-md);
    margin-bottom: var(--crm-space-6);
  }
  .scope-panel label,
  .fixed-scope {
    min-width: 160px;
    display: grid;
    gap: var(--crm-space-2);
    font-size: var(--crm-text-sm);
  }
  .scope-panel p {
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
    line-height: 1.6;
    max-width: 550px;
    margin: 0;
  }
  .actions,
  .save-actions {
    display: flex;
    gap: var(--crm-space-2);
  }
  .save-actions {
    position: sticky;
    bottom: 0;
    background: var(--v2-surface, var(--crm-surface));
    border-top: 1px solid var(--v2-line);
    padding: var(--crm-space-4) 0;
    justify-content: flex-end;
    margin-top: var(--crm-space-5);
  }
  .error {
    color: var(--v2-rust);
  }
  .success {
    color: var(--v2-moss);
  }
  fieldset {
    border: 0;
    padding: 0;
    margin: 0;
    min-width: 0;
  }
  .permission-group {
    border: 1px solid var(--v2-line);
    border-radius: var(--crm-radius-md);
    background: var(--v2-surface, var(--crm-surface));
    margin-bottom: var(--crm-space-3);
  }
  .permission-group summary {
    cursor: pointer;
    padding: 17px var(--crm-space-5);
    font-size: var(--crm-text-sm);
    font-weight: 600;
  }
  .permission-group summary small {
    float: right;
    font-size: var(--crm-text-xs);
    font-weight: 400;
    color: var(--v2-slate);
  }
  .permission-options {
    padding: 0 var(--crm-space-5) var(--crm-space-5);
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: var(--crm-space-5) var(--crm-space-6);
  }
  .permission-option {
    display: flex;
    align-items: flex-start;
    gap: 10px;
  }
  .permission-option input {
    accent-color: var(--v2-ink);
    flex-shrink: 0;
    width: 16px;
    height: 16px;
    margin-top: 2px;
  }
  .permission-option span {
    display: grid;
    gap: 5px;
  }
  .permission-option strong {
    font-weight: 500;
    font-size: var(--crm-text-xs);
  }
  .permission-option small {
    font-size: var(--crm-text-xs);
    line-height: 1.5;
    color: var(--v2-slate);
  }
  .muted {
    opacity: 0.5;
  }
  .back {
    display: flex;
    align-items: center;
    gap: 6px;
    background: none;
    border: 0;
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
    padding: 0;
    margin-bottom: var(--crm-space-6);
  }
  summary:focus-visible,
  .back:focus-visible {
    outline: 2px solid var(--v2-slate);
    outline-offset: 3px;
  }
  @media (max-width: 1000px) {
    .permission-options {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }
  @media (max-width: 650px) {
    .identity,
    .permission-options {
      grid-template-columns: 1fr;
    }
    .roles-content {
      padding: var(--crm-space-4);
    }
    .role,
    .scope-panel {
      flex-wrap: wrap;
    }
  }
  @container (max-width: 36rem) {
    .role {
      flex-direction: column;
      align-items: flex-start;
    }
    .role h2 {
      flex-wrap: wrap;
    }
    .scope-badge {
      white-space: nowrap;
    }
    .actions {
      flex-wrap: wrap;
    }
    .identity,
    .permission-options {
      grid-template-columns: 1fr;
    }
    .scope-panel {
      flex-wrap: wrap;
    }
  }
</style>
