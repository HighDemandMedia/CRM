<script>
  import { tick, onMount } from 'svelte';
  import { beforeNavigate, invalidate, invalidateAll } from '$app/navigation';
  import { useI18n } from '$lib/i18n/context.js';
  import { recordValidation } from '$lib/components/creation/validation.js';
  import StageRequirementField from '$lib/components/pipelines/StageRequirementField.svelte';
  import { showStageRequirements } from '$lib/components/pipelines/feedback.js';
  import { propertyDraft, propertyValue, samePropertyValue } from '$lib/v2/inline-property.js';
  const { ui } = useI18n();
  /** @type {{field:any,value:any,target:string,recordId:string,children:import('svelte').Snippet,onstate?:(active:boolean)=>void,initiallyEditing?:boolean,onfinish?:()=>void,saveOnBlur?:boolean,persistent?:boolean}} */
  let {
    field,
    value,
    target,
    recordId,
    children,
    onstate = () => {},
    initiallyEditing = false,
    persistent = false,
    saveOnBlur = true,
    onfinish = () => {}
  } = $props();
  onMount(() => {
    if (initiallyEditing || persistent) void edit(!persistent);
  });
  let editing = $state(false),
    busy = $state(false),
    error = $state(''),
    status = $state('');
  let draft = $state(/** @type {any} */ (''));
  let original = $state(/** @type {any} */ (null)),
    form = $state(),
    trigger = $state();
  let fieldErrors = $state({});
  let controlBusy = $state(false);
  async function controlState(active) {
    const wasBusy = controlBusy;
    controlBusy = active;
    await tick();
    if (wasBusy && !active && editing && !busy && !form?.contains(document.activeElement))
      form?.requestSubmit();
  }
  let refreshFailed = $state(false);
  const changed = $derived(editing && !samePropertyValue(draft, original));
  $effect(() => {
    onstate(busy || controlBusy || changed);
  });
  beforeNavigate((navigation) => {
    // Do not discard a rejected draft or interrupt a write by changing modules.
    if (busy || controlBusy || changed) {
      navigation.cancel();
      error = busy ? 'Saving…' : 'Finish editing or cancel this change before leaving.';
    }
  });
  export async function edit(focus = true) {
    if (busy || controlBusy) return;
    original = propertyDraft(value, field);
    draft = $state.snapshot(original);
    error = '';
    fieldErrors = {};
    status = '';
    editing = true;
    await tick();
    if (!focus) return;
    const control =
      form?.querySelector(
        'input:not([type=hidden]):not([type=radio]):not([type=checkbox]),textarea'
      ) ||
      form?.querySelector('input:checked') ||
      form?.querySelector('input:not([type=hidden]),select,button');
    // Text fields are ready to replace; choice lists are already expanded.
    control?.focus({ preventScroll: true });
    if (
      control instanceof HTMLInputElement &&
      ['text', 'tel', 'url', 'search'].includes(control.type)
    )
      control.select();
  }
  async function cancel() {
    if (busy || controlBusy) return;
    editing = persistent;
    draft = $state.snapshot(original);
    error = '';
    fieldErrors = {};
    await tick();
    // Do not steal focus if the user has already opened another editor.
    if (document.activeElement === document.body) trigger?.focus({ preventScroll: true });
    onfinish();
  }
  async function refresh() {
    try {
      if (['Contact', 'Account'].includes(target))
        await invalidate(`crm:record:${target}:${recordId}`);
      else await invalidateAll();
      refreshFailed = false;
    } catch {
      refreshFailed = true;
    }
  }
  let pendingSave;
  async function save(event) {
    event.preventDefault();
    await commit();
  }
  export async function commit() {
    // Reuse a blur/outside-click write when the header Save button is clicked.
    if (pendingSave) return pendingSave;
    if (controlBusy) return false;
    if (!editing) return !error;
    if (!form?.reportValidity()) return false;
    pendingSave = persist();
    try {
      return await pendingSave;
    } finally {
      pendingSave = undefined;
    }
  }
  async function persist() {
    if (!changed) {
      editing = persistent;
      onfinish();
      return true;
    }
    busy = true;
    error = '';
    fieldErrors = {};
    status = '';
    try {
      const next = propertyValue(draft, field);
      if (field.required && (next == null || next === '' || (Array.isArray(next) && !next.length)))
        throw new Error('This field is required.');
      const key = field.key.replace(/^custom_fields\./, '');
      const values = { [key]: next };
      const response = await fetch('/api/record-properties', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target, id: recordId, system: !field.custom, values })
      });
      const result = await response.json();
      if (!response.ok) {
        fieldErrors = result.fieldErrors || {};
        if (result.stageRequirements) {
          const changes = field.custom ? { custom_fields: values } : values;
          showStageRequirements({ data: result }, target, recordId, changes);
          editing = false;
          return false;
        }
        throw new Error(result.error || 'Could not save the property.');
      }
      // A refresh failure must never turn a successful write into a retryable write.
      original = $state.snapshot(draft);
      status = 'Saved';
      await refresh();
      if (persistent && !refreshFailed) {
        draft = propertyDraft(value, field);
        original = $state.snapshot(draft);
      }
      editing = persistent;
      onfinish();
      return true;
    } catch (err) {
      error = err.message || 'Could not save the property.';
      return false;
    } finally {
      busy = false;
    }
  }
  async function leave(event) {
    if (!saveOnBlur) return;
    // Safari can blur to the document when a radio, checkbox or label is clicked.
    // Keep the editor mounted until that control receives its click/change.
    if (!event.relatedTarget || form?.contains(event.relatedTarget)) return;
    await tick();
    if (editing && !busy && !controlBusy && !form?.contains(document.activeElement))
      form?.requestSubmit();
  }
  function keyboard(node) {
    let tabExit;
    function tabbed(event) {
      if (saveOnBlur || event.key !== 'Tab') return;
      // Popovers move focus while opening. Only explicit keyboard departure saves here.
      clearTimeout(tabExit);
      tabExit = setTimeout(() => {
        if (editing && !node.contains(document.activeElement)) node.requestSubmit();
      }, 0);
    }
    function pointerdown(event) {
      if (!node.contains(event.target)) node.requestSubmit();
    }
    node.addEventListener('keydown', keydown);
    node.addEventListener('keydown', tabbed);
    node.ownerDocument.addEventListener('pointerdown', pointerdown, true);
    return {
      destroy() {
        node.removeEventListener('keydown', keydown);
        node.removeEventListener('keydown', tabbed);
        clearTimeout(tabExit);
        node.ownerDocument.removeEventListener('pointerdown', pointerdown, true);
      }
    };
  }
  function keydown(event) {
    if (event.key === 'Escape') {
      event.preventDefault();
      event.stopPropagation();
      void cancel();
    }
    if (
      !event.defaultPrevented &&
      event.key === 'Enter' &&
      event.target.getAttribute('role') !== 'combobox' &&
      !event.target.closest('[data-stage-field="tags"]') &&
      event.target.tagName !== 'TEXTAREA' &&
      event.target.tagName !== 'BUTTON' &&
      !event.isComposing
    ) {
      event.preventDefault();
      form?.requestSubmit();
    }
  }
</script>

<div class="inline-property">
  {#if editing}
    <form
      bind:this={form}
      class="auto-save"
      use:recordValidation={fieldErrors}
      onsubmit={save}
      onfocusout={leave}
      use:keyboard
      aria-label={field.label}
      aria-busy={busy}
    >
      <fieldset disabled={busy}>
        <StageRequirementField
          {target}
          {field}
          compact
          onbusy={controlState}
          oncommit={async () => {
            await tick();
            form?.requestSubmit();
          }}
          required={!!field.required}
          bind:value={draft}
        />
      </fieldset>
      {#if busy}<span class="saving" role="status">{ui('Saving…')}</span>{/if}
      {#if error}<p class="field-error" role="alert">{ui(error)}</p>{/if}
    </form>
  {:else}
    <button
      bind:this={trigger}
      type="button"
      class="property-value"
      aria-label={`${ui('Edit')} ${field.label}`}
      onclick={() => edit()}
    >
      <span>{@render children()}</span>
    </button>
  {/if}
  {#if status && !changed && !busy && !error}<span class="saved" role="status">{ui(status)}</span
    >{/if}
  {#if refreshFailed}<p class="field-error" role="alert">
      {ui('Saved. Could not refresh the view.')}
      <button type="button" onclick={refresh}>{ui('Refresh')}</button>
    </p>{/if}
</div>

<style>
  .inline-property {
    white-space: normal;
    min-width: 0;
  }
  .property-value {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    width: 100%;
    text-align: left;
    border: 1px solid transparent;
    border-radius: var(--crm-radius-sm);
    padding: 4px 5px;
    margin: -4px -5px;
    background: transparent;
    color: inherit;
    font: inherit;
    cursor: pointer;
  }
  .property-value > span {
    flex: 1;
    min-width: 0;
    overflow-wrap: anywhere;
    white-space: pre-wrap;
  }
  .property-value:hover,
  .property-value:focus-visible {
    border-color: var(--v2-line);
    background: var(--crm-canvas);
  }
  fieldset {
    border: 0;
    margin: 0;
    padding: 0;
    min-width: 0;
  }
  .saving {
    display: block;
    margin-top: 4px;
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
  }
  .saved {
    display: flex;
    gap: 4px;
    align-items: center;
    color: var(--crm-success, #23734a);
    font-size: var(--crm-text-xs);
    margin-top: 4px;
  }
  .field-error {
    color: var(--crm-danger, #b42318);
    font-size: var(--crm-text-xs);
    margin: 6px 0 0;
  }
</style>
