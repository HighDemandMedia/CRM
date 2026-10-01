<script>
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

<PageHeader title="Roles & Permissions">
  {#snippet sub()}Choose what each role can do and which records it can access.{/snippet}
  {#snippet actions()}{#if !data.forbidden && !editing}<button
        class="v2-btn v2-btn-primary"
        onclick={() => edit(null)}><Plus size={15} />New permission set</button
      >{/if}{/snippet}
</PageHeader>
<div class="v2-scroll">
  <div class="roles-content">
    {#if data.forbidden}<p>Only organization admins can manage roles and permissions.</p>
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
          ><ChevronLeft size={15} />Permission sets</button
        >
        <fieldset disabled={busy}>
          <div class="identity">
            <label
              >Permission set name<input
                class="v2-input"
                name="name"
                readonly={editing.id && ['Member', 'Manager'].includes(editing.name)}
                bind:value={editing.name}
                required
                maxlength="80"
              /></label
            ><label
              >Description<input
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
                <span>Access level</span><strong
                  >{editing.name === 'Member' ? 'Personal' : 'Team'}</strong
                >
              </div>
              <input type="hidden" name="scope" value={editing.scope} />
            {:else}<label
                >Access level<select name="scope" class="v2-input" bind:value={editing.scope}
                  >{#each scopes as [value, label]}<option {value}>{label}</option>{/each}</select
                ></label
              >{/if}
            <p>
              {editing.scope === 'own'
                ? 'Assigned records and events you host. Events you attend are also visible.'
                : editing.scope === 'team'
                  ? 'Your records and records assigned to your teams or their members. Calendar access includes events hosted by team members.'
                  : 'Records and events across this organization.'}
            </p>
          </div>
          <div class="permission-groups">
            {#each data.catalog as module (module.key)}
              <details class="permission-group" bind:open={expandedModules[module.key]}>
                <summary
                  ><span>{module.label}</span><small
                    >{Object.values(editing.enabled[module.key]).filter(Boolean).length} enabled</small
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
            Saving updates access for {editing.member_count} assigned users on their next request.
          </p>{/if}
        {#if error}<p class="error" role="alert">{error}</p>{/if}
        <div class="save-actions">
          <button class="v2-btn" type="button" disabled={busy} onclick={() => (editing = null)}
            >Cancel</button
          ><button class="v2-btn v2-btn-primary" disabled={busy}
            >{busy ? 'Saving…' : 'Save permission set'}</button
          >
        </div>
      </form>
    {:else}
      <div class="role">
        <div>
          <h2><ShieldCheck size={17} />Super Admin</h2>
          <p>Organization creator. Full access and exclusive control over other administrators.</p>
        </div>
        <span class="protected">Creator only</span>
      </div>
      <div class="role">
        <div>
          <h2><ShieldCheck size={17} />Admin</h2>
          <p>
            Full organization access. Manages users, teams, permission sets and CRM configuration.
          </p>
        </div>
        <span class="protected">System role</span>
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
              {role.member_count === 1 ? 'user' : 'users'}
            </p>
          </div>
          <div class="actions">
            <button
              class="v2-btn v2-btn-sm"
              onclick={() =>
                edit({ ...role, id: null, name: `${role.name} copy`, member_count: 0 })}
              aria-label={`Duplicate ${role.name}`}><Copy size={13} />Duplicate</button
            ><button
              class="v2-btn v2-btn-sm"
              onclick={() => edit(role)}
              aria-label={`Edit permissions for ${role.name}`}
              ><Pencil size={13} />Edit permissions</button
            >
          </div>
        </div>{/each}
      {#if form?.saved}<p class="success" role="status">Permission set saved.</p>{/if}
    {/if}
  </div>
</div>

<style>
  .roles-content {
    padding: 24px 28px;
    max-width: 1150px;
  }
  .role {
    display: flex;
    gap: 20px;
    align-items: center;
    justify-content: space-between;
    padding: 22px 0;
    border-bottom: 1px solid var(--v2-line-soft);
  }
  h2 {
    font-size: 15px;
    margin: 0;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .role p,
  .hint {
    color: var(--v2-slate);
    font-size: 12px;
    line-height: 1.6;
  }
  .protected,
  .scope-badge {
    font-size: 11px;
    color: var(--v2-slate);
  }
  .scope-badge {
    border: 1px solid var(--v2-line);
    border-radius: 5px;
    padding: 3px 6px;
    font-weight: 400;
  }
  .identity {
    display: grid;
    grid-template-columns: 1fr 2fr;
    gap: 20px;
    margin-bottom: 24px;
  }
  label {
    display: grid;
    gap: 8px;
    font-size: 13px;
  }
  .scope-panel {
    display: flex;
    align-items: center;
    gap: 28px;
    padding: 18px 20px;
    background: var(--v2-surface, #fff);
    border: 1px solid var(--v2-line);
    border-radius: 10px;
    margin-bottom: 24px;
  }
  .scope-panel label,
  .fixed-scope {
    min-width: 160px;
    display: grid;
    gap: 8px;
    font-size: 13px;
  }
  .scope-panel p {
    font-size: 12px;
    color: var(--v2-slate);
    line-height: 1.6;
    max-width: 550px;
    margin: 0;
  }
  .actions,
  .save-actions {
    display: flex;
    gap: 8px;
  }
  .save-actions {
    position: sticky;
    bottom: 0;
    background: var(--v2-surface, #fff);
    border-top: 1px solid var(--v2-line);
    padding: 16px 0;
    justify-content: flex-end;
    margin-top: 20px;
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
    border-radius: 10px;
    background: var(--v2-surface, #fff);
    margin-bottom: 12px;
  }
  .permission-group summary {
    cursor: pointer;
    padding: 17px 20px;
    font-size: 14px;
    font-weight: 600;
  }
  .permission-group summary small {
    float: right;
    font-size: 11px;
    font-weight: 400;
    color: var(--v2-slate);
  }
  .permission-options {
    padding: 0 20px 20px;
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 20px 24px;
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
    font-size: 12px;
  }
  .permission-option small {
    font-size: 11px;
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
    font-size: 12px;
    color: var(--v2-slate);
    padding: 0;
    margin-bottom: 22px;
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
      padding: 16px;
    }
    .role,
    .scope-panel {
      flex-wrap: wrap;
    }
  }
</style>
