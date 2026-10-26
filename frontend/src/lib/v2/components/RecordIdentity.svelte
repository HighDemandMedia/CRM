<script>
  import { displayPhone, normalizedPhone } from '$lib/utils/phone-number.js';
  import { ArrowLeft, Mail, Phone, Pencil, Check } from '@lucide/svelte';
  import RecordIdentityEditor from './RecordIdentityEditor.svelte';
  import { resolve } from '$app/paths';
  import { asInternalPath } from '$lib/utils/paths.js';
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();
  /** @type {{name:string,email?:string,phone?:string,backHref:string,backLabel:string,onedit?:()=>void,onemail?:()=>void,disabled?:boolean,editing?:boolean,onclose?:()=>void,target?:string,record?:any,schema?:any,actions?:import('svelte').Snippet}} */
  let {
    name,
    email = '',
    phone = '',
    backHref,
    backLabel,
    onedit,
    onemail,
    disabled = false,
    editing = false,
    onclose = () => {},
    target,
    record,
    schema,
    actions
  } = $props();
  let editButton = $state();
  let nameEditor = $state();
  let emailEditor = $state();
  let phoneEditor = $state();
  let saving = $state(false);
  async function saveIdentity() {
    if (saving) return;
    saving = true;
    try {
      for (const editor of [nameEditor, emailEditor, phoneEditor]) {
        if (!(await editor?.commit())) return;
      }
      onclose();
    } finally {
      saving = false;
    }
  }
  let wasEditing = false;
  $effect(() => {
    // Return keyboard focus and the record heading after its editor closes.
    if (wasEditing && !editing) editButton?.focus();
    wasEditing = editing;
  });
</script>

<header class="record-identity">
  <div class="identity-navigation">
    <a class="back-link" href={resolve(asInternalPath(backHref))}
      ><ArrowLeft size={14} />{ui(backLabel)}</a
    >
    {#if onedit}<button
        bind:this={editButton}
        type="button"
        class="identity-edit"
        aria-label={ui(editing ? (saving ? 'Saving…' : 'Save') : 'Edit')}
        title={ui(editing ? (saving ? 'Saving…' : 'Save') : 'Edit')}
        disabled={disabled || saving}
        aria-busy={saving}
        onclick={() => (editing ? saveIdentity() : onedit())}
        >{#if editing}<Check size={15} />{:else}<Pencil size={15} />{/if}</button
      >{/if}
  </div>
  <div class="identity-name">
    {#if editing}<div class="name-editor">
        <span class="identity-label" aria-hidden="true">{ui('Name')}</span>
        <RecordIdentityEditor {target} {record} {schema} property="name" bind:this={nameEditor} />
      </div>{:else}<h1>{name}</h1>{/if}
  </div>
  {#if editing}<div class="identity-contact">
      <div class="contact-editor email-editor">
        <span class="identity-label" aria-hidden="true">{ui('Email')}</span>
        <RecordIdentityEditor {target} {record} {schema} property="email" bind:this={emailEditor} />
      </div>
    </div>
  {:else if email}
    <div class="identity-contact">
      <Mail size={15} />
      {#if onemail}<button class="contact-link" type="button" onclick={onemail}>{email}</button>
      {:else}<a class="contact-link" href={`mailto:${email}`}>{email}</a>{/if}
    </div>
  {:else if onedit}<button type="button" class="contact-link missing" {disabled} onclick={onedit}
      ><Mail size={15} />{ui('Add email')}</button
    >{/if}
  {#if editing}<div class="identity-contact">
      <Phone size={15} />
      <div class="contact-editor">
        <RecordIdentityEditor {target} {record} {schema} property="phone" bind:this={phoneEditor} />
      </div>
    </div>
  {:else if phone}<div class="identity-contact">
      <Phone size={15} /><a
        class="contact-link"
        href={`tel:${normalizedPhone(phone) || phone.replace(/[^+\d]/g, '')}`}
        >{displayPhone(phone)}</a
      >
    </div>
  {:else if onedit}<button type="button" class="contact-link missing" {disabled} onclick={onedit}
      ><Phone size={15} />{ui('Add phone')}</button
    >{/if}
  {#if actions}<div class="identity-actions">{@render actions()}</div>{/if}
</header>

<style>
  .record-identity {
    min-width: 0;
    padding-bottom: var(--crm-space-4);
    margin-bottom: var(--crm-space-2);
    border-bottom: 1px solid var(--v2-line-soft);
  }
  .back-link {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: var(--v2-slate);
    font-size: var(--crm-text-xs);
    min-height: 28px;
    text-decoration: none;
  }
  .identity-navigation {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }
  .identity-name {
    display: flex;
    align-items: flex-start;
    gap: 6px;
    margin: 6px 0 10px;
  }
  .name-editor {
    flex: 1;
    min-width: 0;
  }
  .identity-label {
    display: block;
    margin-bottom: 2px;
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
  }
  .name-editor :global(input.v2-input),
  .email-editor :global(input.v2-input) {
    width: 100%;
    min-width: 0;
    min-height: 32px;
    padding: 4px 0;
    border: 0;
    border-bottom: 1px solid var(--crm-control-border);
    border-radius: 0;
    background: transparent;
    box-shadow: none;
    font-size: var(--crm-text-sm);
    cursor: text;
  }
  .name-editor :global(input.v2-input:focus),
  .email-editor :global(input.v2-input:focus) {
    outline: none;
    border-bottom-color: var(--crm-focus);
    box-shadow: 0 1px 0 var(--crm-focus);
  }
  .name-editor :global(input.v2-input[aria-invalid='true']),
  .email-editor :global(input.v2-input[aria-invalid='true']) {
    border-bottom-color: var(--v2-rust);
    box-shadow: 0 1px 0 var(--v2-rust);
  }
  .email-editor {
    margin-bottom: 8px;
  }
  .contact-editor {
    flex: 1;
    min-width: 0;
    font-size: var(--crm-text-sm);
  }
  h1 {
    flex: 1;
    min-width: 0;
    margin: 0;
    font-size: var(--crm-text-lg);
    line-height: 1.35;
    font-weight: 650;
    overflow-wrap: anywhere;
  }
  .identity-edit {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex: none;
    width: 32px;
    height: 32px;
    border: 1px solid var(--v2-line);
    border-radius: var(--crm-button-radius);
    background: var(--v2-card);
    color: var(--v2-slate);
    cursor: pointer;
  }
  .identity-contact,
  .missing {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
    min-height: 32px;
  }
  .identity-contact :global(svg),
  .missing :global(svg) {
    flex: none;
    color: var(--v2-slate);
  }
  .contact-link {
    min-width: 0;
    padding: 4px 0;
    border: 0;
    background: none;
    color: var(--v2-ink);
    font: inherit;
    font-size: var(--crm-text-sm);
    text-align: left;
    cursor: pointer;
    overflow-wrap: anywhere;
    text-decoration: underline;
    text-decoration-color: var(--v2-line);
    text-underline-offset: 3px;
  }
  .contact-link:hover {
    color: var(--crm-focus);
  }
  .missing {
    color: var(--v2-slate);
  }
  .identity-actions {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: var(--crm-space-2);
    margin-top: var(--crm-space-3);
  }
  .identity-actions :global(.v2-btn) {
    min-height: 34px;
    padding: 6px 10px;
    font-size: var(--crm-text-xs);
    max-width: 100%;
    white-space: normal;
  }
  button:disabled {
    opacity: 0.5;
    cursor: default;
  }
</style>
