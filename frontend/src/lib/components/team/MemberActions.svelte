<script>
  import { enhance } from '$app/forms';
  import { tick } from 'svelte';
  import { Ellipsis, UserCog, UserRoundX, UserRoundCheck, Trash2 } from '@lucide/svelte';
  import * as Menu from '$lib/components/ui/dropdown-menu/index.js';
  import RemoveMember from './RemoveMember.svelte';
  import TeamPanel from './TeamPanel.svelte';

  let { member, roles, isSuperAdmin, isLastAdmin } = $props();
  let menuOpen = $state(false);
  let busy = $state(false);
  let selectedRole = $state('');
  let error = $state('');
  let editing = $state(false);
  let statusForm;
  let removal;
  const currentRole = () => (member.role === 'ADMIN' ? 'ADMIN' : member.access_role_id || '');

  async function editRole() {
    menuOpen = false;
    selectedRole = currentRole();
    error = '';
    await tick();
    editing = true;
  }
  async function remove() {
    menuOpen = false;
    await tick();
    removal.open();
  }
  function saveRole() {
    busy = true;
    error = '';
    return async ({ result, update }) => {
      await update();
      busy = false;
      if (result.type === 'success') editing = false;
      else error = result.data?.error || 'Could not change this role. Please try again.';
    };
  }
  function setStatus() {
    busy = true;
    return async ({ update }) => {
      await update();
      busy = false;
    };
  }
</script>

<Menu.Root bind:open={menuOpen}>
  <Menu.Trigger
    class="v2-btn v2-btn-sm member-menu-trigger"
    aria-label={`Manage ${member.name}`}
    title={`Manage ${member.name}`}
    disabled={busy}
  >
    <Ellipsis size={18} />
  </Menu.Trigger>
  <Menu.Content align="end" class="w-52">
    <Menu.Item disabled={isLastAdmin} onclick={editRole}><UserCog />Change role</Menu.Item>
    <Menu.Item
      disabled={busy || (member.is_active && isLastAdmin)}
      onclick={() => statusForm.requestSubmit()}
    >
      {#if member.is_active}<UserRoundX />Deactivate{:else}<UserRoundCheck />Reactivate{/if}
    </Menu.Item>
    <Menu.Separator />
    <Menu.Item variant="destructive" onclick={remove}><Trash2 />Remove user</Menu.Item>
  </Menu.Content>
</Menu.Root>

<form bind:this={statusForm} method="POST" action="?/setStatus" use:enhance={setStatus} hidden>
  <input type="hidden" name="userId" value={member.user_id} />
  <input type="hidden" name="status" value={member.is_active ? 'Inactive' : 'Active'} />
</form>
<RemoveMember bind:this={removal} id={member.id} hideTrigger />

{#if editing}<TeamPanel
    title="Edit user access"
    subtitle={member.email}
    {busy}
    onclose={() => (editing = false)}
  >
    <form class="panel-form" method="POST" action="?/assignRole" use:enhance={saveRole}>
      <div class="panel-body">
        <p class="person">{member.name}<span>{member.email}</span></p>
        <input type="hidden" name="profileId" value={member.id} />
        <label for={`role-select-${member.id}`}>Permission set</label>
        <select
          id={`role-select-${member.id}`}
          class="v2-input"
          name="role_id"
          bind:value={selectedRole}
          disabled={busy}
          required
        >
          {#if !selectedRole}<option value="" disabled>Choose role</option>{/if}
          {#if isSuperAdmin}<option value="ADMIN">Admin</option>{/if}
          {#each roles as role}<option value={role.id}>{role.name}</option>{/each}
        </select>
        {#if error}<p class="error" role="alert">{error}</p>{/if}
        <div class="access-summary">
          <span>Record access</span><strong
            >{selectedRole === 'ADMIN'
              ? 'Organization'
              : { own: 'Personal', team: 'Team', organization: 'Organization' }[
                  roles.find((r) => r.id === selectedRole)?.scope
                ] || 'Personal'}</strong
          >
        </div>
        <div class="access-summary">
          <span>Teams</span><strong>{member.teams.join(', ') || 'No team assigned'}</strong>
        </div>
        <p class="hint">Team membership is managed from the Teams tab.</p>
      </div>
      <footer class="panel-footer">
        <button class="v2-btn" type="button" disabled={busy} onclick={() => (editing = false)}
          >Cancel</button
        >
        <button
          class="v2-btn v2-btn-primary"
          disabled={busy || !selectedRole || selectedRole === currentRole()}
          >{busy ? 'Saving…' : 'Save role'}</button
        >
      </footer>
    </form>
  </TeamPanel>{/if}

<style>
  :global(.member-menu-trigger) {
    width: 32px;
    height: 32px;
    min-height: 32px;
    padding: 0;
    justify-content: center;
    background: transparent;
    border-color: transparent;
    color: var(--v2-slate);
  }
  :global(.member-menu-trigger:hover),
  :global(.member-menu-trigger[data-state='open']) {
    background: var(--v2-hover);
    border-color: var(--v2-line);
    color: var(--v2-ink);
  }
  .person {
    font-size: 14px;
    font-weight: 600;
    margin: 0 0 24px;
    overflow-wrap: anywhere;
  }
  .person span {
    display: block;
    font-size: 12px;
    font-weight: 400;
    color: var(--v2-slate);
    margin-top: 3px;
  }
  label {
    display: block;
    font-size: 12px;
    font-weight: 500;
    margin-bottom: 7px;
  }
  select {
    width: 100%;
  }
  .access-summary {
    display: flex;
    justify-content: space-between;
    gap: 20px;
    border-bottom: 1px solid var(--v2-line-soft);
    padding: 18px 0;
    font-size: 12px;
  }
  .access-summary span,
  .hint {
    color: var(--v2-slate);
  }
  .access-summary strong {
    font-weight: 500;
    text-align: right;
  }
  .hint {
    font-size: 12px;
    line-height: 1.5;
  }
  .error {
    font-size: 13px;
    color: var(--v2-rust);
  }
</style>
