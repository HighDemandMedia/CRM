<script>
  import { useI18n } from '$lib/i18n/context.js';
  const { ui, locale } = useI18n();

  import { enhance, deserialize } from '$app/forms';
  import { goto, invalidateAll } from '$app/navigation';
  import { page } from '$app/state';
  import { Plus, Search, LockKeyhole, Pencil, X, GripVertical } from '@lucide/svelte';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import TeamPanel from '$lib/components/team/TeamPanel.svelte';
  import { FIELD_TYPE_LABEL } from '$lib/v2/enums.js';

  let { data, form } = $props();
  let deleteDialog;
  let deleting = $state(null),
    deleteConfirmation = $state(''),
    deleteError = $state(''),
    deleteBusy = $state(false);
  function openDelete(property) {
    deleting = property;
    deleteConfirmation = '';
    deleteError = '';
    deleteDialog.showModal();
  }
  function submitDelete() {
    deleteBusy = true;
    deleteError = '';
    return async ({ result, update }) => {
      try {
        if (result.type === 'success') {
          await update({ reset: false });
          deleteDialog.close();
          deleting = null;
        } else {
          deleteError = result.data?.delete?.error || 'Could not delete the property.';
        }
      } finally {
        deleteBusy = false;
      }
    };
  }
  let dragging = $state(''),
    dropTarget = $state(''),
    ordering = $state(false),
    orderError = $state('');
  const propertyKey = (p) => (p.is_system ? p.key : `custom_fields.${p.key}`);
  async function reorder(from, to) {
    if (!from || from === to || ordering) return;
    const keys = data.properties.map(propertyKey);
    const start = keys.indexOf(from),
      end = keys.indexOf(to);
    if (start < 0 || end < 0) return;
    keys.splice(end, 0, keys.splice(start, 1)[0]);
    ordering = true;
    orderError = '';
    dragging = '';
    dropTarget = '';
    try {
      const body = new FormData();
      body.set('target_model', data.target_model);
      body.set('revision', data.revision);
      body.set('order', JSON.stringify(keys));
      const response = await fetch('?/reorder', {
        method: 'POST',
        body,
        headers: { 'x-sveltekit-action': 'true' }
      });
      const result = deserialize(await response.text());
      if (result.type !== 'success')
        throw new Error(
          result.type === 'failure' ? String(result.data?.error) : 'Could not save the order.'
        );
      await invalidateAll();
    } catch (err) {
      orderError = err.message;
    } finally {
      ordering = false;
    }
  }
  let query = $state('');
  let kind = $state('all');
  let editing = $state(/** @type {any} */ (null));
  let label = $state('');
  let keyOverride = $state(null);
  let fieldType = $state('text');
  let busy = $state(false);
  let error = $state('');
  let options = $state(/** @type {{value: string, label: string}[]} */ ([]));
  const types = {
    ...FIELD_TYPE_LABEL,
    phone: 'Phone',
    email: 'Email',
    url: 'Link',
    datetime: 'Date & time',
    relationship: 'Association',
    multi_select: 'Multiple selection',
    list: 'List'
  };
  let objectLabel = $derived(data.objects.find((o) => o.value === data.target_model)?.label ?? '');
  let rows = $derived(
    data.properties.filter(
      (p) =>
        (kind === 'all' || (kind === 'system' ? p.is_system : !p.is_system)) &&
        `${p.label} ${p.key}`.toLowerCase().includes(query.trim().toLowerCase())
    )
  );
  let key = $derived(
    editing?.key ??
      keyOverride ??
      (
        'custom_' +
        label
          .normalize('NFD')
          .replace(/[\u0300-\u036f]/g, '')
          .toLowerCase()
          .replace(/[^a-z0-9]+/g, '_')
          .replace(/^_+|_+$/g, '')
      ).slice(0, 64)
  );
  function openEditor(property = null) {
    editing = property ?? { new: true };
    label = property?.label ?? '';
    keyOverride = null;
    fieldType = property?.field_type ?? 'text';
    options = (property?.options ?? []).map((o) => ({ ...o }));
    error = '';
  }
  function switchObject(event) {
    const url = new URL(page.url);
    url.searchParams.set('object', event.currentTarget.value);
    query = '';
    goto(url, { keepFocus: true, noScroll: true });
  }
  function submit() {
    busy = true;
    error = '';
    return async ({ result, update }) => {
      busy = false;
      if (result.type === 'success') {
        await update({ reset: false });
        editing = null;
      } else {
        error =
          result.data?.create?.error ??
          result.data?.update?.error ??
          'Could not save the property. Try again.';
      }
    };
  }
</script>

<PageHeader title={ui('Properties')}>
  {#snippet sub()}{ui('Manage the fields used by each CRM object.')}{/snippet}
  {#snippet actions()}
    {#if data.can_edit}<button class="v2-btn v2-btn-primary" onclick={() => openEditor()}
        ><Plus size={16} /> {ui('Create property')}</button
      >{/if}
  {/snippet}
</PageHeader>

<div class="catalog">
  <div class="toolbar">
    <label class="object-field"
      >{ui('Object')}
      <select class="v2-input" value={data.target_model} onchange={switchObject}>
        {#each data.objects as object}<option value={object.value}>{object.label}</option>{/each}
      </select>
    </label>
    <div class="search">
      <Search size={16} /><input
        class="v2-input"
        aria-label={ui('Search properties')}
        placeholder={ui('Search properties')}
        bind:value={query}
      />
    </div>
    <select class="v2-input kind" aria-label={ui('Property origin')} bind:value={kind}>
      <option value="all">{ui('All properties')}</option><option value="system"
        >{ui('System properties')}</option
      ><option value="custom">{ui('Custom properties')}</option>
    </select>
  </div>
  <div class="summary">
    <span>{rows.length} {ui('properties')}</span><span
      >{data.record_count} {objectLabel.toLowerCase()}</span
    >
  </div>
  {#if form?.deactivate?.error || form?.activate?.error}<p class="error" role="alert">
      {form.deactivate?.error ?? form.activate?.error}
    </p>{/if}
  {#if orderError}<p class="v2-error" role="alert">{orderError}</p>{/if}
  {#if ordering}<p role="status">{ui('Saving order…')}</p>{/if}
  <!-- svelte-ignore a11y_no_noninteractive_tabindex (The scroll region needs focus for keyboard scrolling.) -->
  <div class="table-scroll" role="region" aria-label={ui('Properties list')} tabindex="0">
    <table>
      <thead
        ><tr
          ><th>{ui('Property')}</th><th>{ui('Internal name')}</th><th>{ui('Field type')}</th><th
            title={ui('Records with a saved value')}>{ui('Used in records')}</th
          ><th>{ui('Origin')}</th><th><span class="sr-only">{ui('Actions')}</span></th></tr
        ></thead
      >
      <tbody>
        {#each rows as property (property.id)}
          <tr
            class:inactive={!property.is_active}
            class:drop-position={dropTarget === propertyKey(property)}
            ondragover={(event) => {
              if (dragging && !ordering) {
                event.preventDefault();
                dropTarget = propertyKey(property);
              }
            }}
            ondrop={(event) => {
              event.preventDefault();
              void reorder(dragging, propertyKey(property));
            }}
          >
            <td
              >{#if data.can_edit}<button
                  type="button"
                  class="drag-property"
                  aria-label={`Move ${property.label}`}
                  title={ui('Drag to reorder; Alt + arrow keys also move this property')}
                  draggable={!ordering}
                  disabled={ordering}
                  ondragstart={(event) => {
                    dragging = propertyKey(property);
                    event.dataTransfer.effectAllowed = 'move';
                    event.dataTransfer.setData('text/plain', dragging);
                  }}
                  ondragend={() => {
                    dragging = '';
                    dropTarget = '';
                  }}
                  onkeydown={(event) => {
                    if (event.altKey && ['ArrowUp', 'ArrowDown'].includes(event.key)) {
                      event.preventDefault();
                      const index = data.properties.indexOf(property);
                      const other = data.properties[index + (event.key === 'ArrowUp' ? -1 : 1)];
                      if (other) void reorder(propertyKey(property), propertyKey(other));
                    }
                  }}><GripVertical size={15} /></button
                >{/if}<strong>{property.label}</strong>{#if !property.is_active}<small
                  >{ui('Inactive')}</small
                >{/if}</td
            >
            <td><code class="internal-name">{property.key}</code></td>
            <td>{types[property.field_type] ?? property.field_type}</td>
            <td class="number">{property.usage_count.toLocaleString(locale())}</td>
            <td
              ><span class="origin" class:system={property.is_system}
                >{#if property.is_system}<LockKeyhole size={12} />{/if}{property.is_system
                  ? ui('System')
                  : ui('Custom')}</span
              ></td
            >
            <td class="actions">
              {#if !property.is_system && data.can_edit}
                <button
                  class="v2-btn v2-btn-quiet icon"
                  aria-label={`Edit ${property.label}`}
                  onclick={() => openEditor(property)}><Pencil size={15} /></button
                >
                <form
                  method="POST"
                  action={property.is_active ? '?/deactivate' : '?/activate'}
                  use:enhance
                >
                  <input type="hidden" name="id" value={property.id} />
                  <button class="v2-btn v2-btn-quiet toggle"
                    >{property.is_active ? ui('Turn off') : ui('Turn on')}</button
                  >
                </form>
                <button
                  class="v2-btn v2-btn-quiet toggle delete-property"
                  type="button"
                  aria-label={`Delete ${property.label}`}
                  onclick={() => openDelete(property)}>{ui('Delete')}</button
                >
              {/if}
            </td>
          </tr>
        {:else}<tr
            ><td colspan="6" class="empty"
              >{query ? ui('No matching properties.') : ui('No custom properties yet.')}</td
            ></tr
          >{/each}
      </tbody>
    </table>
  </div>
</div>

<dialog
  class="delete-dialog"
  bind:this={deleteDialog}
  aria-labelledby="delete-property-title"
  oncancel={(event) => {
    if (deleteBusy) event.preventDefault();
  }}
>
  <form method="POST" action="?/delete" use:enhance={submitDelete}>
    <h2 id="delete-property-title">{ui('Delete property?')}</h2>
    <p>
      {ui('This permanently deletes')} <strong>{deleting?.label}</strong>
      {ui('and its saved values from')}
      {objectLabel.toLowerCase()}{ui(
        '. Any pipeline requirements using this property will also be removed. This cannot be undone.'
      )}
    </p>
    <input type="hidden" name="id" value={deleting?.id || ''} />
    <label
      >{ui('Type')} <strong>{deleting?.key}</strong>
      {ui('to confirm.')}
      <input
        class="v2-input"
        name="confirmation"
        bind:value={deleteConfirmation}
        autocomplete="off"
        disabled={deleteBusy}
      />
    </label>
    {#if deleteError}<p class="error" role="alert">{deleteError}</p>{/if}
    <div class="delete-actions">
      <button
        class="v2-btn"
        type="button"
        disabled={deleteBusy}
        onclick={() => deleteDialog.close()}>{ui('Cancel')}</button
      >
      <button
        class="v2-btn delete-confirm"
        disabled={deleteBusy || !deleting || deleteConfirmation.trim() !== deleting.key}
        >{deleteBusy ? ui('Deleting…') : ui('Delete permanently')}</button
      >
    </div>
  </form>
</dialog>

{#if editing}
  <TeamPanel
    title={editing.new ? ui('Create property') : ui('Edit property')}
    subtitle={objectLabel}
    {busy}
    onclose={() => (editing = null)}
  >
    <form
      class="panel-form"
      method="POST"
      action={editing.new ? '?/create' : '?/update'}
      use:enhance={submit}
    >
      <input type="hidden" name="target_model" value={data.target_model} />
      <input type="hidden" name="id" value={editing.id ?? ''} />
      <input type="hidden" name="field_type" value={fieldType} />
      <input
        type="hidden"
        name="display_order"
        value={editing.display_order ?? data.properties.length}
      />
      <input type="hidden" name="is_filterable" value={editing.is_filterable ?? true} />
      <div class="panel-body">
        <label class="field"
          >{ui('Property name')}<input
            class="v2-input"
            name="label"
            bind:value={label}
            required
            maxlength="128"
            placeholder={ui('e.g. Customer reference')}
          /></label
        >
        <label class="field">
          {ui('Internal name')}
          <input
            class="v2-input internal-name"
            name="key"
            value={key}
            oninput={(event) => (keyOverride = event.currentTarget.value)}
            readonly={!editing.new}
            required
            maxlength="64"
            pattern="[a-z][a-z0-9_]*"
            title={ui('Use lowercase letters, numbers and underscores; start with a letter.')}
          />
          <small
            >{editing.new
              ? ui('Used by the API. You can adjust it before creating the property.')
              : ui(
                  'Permanent identifier used by the API. It stays the same when the property name changes.'
                )}</small
          >
        </label>
        <label class="field"
          >{ui('Field type')}
          <select class="v2-input" bind:value={fieldType} disabled={!editing.new}>
            {#each Object.entries(FIELD_TYPE_LABEL) as [value, name]}<option {value}>{name}</option
              >{/each}
          </select>
          {#if !editing.new}<small>{ui('The type stays fixed to protect existing values.')}</small
            >{/if}
        </label>
        {#if fieldType === 'money'}<p class="hint">
            {ui('Amount in the organization’s currency, with up to 2 decimal places.')}
          </p>{/if}
        {#if fieldType === 'time'}<p class="hint">
            {ui('Local time, without a date or time zone.')}
          </p>{/if}
        {#if ['dropdown', 'multi_select'].includes(fieldType)}
          <fieldset>
            <legend>{ui('Options')}</legend>
            {#each options as option, index}
              <div class="option-row">
                <input type="hidden" name="option_value" value={option.value} /><input
                  class="v2-input"
                  name="option_label"
                  aria-label={`Option ${index + 1}`}
                  bind:value={option.label}
                  placeholder={`Option ${index + 1}`}
                  required
                /><button
                  type="button"
                  class="v2-btn v2-btn-quiet icon"
                  aria-label={`Remove option ${index + 1}`}
                  onclick={() => (options = options.filter((_, i) => i !== index))}
                  ><X size={16} /></button
                >
              </div>
            {/each}
            <button
              type="button"
              class="v2-btn v2-btn-quiet"
              onclick={() => (options = [...options, { value: '', label: '' }])}
              ><Plus size={14} /> {ui('Add option')}</button
            >
          </fieldset>
        {/if}
        {#if error}<p class="panel-error" role="alert">{ui(error)}</p>{/if}
      </div>
      <div class="panel-footer">
        <button type="button" class="v2-btn" disabled={busy} onclick={() => (editing = null)}
          >{ui('Cancel')}</button
        ><button
          class="v2-btn v2-btn-primary"
          disabled={busy ||
            !label.trim() ||
            (['dropdown', 'multi_select'].includes(fieldType) && !options.length)}
          >{busy ? ui('Saving…') : editing.new ? ui('Create property') : ui('Save changes')}</button
        >
      </div>
    </form>
  </TeamPanel>
{/if}

<style>
  .delete-property {
    color: var(--crm-danger);
  }
  .delete-dialog {
    margin: auto;
    width: min(460px, calc(100vw - 32px));
    max-height: 90dvh;
    overflow: auto;
    padding: var(--crm-space-6);
    border: 1px solid var(--v2-line);
    border-radius: var(--crm-radius-lg);
    background: var(--v2-card, var(--crm-surface));
    color: var(--v2-ink);
    box-shadow: var(--crm-shadow-lg);
  }
  .delete-dialog::backdrop {
    background: var(--crm-overlay);
  }
  .delete-dialog h2 {
    font-size: var(--crm-text-lg);
    margin: 0 0 var(--crm-space-3);
  }
  .delete-dialog p {
    font-size: var(--crm-text-sm);
    line-height: 1.6;
    color: var(--v2-slate);
  }
  .delete-dialog label {
    display: block;
    font-size: var(--crm-text-sm);
    margin-top: var(--crm-space-5);
    overflow-wrap: anywhere;
  }
  .delete-dialog input {
    margin-top: 10px;
    width: 100%;
  }
  .delete-actions {
    display: flex;
    justify-content: flex-end;
    gap: var(--crm-space-2);
    margin-top: var(--crm-space-6);
  }
  .delete-confirm {
    background: var(--crm-danger-bg);
    color: var(--crm-danger);
  }
  .drag-property {
    border: 0;
    background: transparent;
    color: var(--v2-slate);
    cursor: grab;
    padding: 5px;
    margin-right: 5px;
    vertical-align: middle;
  }
  .drop-position {
    box-shadow: inset 0 3px var(--crm-info);
  }
  .catalog {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding: var(--crm-space-6) 30px;
  }
  .toolbar,
  .summary {
    flex-shrink: 0;
  }
  .toolbar {
    display: flex;
    align-items: flex-end;
    gap: var(--crm-space-3);
    flex-wrap: wrap;
  }
  .object-field {
    display: grid;
    gap: 7px;
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
    min-width: 210px;
  }
  .toolbar .v2-input {
    min-height: 40px;
  }
  .search {
    position: relative;
    margin-left: auto;
  }
  .search :global(svg) {
    position: absolute;
    left: 12px;
    top: 12px;
    color: var(--v2-slate);
  }
  .search input {
    padding-left: 36px;
    width: 250px;
  }
  .kind {
    width: 165px;
  }
  .summary {
    display: flex;
    justify-content: space-between;
    color: var(--v2-slate);
    font-size: var(--crm-text-xs);
    margin: var(--crm-space-6) 0 var(--crm-space-3);
  }
  .table-scroll {
    flex: 1;
    min-height: 160px;
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
  th {
    position: sticky;
    top: 0;
    z-index: 1;
    color: var(--v2-slate);
    font-weight: 500;
    font-size: var(--crm-text-xs);
    background: var(--v2-bg);
    white-space: nowrap;
  }
  th,
  td {
    padding: 14px 18px;
    border-bottom: 1px solid var(--v2-line-soft);
  }
  tr:last-child td {
    border-bottom: 0;
  }
  strong {
    font-weight: 500;
    color: var(--v2-ink);
  }
  small {
    display: block;
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
    margin-top: var(--crm-space-1);
  }
  .number {
    font-variant-numeric: tabular-nums;
  }
  .origin {
    display: inline-flex;
    gap: 5px;
    align-items: center;
    border-radius: var(--crm-radius-sm);
    background: var(--v2-bg);
    padding: var(--crm-space-1) 7px;
    font-size: var(--crm-text-xs);
  }
  .system {
    color: var(--v2-slate);
  }
  .actions {
    white-space: nowrap;
    text-align: right;
  }
  .actions form {
    display: inline-block;
  }
  .icon {
    padding: 6px;
  }
  .toggle {
    font-size: var(--crm-text-xs);
  }
  .inactive {
    opacity: 0.6;
  }
  .empty {
    text-align: center;
    color: var(--v2-slate);
    padding: var(--crm-space-10);
  }

  fieldset {
    border: 0;
    padding: 0;
    margin: 0 0 var(--crm-space-6);
  }
  legend {
    font-size: var(--crm-text-sm);
    margin-bottom: 10px;
  }
  .option-row {
    display: flex;
    gap: 6px;
    margin-bottom: var(--crm-space-2);
  }
  .option-row input {
    flex: 1;
    min-width: 0;
  }
  .internal-name {
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
    overflow-wrap: anywhere;
  }
  .error {
    color: var(--v2-rust);
  }
  @media (max-width: 800px) {
    .catalog {
      padding: 18px;
    }
    .search {
      margin-left: 0;
    }
    th,
    td {
      padding: var(--crm-space-3);
    }
  }
</style>
