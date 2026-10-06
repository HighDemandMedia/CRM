<script>
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();

  import { deserialize } from '$app/forms';
  import { invalidateAll } from '$app/navigation';
  import { untrack, tick } from 'svelte';
  import TeamPanel from '$lib/components/team/TeamPanel.svelte';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import { ArrowUp, ArrowDown, ChevronRight, Plus, Trash2 } from '@lucide/svelte';
  let { data } = $props();
  let target = $state('Contact');
  let drafts = $state(untrack(() => structuredClone(data.pipelines)));
  let revision = $state(untrack(() => data.revision));
  let busy = $state(false);
  let expanded = $state('');
  let stagePanel = $state('');
  let stageName = $state('');
  let stagePercentage = $state(0);
  let removing = $state(null);
  let destination = $state('');
  let stages = $derived(drafts[target].stages);
  let error = $state('');
  let requiredFields = $state([]);
  let allowedFrom = $state([]);
  let selectedStage = $derived(stages.find((stage) => stage.key === expanded));
  let properties = $derived(data.pipelines[target].properties);

  async function persist(next, additions = [], removals = {}) {
    if (busy || !data.can_edit) return false;
    busy = true;
    error = '';
    const body = new FormData();
    body.set('target_model', target);
    body.set('revision', revision);
    body.set('stages', JSON.stringify(next));
    body.set('additions', JSON.stringify(additions));
    body.set('removals', JSON.stringify(removals));
    try {
      const response = await fetch('?/save', {
        method: 'POST',
        body,
        headers: { 'x-sveltekit-action': 'true' }
      });
      const result = deserialize(await response.text());
      if (result.type !== 'success')
        throw new Error(
          String(
            result.type === 'failure'
              ? result.data?.error || 'Could not save. Your change was not applied.'
              : 'Could not save. Please reload and try again.'
          )
        );
      revision = result.data.revision;
      drafts[target].stages = next;
      // Refresh shared configuration and counts only after the write succeeds.
      try {
        await invalidateAll();
        drafts = structuredClone(data.pipelines);
        revision = data.revision;
      } catch {
        // The save succeeded; keep its returned revision if refreshing is unavailable.
      }
      return true;
    } catch (cause) {
      error = cause.message || 'Could not save. Please try again.';
      return false;
    } finally {
      busy = false;
    }
  }
  function editField(stage, field, event) {
    const input = event.currentTarget;
    if (!input.reportValidity()) return;
    const value = field === 'percentage' ? Number(input.value) : input.value.trim();
    if (stage[field] === value) return;
    const next = stages.map((row) =>
      row.key === stage.key ? { ...row, [field]: value } : { ...row }
    );
    void persist(next).then((ok) => {
      if (!ok) input.value = String(stage[field]);
    });
  }
  function move(index, offset) {
    const next = stages.map((stage) => ({ ...stage }));
    [next[index], next[index + offset]] = [next[index + offset], next[index]];
    void persist(next);
  }
  function openRules(stage) {
    requiredFields = [...stage.required_fields];
    allowedFrom = [...stage.allowed_from];
    error = '';
    expanded = stage.key;
  }
  async function saveRules() {
    await tick();
    const next = stages.map((stage) =>
      stage.key === expanded
        ? { ...stage, required_fields: [...requiredFields], allowed_from: [...allowedFrom] }
        : { ...stage }
    );
    if (!(await persist(next))) {
      requiredFields = [...selectedStage.required_fields];
      allowedFrom = [...selectedStage.allowed_from];
    }
  }
  async function addStage(event) {
    event.preventDefault();
    const label = stageName.trim();
    if (!label || stages.some((stage) => stage.label.toLowerCase() === label.toLowerCase())) {
      error = 'Choose a unique stage name.';
      return;
    }
    const slug =
      label
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '_')
        .replace(/^_|_$/g, '')
        .slice(0, 18) || 'stage';
    const key = 'custom_' + slug + '_' + crypto.randomUUID().slice(0, 6);
    if (
      await persist(
        [
          ...stages,
          {
            key,
            label,
            percentage: stagePercentage,
            required_fields: [],
            allowed_from: [],
            record_count: 0,
            protected: false
          }
        ],
        [key]
      )
    )
      stagePanel = '';
  }
  async function removeStage(event) {
    event.preventDefault();
    const next = stages
      .filter((stage) => stage.key !== removing.key)
      .map((stage) => ({
        ...stage,
        allowed_from: stage.allowed_from.filter((key) => key !== removing.key)
      }));
    if (await persist(next, [], { [removing.key]: destination || null })) {
      removing = null;
      stagePanel = '';
    }
  }
</script>

<PageHeader title={ui('Pipelines')} />
<div class="pipeline-settings">
  <div class="toolbar">
    <label
      >{ui('Object')}<select
        class="v2-input"
        bind:value={target}
        disabled={busy}
        onchange={() => {
          expanded = '';
          error = '';
        }}
      >
        {#each data.objects as object}<option value={object.value}>{object.label}</option>{/each}
      </select></label
    >
    {#if data.can_edit}<button
        class="v2-btn v2-btn-primary add-stage"
        disabled={busy}
        onclick={() => {
          stageName = '';
          stagePercentage = 0;
          error = '';
          stagePanel = 'add';
        }}><Plus size={16} />{ui('Add stage')}</button
      >{/if}
  </div>
  <div class="table-wrap">
    <table>
      <thead
        ><tr
          ><th>{ui('Order')}</th><th>{ui('Stage name')}</th><th>{ui('Internal name')}</th><th
            >{target === 'Opportunity' ? ui('Close probability') : ui('Progress')}</th
          ><th>{ui('Entry rules')}</th><th><span class="sr-only">{ui('Remove stage')}</span></th
          ></tr
        ></thead
      >
      <tbody>
        {#each stages as stage, index (stage.key)}
          <tr>
            <td
              ><div class="order">
                <span>{index + 1}</span><button
                  type="button"
                  class="v2-btn v2-btn-quiet"
                  disabled={!data.can_edit || busy || index === 0}
                  aria-label={`Move ${stage.label} up`}
                  onclick={() => move(index, -1)}><ArrowUp size={14} /></button
                ><button
                  type="button"
                  class="v2-btn v2-btn-quiet"
                  disabled={!data.can_edit || busy || index === stages.length - 1}
                  aria-label={`Move ${stage.label} down`}
                  onclick={() => move(index, 1)}><ArrowDown size={14} /></button
                >
              </div></td
            >
            <td
              ><input
                class="v2-input"
                aria-label={`Stage name ${stage.key}`}
                value={stage.label}
                onchange={(event) => editField(stage, 'label', event)}
                required
                maxlength="100"
                disabled={!data.can_edit || busy}
              /></td
            >
            <td><code>{stage.key}</code></td>
            <td
              ><div class="percentage">
                <input
                  class="v2-input"
                  type="number"
                  min="0"
                  max="100"
                  step="1"
                  required
                  aria-label={`Percentage ${stage.label}`}
                  value={stage.percentage}
                  onchange={(event) => editField(stage, 'percentage', event)}
                  disabled={!data.can_edit || busy}
                /><span>%</span>
              </div></td
            >
            <td
              ><button
                class="v2-btn v2-btn-quiet"
                type="button"
                aria-haspopup="dialog"
                disabled={busy}
                onclick={() => openRules(stage)}
                >{stage.required_fields.length + stage.allowed_from.length
                  ? `${stage.required_fields.length} required · ${stage.allowed_from.length || 'Any'} origin`
                  : ui('Configure')}<ChevronRight size={14} /></button
              ></td
            >
            <td
              >{#if data.can_edit}<button
                  type="button"
                  class="v2-btn v2-btn-quiet"
                  aria-label={`Remove ${stage.label}`}
                  title={stage.protected
                    ? ui('System default stages cannot be removed')
                    : ui('Remove stage')}
                  disabled={busy || stage.protected}
                  onclick={() => {
                    removing = stage;
                    destination = '';
                    error = '';
                    stagePanel = 'remove';
                  }}><Trash2 size={16} /></button
                >{/if}</td
            >
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
  {#if error}<p class="error" role="alert">{ui(error)}</p>{/if}
</div>

{#if selectedStage}
  <TeamPanel
    title={ui('Entry rules')}
    subtitle={`${data.objects.find((object) => object.value === target)?.label} · ${selectedStage.label}`}
    {busy}
    onclose={() => {
      expanded = '';
      error = '';
    }}
  >
    <div class="panel-form">
      <div class="panel-body rules">
        <fieldset disabled={!data.can_edit || busy}>
          <legend>{ui('Required properties')}</legend>
          <p>{ui('Must have a value before entering this stage.')}</p>
          <div class="choices">
            {#each properties as property}
              <label
                ><input
                  type="checkbox"
                  value={property.key}
                  bind:group={requiredFields}
                  onchange={saveRules}
                /><span>{property.label}<code>{property.key}</code></span></label
              >
            {/each}
          </div>
        </fieldset>
        <fieldset disabled={!data.can_edit || busy}>
          <legend>{ui('Allowed source stages')}</legend>
          <p>{ui('Leave empty to allow entry from any stage, including new records.')}</p>
          <div class="choices">
            {#each stages.filter((stage) => stage.key !== expanded) as source}
              <label
                ><input
                  type="checkbox"
                  value={source.key}
                  bind:group={allowedFrom}
                  onchange={saveRules}
                />{source.label}</label
              >
            {/each}
          </div>
        </fieldset>
      </div>
      {#if error}<p class="panel-error" role="alert">{ui(error)}</p>{/if}
      <div class="panel-footer">
        <button
          class="v2-btn"
          type="button"
          disabled={busy}
          onclick={() => {
            expanded = '';
            error = '';
          }}>{ui('Close')}</button
        >
      </div>
    </div>
  </TeamPanel>
{/if}

{#if stagePanel}
  <TeamPanel
    title={stagePanel === 'add' ? ui('Add stage') : ui('Remove stage')}
    subtitle={data.objects.find((object) => object.value === target)?.label}
    {busy}
    onclose={() => {
      stagePanel = '';
      error = '';
    }}
  >
    <form class="panel-form" onsubmit={stagePanel === 'add' ? addStage : removeStage}>
      <fieldset class="panel-body stage-fields" disabled={busy}>
        {#if stagePanel === 'add'}
          <label
            >{ui('Stage name')}<input
              class="v2-input"
              bind:value={stageName}
              required
              maxlength="100"
            /></label
          >
          <label
            >{target === 'Opportunity' ? ui('Close probability (%)') : ui('Progress (%)')}<input
              class="v2-input"
              type="number"
              min="0"
              max="100"
              step="1"
              required
              bind:value={stagePercentage}
            /></label
          >
          <p class="hint">
            {ui(
              'An internal name is generated once and stays fixed. Configure entry rules after adding the stage.'
            )}
          </p>
        {:else if removing}
          <p>{ui('Remove')} <strong>{removing.label}</strong> {ui('from this pipeline?')}</p>
          <p class="hint">
            {removing.record_count || 0}
            {ui(
              'records currently in this stage. Records will be moved, never deleted. References to this stage in entry rules will be removed. A rule left with no source stages allows entry from any stage.'
            )}
          </p>
          <label
            >{ui('Move records to')}<select
              class="v2-input"
              bind:value={destination}
              required={Boolean(removing.record_count)}
            >
              <option value=""
                >{removing.record_count
                  ? ui('Select a destination')
                  : ui('No records to move')}</option
              >
              {#each stages.filter((stage) => stage.key !== removing.key) as stage}<option
                  value={stage.key}>{stage.label}</option
                >{/each}
            </select></label
          >
          <p class="hint">
            {ui(
              'Destination requirements still apply. Confirming removes this stage and moves its records.'
            )}
          </p>
        {/if}
        {#if error}<p class="error" role="alert">{ui(error)}</p>{/if}
      </fieldset>
      <div class="panel-footer">
        <button
          class="v2-btn"
          type="button"
          disabled={busy}
          onclick={() => {
            stagePanel = '';
            error = '';
          }}>{ui('Cancel')}</button
        ><button class="v2-btn v2-btn-primary" disabled={busy}
          >{busy
            ? ui('Saving…')
            : stagePanel === 'add'
              ? ui('Add stage')
              : ui('Remove stage')}</button
        >
      </div>
    </form>
  </TeamPanel>
{/if}

<style>
  .add-stage {
    margin-left: auto;
  }
  .stage-fields {
    display: grid;
    align-content: start;
    gap: var(--crm-space-5);
    padding: var(--crm-space-6);
  }
  .stage-fields label {
    display: grid;
    gap: var(--crm-space-2);
  }
  .stage-fields p {
    margin: 0;
  }
  .pipeline-settings {
    padding: var(--crm-space-6) 30px;
  }
  .toolbar {
    display: flex;
    align-items: end;
    gap: var(--crm-space-6);
    margin-bottom: var(--crm-space-6);
  }
  .toolbar label {
    display: grid;
    gap: var(--crm-space-2);
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
    width: 230px;
  }
  .hint {
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
    padding-bottom: 10px;
  }
  .table-wrap {
    overflow: auto;
    background: var(--v2-card, var(--crm-surface));
    border: 1px solid var(--v2-line);
    border-radius: var(--crm-radius-lg);
  }
  table {
    width: 100%;
    border-collapse: collapse;
    text-align: left;
    font-size: var(--crm-text-sm);
  }
  th,
  td {
    padding: 14px;
    border-bottom: 1px solid var(--v2-line-soft);
  }
  th {
    font-weight: 500;
    color: var(--v2-slate);
    font-size: var(--crm-text-xs);
    white-space: nowrap;
  }
  tr:last-child td {
    border-bottom: 0;
  }
  code {
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
  }
  .order,
  .percentage {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .order button {
    padding: 5px;
  }
  .percentage input {
    width: 76px;
  }
  .rules {
    display: grid;
    align-content: start;
    gap: 28px;
  }
  fieldset {
    border: 0;
    margin: 0;
    padding: 0;
    min-width: 0;
  }
  legend {
    font-weight: 600;
  }
  .rules p {
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
    margin: var(--crm-space-2) 0 14px;
  }
  .choices {
    display: grid;
    gap: 10px;
  }
  .choices label {
    display: flex;
    gap: var(--crm-space-2);
    align-items: center;
    font-size: var(--crm-text-xs);
  }
  .choices label {
    padding: var(--crm-space-2) 0;
    align-items: flex-start;
  }
  .choices input {
    margin-top: 3px;
    flex-shrink: 0;
  }
  .choices span {
    min-width: 0;
  }
  .choices code {
    display: block;
    overflow-wrap: anywhere;
    margin-top: 3px;
  }
  .panel-error {
    margin: 0;
    padding: var(--crm-space-3) var(--crm-space-6);
  }

  .error {
    color: var(--v2-rust);
    font-size: var(--crm-text-sm);
  }
  @media (max-width: 850px) {
    .rules {
      grid-template-columns: 1fr;
    }
    .pipeline-settings {
      padding: var(--crm-space-4);
    }
  }
</style>
