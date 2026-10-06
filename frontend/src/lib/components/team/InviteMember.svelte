<script>
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();

  import { enhance } from '$app/forms';
  import TeamPanel from './TeamPanel.svelte';
  let { roles, isSuperAdmin, onclose } = $props();
  let role = $state('');
  let busy = $state(false);
  let error = $state('');
  const scope = $derived(
    role === 'ADMIN'
      ? 'Organization'
      : { own: 'Personal', team: 'Team', organization: 'Organization' }[
          roles.find((r) => r.id === role)?.scope || 'own'
        ]
  );
</script>

<TeamPanel
  title={ui('Invite user')}
  subtitle="Give someone access to this organization."
  {busy}
  {onclose}
>
  <form
    method="POST"
    action="?/invite"
    class="panel-form"
    use:enhance={() => {
      busy = true;
      error = '';
      return async ({ result, update }) => {
        try {
          if (result.type === 'success') {
            await update({ reset: false });
            onclose();
          } else
            error =
              result.type === 'failure'
                ? String(
                    /** @type {any} */ (result.data?.invite)?.error || 'Could not send invitation.'
                  )
                : 'Could not send invitation. Please try again.';
        } finally {
          busy = false;
        }
      };
    }}
  >
    <div class="panel-body">
      <label class="field"
        >{ui('Email')}<input
          class="v2-input"
          name="email"
          type="email"
          placeholder="name@company.com"
          required
          disabled={busy}
          autocomplete="email"
        /></label
      >
      <label class="field"
        >{ui('Permission set')}<select class="v2-input" bind:value={role} disabled={busy}
          ><option value="">{ui('Member')}</option
          >{#each roles.filter((r) => r.name !== 'Member') as r}<option value={r.id}
              >{r.name}</option
            >{/each}{#if isSuperAdmin}<option value="ADMIN">{ui('Admin')}</option>{/if}</select
        ><small>{ui('Record access:')} {scope}</small></label
      >
      <input type="hidden" name="role" value={role === 'ADMIN' ? 'ADMIN' : 'USER'} />
      <input
        type="hidden"
        name="access_role_id"
        value={role === 'ADMIN' ? '' : role || roles.find((r) => r.name === 'Member')?.id || ''}
      />
      <p class="invite-note">
        {ui(
          'They’ll receive an email to accept the invitation. You can add them to a team after they join.'
        )}
      </p>
      {#if error}<p class="panel-error" role="alert">{ui(error)}</p>{/if}
    </div>
    <footer class="panel-footer">
      <button class="v2-btn" type="button" disabled={busy} onclick={onclose}>{ui('Cancel')}</button
      ><button class="v2-btn v2-btn-primary" disabled={busy}
        >{busy ? ui('Sending…') : ui('Send invitation')}</button
      >
    </footer>
  </form>
</TeamPanel>

<style>
  .invite-note {
    font-size: var(--crm-text-sm);
    line-height: 1.65;
    color: var(--v2-slate);
    padding: var(--crm-space-4);
    background: var(--v2-hover);
    border-radius: var(--crm-radius-md);
  }
</style>
