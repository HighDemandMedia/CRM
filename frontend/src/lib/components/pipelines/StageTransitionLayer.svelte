<script>
  import { onMount } from 'svelte';
  onMount(() => {
    window.addEventListener('crm-stage-requirements', open);
    return () => window.removeEventListener('crm-stage-requirements', open);
  });
  import { invalidateAll } from '$app/navigation';
  import TeamPanel from '$lib/components/team/TeamPanel.svelte';
  import StageRuleNotice from './StageRuleNotice.svelte';
  import StageRequirementField from './StageRequirementField.svelte';
  let pending = $state(null),
    values = $state({}),
    busy = $state(false),
    error = $state('');
  function open(event) {
    if (busy) return;
    pending = event.detail;
    values = {};
    error = '';
    for (const f of pending.issue.fields || [])
      values[f.key] =
        f.multiple === true ||
        f.multiple === 'True' ||
        f.field_type === 'multi_select' ||
        f.key === 'pages'
          ? []
          : '';
  }
  async function save(event) {
    event.preventDefault();
    busy = true;
    error = '';
    try {
      const changes = { ...pending.values };
      for (const f of pending.issue.fields) {
        if (f.is_read_only === true || f.is_read_only === 'True') continue;
        let v = values[f.key];
        if (f.field_type === 'checkbox') v = v === 'true';
        if (f.field_type === 'list' && typeof v === 'string') v = JSON.parse(v);
        if (f.field_type === 'datetime' && v) v = new Date(v).toISOString();
        if (f.key.startsWith('custom_fields.'))
          changes.custom_fields = { ...changes.custom_fields, [f.key.slice(14)]: v };
        else changes[f.key] = v;
      }
      const response = await fetch('/api/stage-transition', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target: pending.target, id: pending.id, values: changes })
      });
      const result = await response.json();
      if (!response.ok) {
        error = result.error;
        if (result.stageRequirements) {
          pending = { ...pending, values: changes, issue: result.stageRequirements };
          for (const f of pending.issue.fields)
            if (!(f.key in values))
              values[f.key] = f.multiple === 'True' || f.field_type === 'multi_select' ? [] : '';
        }
        return;
      }
      pending = null;
      try {
        await invalidateAll();
      } catch {
        error = 'Saved. Reload to refresh the view.';
      }
    } catch {
      error = 'Could not save. Check the fields and try again.';
    } finally {
      busy = false;
    }
  }
</script>

{#if pending}<TeamPanel
    title={pending.issue.code === 'source_stage'
      ? 'Stage change blocked'
      : `Move to ${pending.issue.stage_label}`}
    subtitle="The record stays in its current stage until the change is saved."
    {busy}
    onclose={() => {
      pending = null;
      error = '';
    }}
  >
    <form class="panel-form" onsubmit={save}>
      <div class="panel-body">
        <StageRuleNotice
          issue={pending.issue}
          completion
        />{#each pending.issue.fields || [] as field (field.key)}<StageRequirementField
            {field}
            bind:value={values[field.key]}
          />{/each}{#if error}<p class="panel-error" role="alert">{error}</p>{/if}
      </div>
      <div class="panel-footer">
        <button type="button" class="v2-btn" disabled={busy} onclick={() => (pending = null)}
          >Cancel</button
        >{#if pending.issue.code === 'missing_properties'}<button
            class="v2-btn v2-btn-primary"
            disabled={busy ||
              pending.issue.fields.some(
                (f) => f.is_read_only === true || f.is_read_only === 'True'
              )}>{busy ? 'Saving…' : 'Save and move'}</button
          >{/if}
      </div>
    </form></TeamPanel
  >{/if}
