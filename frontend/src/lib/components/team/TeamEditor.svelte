<script>
  import { enhance } from '$app/forms';
  import { untrack } from 'svelte';
  import TaskAssignees from '$lib/components/tasks/TaskAssignees.svelte';
  import TeamPanel from './TeamPanel.svelte';
  let { team, people, onclose } = $props();
  let selected = $state(untrack(() => [...(team.members ?? [])]));
  let busy = $state(false),
    error = $state('');
</script>

<TeamPanel
  title={team.id ? 'Edit team' : 'Create team'}
  subtitle="Organize users who work together."
  {busy}
  {onclose}
>
  <form
    class="panel-form"
    method="POST"
    action="?/saveTeam"
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
                ? String(result.data?.error || 'Could not save team.')
                : 'Could not save team. Please try again.';
        } finally {
          busy = false;
        }
      };
    }}
  >
    <div class="panel-body">
      <input type="hidden" name="id" value={team.id ?? ''} />
      <label class="field"
        >Team name<input
          class="v2-input"
          name="name"
          value={team.name ?? ''}
          placeholder="e.g. Sales"
          required
          maxlength="100"
          disabled={busy}
        /></label
      >
      <label class="field"
        >Description <span class="optional">Optional</span><textarea
          class="v2-input"
          name="description"
          rows="3"
          placeholder="What does this team work on?"
          disabled={busy}>{team.description ?? ''}</textarea
        ></label
      >
      <TaskAssignees
        label="Members"
        fieldName="members"
        people={people.filter((p) => p.is_active || selected.includes(p.id))}
        bind:selected
        disabled={busy}
      />
      {#if error}<p role="alert" class="panel-error">{error}</p>{/if}
    </div>
    <footer class="panel-footer">
      <button class="v2-btn" type="button" disabled={busy} onclick={onclose}>Cancel</button><button
        class="v2-btn v2-btn-primary"
        disabled={busy}>{busy ? 'Saving…' : team.id ? 'Save changes' : 'Create team'}</button
      >
    </footer>
  </form>
</TeamPanel>

<style>
  .optional {
    font-size: 11px;
    color: var(--v2-slate);
    font-weight: 400;
  }
  .field:has(.optional) {
    position: relative;
  }
  .optional {
    position: absolute;
    right: 0;
    top: 0;
  }
  textarea {
    resize: vertical;
    min-height: 88px;
  }
</style>
