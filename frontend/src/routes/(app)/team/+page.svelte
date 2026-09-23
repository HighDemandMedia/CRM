<script>
  import { resolve } from '$app/paths';
  import { enhance } from '$app/forms';
  import {
    UserPlus,
    UsersRound,
    Search,
    Plus,
    ArrowUpRight,
    Pencil,
    ShieldCheck
  } from '@lucide/svelte';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import Avatar from '$lib/v2/components/Avatar.svelte';
  import NextAction from '$lib/v2/components/NextAction.svelte';
  import { relativeDays } from '$lib/v2/format.js';
  import MemberActions from '$lib/components/team/MemberActions.svelte';
  import TeamEditor from '$lib/components/team/TeamEditor.svelte';
  import InviteMember from '$lib/components/team/InviteMember.svelte';
  let { data, form } = $props();
  let activeTab = $state('users'),
    search = $state(''),
    status = $state('all'),
    role = $state(''),
    teamFilter = $state('');
  let inviting = $state(false),
    editingTeam = $state(null),
    busy = $state(false);
  const members = $derived([...(data.active || []), ...(data.inactive || [])]);
  const matches = (text) =>
    String(text || '')
      .toLowerCase()
      .includes(search.trim().toLowerCase());
  const roleName = (m) =>
    m.is_super_admin
      ? 'Super Admin'
      : m.role === 'ADMIN'
        ? 'Admin'
        : m.access_role_name || 'Member';
  const filteredMembers = $derived(
    members.filter(
      (m) =>
        matches(`${m.name} ${m.email} ${m.teams.join(' ')}`) &&
        (status === 'all' || (status === 'active' ? m.is_active : !m.is_active)) &&
        (!role || roleName(m) === role) &&
        (!teamFilter || data.teams.find((t) => t.id === teamFilter)?.members.includes(m.id))
    )
  );
  const filteredTeams = $derived(
    (data.teams || []).filter((t) =>
      matches(
        `${t.name} ${t.description} ${members
          .filter((m) => t.members.includes(m.id))
          .map((m) => m.name)
          .join(' ')}`
      )
    )
  );
  const invitations = $derived((data.invitations || []).filter((i) => i.status !== 'Accepted'));
  function tab(id) {
    activeTab = id;
    search = '';
  }
  const working = () => {
    busy = true;
    return async ({ update }) => {
      try {
        await update();
      } finally {
        busy = false;
      }
    };
  };
</script>

{#if data.forbidden}
  <PageHeader title="Users & Teams" />
  <div class="v2-pad">
    <NextAction
      label="Admins only"
      text="An organization admin can invite users, manage teams and change access."
    />
  </div>
{:else}
  <PageHeader title="Users & Teams">
    {#snippet sub()}<span
        >{data.active.length} active · {data.teams.length}
        {data.teams.length === 1 ? 'team' : 'teams'}</span
      >{/snippet}
    {#snippet actions()}
      {#if activeTab === 'teams'}<button
          class="v2-btn v2-btn-primary"
          onclick={() => (editingTeam = {})}><Plus size={16} />Create team</button
        >{:else}<button class="v2-btn v2-btn-primary" onclick={() => (inviting = true)}
          ><UserPlus size={16} />Invite user</button
        >{/if}
    {/snippet}
  </PageHeader>
  <nav class="team-tabs" aria-label="Users and teams sections">
    {#each [['users', 'Users', members.length], ['teams', 'Teams', data.teams.length], ['invitations', 'Invitations', invitations.length]] as [id, label, total]}
      <button
        class:active={activeTab === id}
        aria-pressed={activeTab === id}
        onclick={() => tab(id)}>{label}<span>{total}</span></button
      >
    {/each}
    <a href={resolve('/settings/roles')}>Roles &amp; permissions<ArrowUpRight size={14} /></a>
  </nav>
  <div class="v2-scroll">
    <div class="team-content">
      {#if form?.invited}<p class="notice" role="status">
          Invitation sent to {form.invited}.
        </p>{:else if form?.error}<p class="error" role="alert">{form.error}</p>{/if}
      {#if data.totals.tokens_on_deactivated}<p class="notice">
          Deactivated users have {data.totals.tokens_on_deactivated} dormant access tokens.
          <a href={resolve('/settings/api-tokens')}>Review tokens</a>
        </p>{/if}
      <div class="toolbar">
        <label class="search"
          ><Search size={16} /><input
            type="search"
            aria-label={`Search ${activeTab}`}
            placeholder={activeTab === 'users'
              ? 'Search name or email'
              : activeTab === 'teams'
                ? 'Search teams'
                : 'Search invitations'}
            bind:value={search}
          /></label
        >
        {#if activeTab === 'users'}
          <select class="v2-input filter" aria-label="Filter users by status" bind:value={status}
            ><option value="all">All statuses</option><option value="active">Active</option><option
              value="inactive">Deactivated</option
            ></select
          >
          <select class="v2-input filter" aria-label="Filter users by role" bind:value={role}
            ><option value="">All roles</option
            >{#each [...new Set(members.map(roleName))] as name}<option value={name}>{name}</option
              >{/each}</select
          >
          <select class="v2-input filter" aria-label="Filter users by team" bind:value={teamFilter}
            ><option value="">All teams</option>{#each data.teams as t}<option value={t.id}
                >{t.name}</option
              >{/each}</select
          >
        {/if}
      </div>
      {#if activeTab === 'users'}
        <div class="table-wrap">
          <table class="access-table">
            <thead
              ><tr
                ><th>User</th><th>Permission set</th><th>Teams</th><th>Status</th><th
                  >Last sign-in</th
                ><th><span class="sr-only">Actions</span></th></tr
              ></thead
            >
            <tbody
              >{#each filteredMembers as m (m.id)}<tr>
                  <td
                    ><div class="person">
                      <Avatar name={m.name} size={30} />
                      <div>
                        <strong
                          >{m.name}{#if m.is_you}<small class="you">You</small>{/if}</strong
                        ><span>{m.email}</span>
                      </div>
                    </div></td
                  >
                  <td
                    ><span class="role-badge" class:admin={m.role === 'ADMIN'}
                      >{#if m.is_super_admin}<ShieldCheck size={13} />{/if}{roleName(m)}</span
                    ></td
                  >
                  <td
                    ><div class="team-chips">
                      {#each data.teams.filter((t) => t.members.includes(m.id)) as t}<button
                          onclick={() => (editingTeam = t)}>{t.name}</button
                        >{:else}<span class="muted">—</span>{/each}
                    </div></td
                  >
                  <td
                    ><span class="status" class:inactive={!m.is_active}
                      ><i></i>{m.is_active ? 'Active' : 'Deactivated'}</span
                    ></td
                  >
                  <td class="muted">{m.last_login ? relativeDays(m.last_login) : 'Not yet'}</td>
                  <td class="row-actions"
                    >{#if m.is_super_admin}<span class="protected" title="Organization creator"
                        >Protected</span
                      >{:else if m.role === 'ADMIN' && !data.isSuperAdmin}<span
                        class="protected"
                        title="Managed by Super Admin">Protected</span
                      >{:else if m.is_you}<span class="muted">—</span>{:else}<MemberActions
                        member={m}
                        roles={data.accessRoles}
                        isSuperAdmin={data.isSuperAdmin}
                        isLastAdmin={m.user_id === data.last_admin_id}
                      />{/if}</td
                  >
                </tr>{:else}<tr
                  ><td colspan="6"
                    ><div class="empty">
                      <UsersRound size={26} /><strong>No users found</strong><span
                        >Try another search or filter.</span
                      >
                    </div></td
                  ></tr
                >{/each}</tbody
            >
          </table>
        </div>
      {:else if activeTab === 'teams'}
        <div class="table-wrap">
          <table class="access-table teams-table">
            <thead
              ><tr><th>Team</th><th>Members</th><th><span class="sr-only">Actions</span></th></tr
              ></thead
            >
            <tbody
              >{#each filteredTeams as t (t.id)}<tr>
                  <td
                    ><div class="team-name">
                      <span class="team-icon"><UsersRound size={19} /></span>
                      <div>
                        <button class="name-link" onclick={() => (editingTeam = t)}>{t.name}</button
                        >
                        <p>{t.description || 'No description'}</p>
                      </div>
                    </div></td
                  >
                  <td
                    ><div class="member-preview">
                      {#each members
                        .filter((m) => t.members.includes(m.id))
                        .slice(0, 3) as person}<span class="member-chip">{person.name}</span
                        >{/each}{#if t.member_count > 3}<span class="muted"
                          >+{t.member_count - 3}</span
                        >{/if}{#if !t.member_count}<span class="muted">No members</span>{/if}
                    </div>
                    <small class="member-total"
                      >{t.member_count} {t.member_count === 1 ? 'member' : 'members'}</small
                    ></td
                  >
                  <td class="row-actions"
                    ><button
                      class="v2-btn v2-btn-sm"
                      onclick={() => (editingTeam = t)}
                      aria-label={`Edit ${t.name}`}><Pencil size={14} />Edit</button
                    ></td
                  >
                </tr>{:else}<tr
                  ><td colspan="3"
                    ><div class="empty">
                      <UsersRound size={26} /><strong
                        >{search ? 'No matching teams' : 'No teams yet'}</strong
                      ><span
                        >{search
                          ? 'Try another search.'
                          : 'Create a team and choose its members.'}</span
                      >{#if !search}<button class="v2-btn" onclick={() => (editingTeam = {})}
                          >Create team</button
                        >{/if}
                    </div></td
                  ></tr
                >{/each}</tbody
            >
          </table>
        </div>
      {:else}
        <div class="table-wrap">
          <table class="access-table">
            <thead
              ><tr
                ><th>Email</th><th>Permission set</th><th>Status</th><th
                  ><span class="sr-only">Actions</span></th
                ></tr
              ></thead
            >
            <tbody
              >{#each invitations.filter((i) => matches(i.email)) as invite}<tr>
                  <td><strong>{invite.email}</strong></td><td
                    ><span class="role-badge"
                      >{invite.role === 'ADMIN'
                        ? 'Admin'
                        : invite.access_role_name || 'Member'}</span
                    ></td
                  ><td><span class="muted">{invite.status}</span></td>
                  <td
                    ><div class="invitation-actions">
                      {#if data.isSuperAdmin || invite.role !== 'ADMIN'}
                        <form method="POST" action="?/invite" use:enhance={working}>
                          <input type="hidden" name="email" value={invite.email} /><input
                            type="hidden"
                            name="role"
                            value={invite.role}
                          /><input
                            type="hidden"
                            name="access_role_id"
                            value={invite.access_role_id || ''}
                          /><button class="v2-btn v2-btn-sm" disabled={busy}>Resend</button>
                        </form>
                        {#if invite.status === 'Pending'}<form
                            method="POST"
                            action="?/cancelInvite"
                            use:enhance={working}
                          >
                            <input type="hidden" name="id" value={invite.id} /><button
                              class="v2-btn v2-btn-sm"
                              disabled={busy}>Cancel invite</button
                            >
                          </form>{/if}
                      {/if}
                    </div></td
                  >
                </tr>{:else}<tr
                  ><td colspan="4"
                    ><div class="empty">
                      <UserPlus size={26} /><strong
                        >{search ? 'No matching invitations' : 'No invitations'}</strong
                      ><span>Invitations appear here until accepted.</span>
                    </div></td
                  ></tr
                >{/each}</tbody
            >
          </table>
        </div>
      {/if}
    </div>
  </div>
  {#if inviting}<InviteMember
      roles={data.accessRoles}
      isSuperAdmin={data.isSuperAdmin}
      onclose={() => (inviting = false)}
    />{/if}
  {#if editingTeam}{#key editingTeam}<TeamEditor
        team={editingTeam}
        people={members}
        onclose={() => (editingTeam = null)}
      />{/key}{/if}
{/if}

<style>
  .team-tabs {
    display: flex;
    align-items: center;
    gap: 24px;
    padding: 0 24px;
    border-bottom: 1px solid var(--v2-line);
    flex-wrap: wrap;
    flex-shrink: 0;
  }
  .team-tabs > button {
    display: flex;
    align-items: center;
    gap: 8px;
    border: 0;
    border-bottom: 2px solid transparent;
    background: none;
    padding: 14px 0;
    font: inherit;
    font-size: 13px;
    color: var(--v2-slate);
    cursor: pointer;
  }
  .team-tabs > button.active {
    border-bottom-color: var(--v2-ink);
    color: var(--v2-ink);
    font-weight: 600;
  }
  .team-tabs button > span {
    font-size: 10px;
    background: var(--v2-hover);
    padding: 1px 6px;
    border-radius: 5px;
    color: var(--v2-slate);
  }
  .team-tabs a {
    display: flex;
    align-items: center;
    gap: 5px;
    margin-left: auto;
    font-size: 12px;
    color: var(--v2-slate);
  }
  .team-tabs button:focus:not(:focus-visible) {
    outline: none;
  }
  .team-content {
    padding: 20px 24px 32px;
  }
  .toolbar {
    display: flex;
    gap: 8px;
    align-items: center;
    flex-wrap: wrap;
    margin-bottom: 16px;
  }
  .search {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 9px 12px;
    background: var(--v2-card);
    border: 1px solid var(--v2-line);
    border-radius: 8px;
    color: var(--v2-slate);
    width: 280px;
    max-width: 100%;
    min-height: 38px;
  }
  .search input {
    background: none;
    border: 0;
    outline: none;
    width: 100%;
    min-width: 0;
    color: var(--v2-ink);
    font-size: 12px;
  }
  .search:focus-within {
    outline: 2px solid var(--v2-slate);
    outline-offset: 2px;
  }
  .filter {
    width: auto;
    min-width: 110px;
    max-width: 200px;
    height: 38px;
    font-size: 12px;
  }
  .table-wrap {
    overflow-x: auto;
    border: 1px solid var(--v2-line);
    border-radius: 12px;
    background: var(--v2-card);
  }
  .access-table {
    border-collapse: collapse;
    width: 100%;
    font-size: 13px;
    text-align: left;
  }
  .access-table th {
    font-size: 11px;
    color: var(--v2-slate);
    font-weight: 500;
    background: var(--v2-hover);
    padding: 12px 16px;
    white-space: nowrap;
  }
  .access-table td {
    padding: 16px;
    border-top: 1px solid var(--v2-line-soft);
    vertical-align: middle;
  }
  .access-table tr:hover td {
    background: var(--v2-hover);
  }
  .access-table strong {
    font-weight: 550;
  }
  .person {
    display: flex;
    align-items: center;
    gap: 10px;
    min-width: 190px;
  }
  .person strong {
    display: flex;
    align-items: center;
    gap: 7px;
  }
  .person > div {
    min-width: 0;
  }
  .person span {
    display: block;
    color: var(--v2-slate);
    font-size: 11px;
    margin-top: 3px;
    overflow-wrap: anywhere;
  }
  .you {
    font-size: 10px;
    font-weight: 400;
    color: var(--v2-slate);
  }
  .role-badge {
    display: inline-flex;
    gap: 5px;
    align-items: center;
    padding: 4px 8px;
    border-radius: 6px;
    background: var(--v2-hover);
    color: var(--v2-slate);
    font-size: 11px;
    white-space: nowrap;
  }
  .role-badge.admin {
    background: #ece8f1;
    color: #62576d;
  }
  .team-chips,
  .member-preview {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    min-width: 100px;
  }
  .team-chips button,
  .member-chip {
    font-size: 11px;
    border: 1px solid var(--v2-line);
    border-radius: 5px;
    padding: 3px 7px;
    background: transparent;
    color: var(--v2-ink);
  }
  .team-chips button:hover {
    text-decoration: underline;
  }
  .status {
    display: inline-flex;
    gap: 6px;
    align-items: center;
    font-size: 11px;
    white-space: nowrap;
    color: var(--v2-slate);
  }
  .status i {
    width: 6px;
    height: 6px;
    border-radius: 100%;
    background: var(--v2-moss, #61755b);
  }
  .status.inactive i {
    background: var(--v2-slate);
  }
  .muted {
    color: var(--v2-slate);
    font-size: 12px;
  }
  .protected {
    font-size: 10px;
    color: var(--v2-slate);
  }
  .row-actions {
    text-align: right;
    width: 72px;
    white-space: nowrap;
  }
  .team-name {
    display: flex;
    align-items: center;
    gap: 12px;
    min-width: 200px;
  }
  .team-icon {
    display: grid;
    place-items: center;
    width: 36px;
    height: 36px;
    border-radius: 9px;
    background: var(--v2-hover);
    color: var(--v2-slate);
    flex-shrink: 0;
  }
  .name-link {
    border: 0;
    background: none;
    padding: 0;
    font-weight: 550;
    color: var(--v2-ink);
    text-align: left;
    cursor: pointer;
  }
  .name-link:hover {
    text-decoration: underline;
  }
  .team-name p {
    font-size: 11px;
    color: var(--v2-slate);
    margin: 4px 0 0;
    max-width: 360px;
    overflow-wrap: anywhere;
  }
  .member-total {
    display: block;
    font-size: 10px;
    color: var(--v2-slate);
    margin-top: 6px;
  }
  .teams-table td:first-child {
    width: 46%;
  }
  .invitation-actions {
    display: flex;
    gap: 6px;
    justify-content: flex-end;
  }
  .invitation-actions form {
    margin: 0;
  }
  .empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
    padding: 36px 16px;
    color: var(--v2-slate);
    text-align: center;
  }
  .empty strong {
    color: var(--v2-ink);
    font-size: 14px;
  }
  .empty span {
    font-size: 12px;
  }
  .notice,
  .error {
    font-size: 13px;
    margin: 0 0 16px;
    padding: 12px 14px;
    border-radius: 8px;
    background: var(--v2-hover);
  }
  .error {
    color: var(--v2-rust);
  }
  .notice a {
    text-decoration: underline;
  }
  @media (max-width: 900px) {
    .access-table {
      min-width: 700px;
    }
    .teams-table {
      min-width: 520px;
    }
    .team-tabs a {
      display: none;
    }
    .team-content {
      padding: 16px;
    }
    .team-tabs {
      padding: 0 16px;
      gap: 18px;
    }
    .search {
      width: 100%;
    }
  }
</style>
